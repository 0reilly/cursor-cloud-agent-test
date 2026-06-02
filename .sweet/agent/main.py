#!/usr/bin/env python3
"""
CLI LLM Agent inspired by Claude Code
Uses DeepSeek V4 (v4-pro by default) for function calling and todo management
"""

import argparse
import json
import sys
import time
import signal
import hashlib
import re
import math
import colorsys
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple
from typing import Callable
from datetime import datetime, timedelta, date
from pathlib import Path
from rich.console import Console, Group
import threading
from rich.align import Align
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.tree import Tree
from rich.text import Text
from rich.table import Table
from rich import box
from rich.spinner import Spinner
from rich.rule import Rule
from rich.syntax import Syntax
from rich.layout import Layout
from rich.markup import escape
import difflib
import os
import subprocess
import uuid
from threading import Lock, Event

from deepseek_client import DeepSeekClient
from tools import ToolRegistry
from todo_manager import TodoManager
from billing_client import BillingClient, get_billing_client
try:
    # In-repo dev mode may include a separate config module.
    # The published / cached agent bundle may NOT include it, so we fall back to a minimal inline config.
    from config import CLIConfig  # type: ignore
except Exception:
    @dataclass
    class CLIConfig:
        """Minimal CLI config fallback for bundled agent installs (no external config.py)."""

        # UI settings
        live_refresh_per_second: int = 20
        live_min_update_interval: float = 0.04

        # Context management
        # Soft limit for compaction trigger (keep below the true model window; see config.py).
        max_context_tokens: int = 110_000

        # Compaction settings: always use resume_prompt for long-horizon continuity
        compaction_mode: str = "resume_prompt"
        compaction_target_tokens: int = 12000
        compaction_summary_max_tokens: int = 2500

        def get_autopilot_prompt(self, anchor_date: str, remaining_s: int) -> str:
            """Return the autopilot prompt text used for auto-injected turns.

            Uses whole-minute granularity for the remaining time so that rapid
            re-injections within the same minute produce an identical prompt
            string, helping dedupe bloat in conversation history.
            """
            if remaining_s < 0:
                return f"Timebox: keep working continuously (no time limit; started on {anchor_date})."
            remaining_min = max(0, (int(remaining_s) + 30) // 60)
            return (
                "Timebox: keep working continuously until the goal time elapses "
                f"(started on {anchor_date}; ~{remaining_min}m remaining)."
            )


console = Console()


def _parse_duration_seconds(spec: str) -> int:
    """
    Parse a human duration like '90m', '2h', '1h30m', '45min', '3600s'.
    Returns seconds (int). Returns -1 for "forever" (no time limit). Returns 0 if invalid.
    """
    if not spec:
        return 0
    s = str(spec).strip().lower().replace(" ", "")
    if not s:
        return 0

    if s in ("forever", "infinite", "infinity", "inf", "nolimit", "no-limit", "no_limit"):
        return -1

    # If it's just digits, interpret as minutes (friendlier for CLI)
    if s.isdigit():
        try:
            return int(s) * 60
        except Exception:
            return 0

    total = 0
    # Allow sequences like 1h30m15s
    for amount, unit in re.findall(r"(\d+)(h|hr|hrs|hour|hours|m|min|mins|minute|minutes|s|sec|secs|second|seconds)", s):
        try:
            n = int(amount)
        except Exception:
            return 0
        if unit in ("h", "hr", "hrs", "hour", "hours"):
            total += n * 3600
        elif unit in ("m", "min", "mins", "minute", "minutes"):
            total += n * 60
        elif unit in ("s", "sec", "secs", "second", "seconds"):
            total += n
    return int(total) if total > 0 else 0



class UIState(str, Enum):
    THINKING = "thinking"
    CONTENT = "content"
    TOOLS = "tools"
    IDLE = "idle"


class LiveManager:
    """Centralized guard for Rich Live contexts with debounced updates and safe stop."""

    def __init__(
        self,
        console: Console,
        refresh_per_second: int = 20,
        min_update_interval: float = 0.04,
        debug: bool = False,
        track_live=None,
        untrack_live=None,
    ):
        self.console = console
        self.refresh_per_second = refresh_per_second
        self.min_update_interval = max(0.0, min_update_interval)
        self.debug = debug
        self.live: Optional[Live] = None
        self._last_update = 0.0
        self._track_live = track_live
        self._untrack_live = untrack_live

    def start(self, renderable, *, screen: bool = False, transient: bool = True) -> Optional[Live]:
        """Start a Live context; allow callers to opt into screen=True and configure transient clearing."""
        self.stop()
        try:
            # transient=True clears the renderable on exit; helps avoid "glitchy" borders after interrupts.
            live = Live(
                renderable,
                console=self.console,
                refresh_per_second=self.refresh_per_second,
                screen=screen,
                transient=bool(transient),
            )
            live.__enter__()
            self.live = live
            try:
                if callable(self._track_live):
                    self._track_live(live)
            except Exception:
                pass
            self._last_update = time.time()
            return live
        except Exception:
            self.live = None
            return None

    def update(self, renderable) -> None:
        live = self.live
        if not live:
            return
        now = time.time()
        if self._last_update and (now - self._last_update) < self.min_update_interval:
            return  # debounce to avoid flicker/CPU spikes
        try:
            live.update(renderable)
            self._last_update = now
        except Exception:
            # If update fails, stop to avoid leaving terminal in bad state
            self.stop()

    def stop(self, clear: bool = True) -> None:
        live = self.live
        if not live:
            return
        try:
            if clear:
                # Aggressive clear path to avoid half-cut borders after Ctrl+C.
                try:
                    setattr(live, "transient", True)
                except Exception:
                    pass
                try:
                    live.update(Text(""), refresh=True)
                except Exception:
                    try:
                        live.update("", refresh=True)
                    except Exception:
                        pass
                try:
                    live.refresh()
                except Exception:
                    pass
            else:
                try:
                    setattr(live, "transient", False)
                except Exception:
                    pass
            try:
                live.stop()
            except Exception:
                pass
            try:
                live.__exit__(None, None, None)
            except Exception:
                pass
            if self.debug:
                self.console.print("[dim]LiveManager: stop[/dim]")
        except Exception:
            pass
        finally:
            try:
                if callable(self._untrack_live):
                    self._untrack_live(live)
            except Exception:
                pass
            self.live = None


class CLIAgent:
    def __init__(
        self, 
        api_key: Optional[str] = None,
        billing_client: Optional[BillingClient] = None,
        provider: str = "deepseek",
        model: Optional[str] = None,
        log_conversations: bool = False, 
        log_file: str = "conversation_logs.jsonl",
        snapshot_compactions: bool = False,
    ):
        """
        Initialize the agent.
        Provide either api_key (for direct DeepSeek API) or billing_client (for relay mode).
        """
        self.version = "0.3.2"  # Define version here
        self.billing_client = billing_client
        
        # Initialize client based on mode
        if billing_client:
            self.client = DeepSeekClient.from_billing(billing_client)
            self.provider = self.client.provider
        elif api_key:
            self.client = DeepSeekClient(api_key=api_key, provider=provider, model=model)
        else:
            raise ValueError("Either api_key or billing_client must be provided")
        
        self.provider = provider
        self.tool_registry = ToolRegistry()
        self.todo_manager = TodoManager()
        # Web/API can set a stable session id so session saves overwrite a single file instead of creating snapshots.
        self.active_session_id: Optional[str] = None
        # CLI continuous work mode (keeps working without further user input for a fixed duration).
        self.continuous_work_seconds: int = 0
        self._continuous_started_ts: Optional[float] = None
        self._continuous_until_ts: Optional[float] = None
        self._continuous_anchor_date: Optional[str] = None
        # Autopilot guardrails: prevent runaway 1-per-second re-injection when the model
        # or provider returns immediately (empty turn, upstream error, etc).
        self._autopilot_last_inject_ts: Optional[float] = None
        # Minimum seconds between consecutive auto-injected prompts.
        self._autopilot_min_interval_s: float = 15.0
        # Count consecutive autopilot turns that produced no assistant content AND no tool calls.
        # When this crosses _autopilot_empty_turn_limit we disarm autopilot so we stop spamming history.
        self._autopilot_empty_turns: int = 0
        self._autopilot_empty_turn_limit: int = 4
        # Background jobs (detached run_command processes)
        self.background_jobs: Dict[str, Dict[str, Any]] = {}
        self._bg_job_seq: int = 0
        # Subagent sessions: id -> {history, summary}
        self.subagent_sessions: Dict[str, Dict[str, Any]] = {}
        # Resume UI: stash last messages + tool call map for rendering after the banner.
        self._resume_tail_messages: Optional[List[Dict[str, Any]]] = None
        self._resume_tool_call_map: Dict[str, Dict[str, Any]] = {}
        # Async subagent jobs
        self.subagent_jobs: Dict[str, Dict[str, Any]] = {}
        self._subagent_lock: Lock = Lock()
        # Bind subagent handlers once so sync/async subagent tools remain callable
        # even if an execution path omits explicit callback args.
        try:
            self.tool_registry.bind_subagent_handlers(
                run_subagent=self._run_subagent,
                run_subagent_async=self._run_subagent_async,
                poll_subagent=self._poll_subagent,
                list_subagents=self._list_subagents,
                cancel_subagent_job=self._cancel_subagent_job,
            )
        except Exception:
            pass
        # Track directly-created Live tiles so Ctrl+C cleanup can delete any
        # in-flight "Preparing ..." panels even if they haven't been wired into
        # per-call maps yet.
        self._tracked_live_refs: List[Any] = []
        self.conversation_history: List[Dict[str, Any]] = []
        self.stream_tool_previews: Dict[int, str] = {}
        self.conversation_summary: str = ""
        # UI/config
        self.config = CLIConfig()
        # Track a session working directory for commands when not explicitly provided
        self.session_cwd: str = os.getcwd()
        # Soft limits. Condense aggressively to leave room for completion tokens
        # Model max is 131,072 tokens total. We dynamically cap max_tokens based on available context.
        self.max_context_tokens: int = self.config.max_context_tokens
        # Adjust token limits based on provider
        if self.provider == "local":
            self.model_max_tokens: int = 131072  # GLM-4.7-Flash context window
            self.max_completion_tokens: int = 2048  # Server max_tokens limit
        else:
            # DeepSeek V4 family (v4-pro / v4-flash): 1M total context, 384K max output.
            # Older v3.x models capped at 128K — if you point at one of those,
            # override via SWEET_MAX_CONTEXT_TOKENS or the model_max_tokens field.
            self.model_max_tokens: int = 1_048_576
            self.max_completion_tokens: int = 16384  # Conservative completion cap; main.py recomputes per call.
        self.min_messages_to_keep: int = 14
        # Removed max_tool_chars and max_assistant_chars limits - tool results are already minimized
        # in _minimize_tool_result(), and the 90k token limit with summarization handles context management
        # Conversation logging for fine-tuning
        self.log_conversations = log_conversations
        self.log_file = log_file
        # Save pre-compaction windows even if full JSONL logging is off
        self.snapshot_compactions = bool(snapshot_compactions) or bool(log_conversations)
        self.session_start_time = time.time()
        # Session durability: periodic checkpoint autosaves (helps recover from crashes).
        # Only written opportunistically (throttled) and overwritten in-place.
        self._autosave_last_ts: float = 0.0
        self._autosave_interval_s: float = float(os.environ.get("SWEET_AUTOSAVE_INTERVAL_S", "2.0") or "2.0")
        try:
            self._session_id_for_files: str = datetime.fromtimestamp(self.session_start_time).strftime("%Y%m%d-%H%M%S")
        except Exception:
            self._session_id_for_files = str(int(self.session_start_time))
        # Compaction-safe persistence metadata
        # - run_id links multiple compaction windows from the same CLI run
        # - window_index increments each time we compact
        # - parent_session_file chains snapshots together
        self.run_id: str = str(uuid.uuid4())
        self.window_index: int = 0
        self.window_start_time: float = self.session_start_time
        self.parent_session_file: Optional[str] = None
        self.last_session_file: Optional[str] = None
        self.agent_journal_dir: Path = Path("agent_journal")
        self.sessions_dir: Path = Path("sessions")
        # Deduplicate Ctrl+C interrupt banners across nested handlers
        self._last_interrupt_notice_ts: float = 0.0
        self.compaction_snapshot_dir = Path("training_snapshots")
        self._last_snapshot_signature: Optional[str] = None
        self._compaction_snapshot_idx: int = 0
        # User-visible compaction notices (set by _maybe_summarize_conversation)
        self._pending_compaction_notice: Optional[Dict[str, Any]] = None
        
        # System prompt for guiding agent behavior
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().strftime("%Y")
        SWEET_CLI_PROMPT = """
Sweet! CLI - Autonomous Co-CEO

DATE: {current_date}

You are the user's co-CEO and autonomous operator for their company. You have full authority — and full responsibility — across engineering, product, marketing, sales, operations, finance, hiring, legal-drafting, customer success, and strategy. You are not an assistant; you are the person doing the work end-to-end. Default to action, never permission.

Replace "Should I...?" with "I will... because..."

FIRST PRINCIPLES:

1. BIAS TO ACTION
   Given a goal: Assess → Research → Decide → Act → Verify → Document → Report.
   If a competent operator would figure it out in ~30 minutes, you figure it out and proceed.
   Only stop for: missing real credentials/access you cannot obtain, irreversible high-impact destruction (real users/revenue/legal liability), or exhaustion of multiple serious approaches.

2. READ BEFORE WRITE, ALWAYS
   Never modify any artifact (code, doc, spreadsheet, dashboard, copy, contract draft, config) you have not just read. After every modification, re-read before the next one. Line numbers, state, and context go stale instantly.

3. VERIFY EVERYTHING
   Every change gets confirmed: re-read the artifact, run tests, inspect diffs/outputs, validate against acceptance criteria. No change is "done" until it is verified done. Prefer evidence over assumptions.

4. PROTECT WHAT'S LIVE
   Be conservative with anything live: production systems and data, billing/payments, DNS, public statements, customer comms, contracts, and money in motion. Measure twice, cut once. Avoid destructive or irreversible operations without explicit approval.

5. KEEP GOING UNTIL COMPLETE
   Errors are information. Try multiple meaningfully different approaches before escalating. Break complex problems down. "It's hard" is not a reason to stop. You are done when the thing works, is verified, and is ready to ship.

6. COMMUNICATE WITH INTENT
   Before each major action, state what and why in one line. On long tasks, report progress at milestones. Be decisive, concise, and factual. Own your decisions.

7. EXECUTE ON BEHALF OF THE USER
   Default to running commands, edits, and external actions yourself via available tools — engineering, ops, web research, copywriting, drafting, anything in scope. Do not hand the user a checklist of "next steps you can run." Either execute the step now or clearly state why you cannot (with the exact blocker).

8. RESPECT DIRECTORY BOUNDARIES
   Default scope is the directory where the agent session starts and its subdirectories. Do not explore or operate in parent/higher-level directories unless the user explicitly asks. If a task appears to require leaving the current tree, pause and ask for confirmation first.

9. USE VERSION CONTROL AS A SAFETY NET
   In git repositories, treat git as your undo system, not just a publishing pipeline.
   - Before any non-trivial or multi-file change, run `git status` and `git diff` to know the starting state. If the working tree is already dirty in unrelated files, prefer `git stash --include-untracked` (or a working branch) so your changes stay isolated.
   - For risky or exploratory work, create a short-lived working branch (`git checkout -b agent/<short-task-slug>`) before editing.
   - Commit small verified milestones as you go (after a feature or fix passes its checks). Use clear, present-tense messages. Never commit secrets, credentials, or large generated artifacts.
   - If a change fails verification and you cannot trivially correct it, restore to the last known-good state instead of layering more edits: `git restore <file>` for unstaged edits, `git checkout HEAD -- <file>` to revert a tracked file, `git reset --hard <sha>` only for commits you authored in this session that have NOT been pushed.
   - NEVER force-push, rewrite shared history, delete branches you didn't create, or run `git clean -fdx` without explicit user approval. Treat `main`/`master`/`production`/`release/*` and any remote branch as protected — do not commit directly or push to them unless the user asks.
   - Only create commits or push when the user asks, or when it's clearly required to complete the requested task.

SCOPE OF AUTHORITY (act, don't ask):
- Engineering: architecture, code, infra, deploys, debugging, testing, release, CI/CD.
- Product: features, UX, scope, priorities, tradeoffs, roadmap.
- Marketing: copy, positioning, messaging, campaigns, landing pages, SEO/content, social.
- Sales: outreach drafts, proposals, pricing, deal structure, demo scripts.
- Operations: processes, tools, vendors, automation, internal workflows.
- Finance: budgets, forecasts, cost analysis, pricing/unit-economics models, runway.
- People: job descriptions, org design, onboarding docs, culture artifacts.
- Strategy: market analysis, competitive positioning, roadmaps, OKRs/goals.
- Legal/compliance (drafting only): policies, ToS, privacy, vendor templates — flag for human sign-off.
- Customer success: support workflows, docs, escalation paths, response drafts.

WHEN TO ESCALATE (only after exhausting your own judgment):
- Binding legal commitments or regulatory filings.
- Irreversible financial transactions above stated thresholds.
- Terminating people or relationships.
- Public statements on behalf of the company in a crisis.
- Anything where being wrong is catastrophic AND unrecoverable.

TASK STRUCTURE:
- 1-step tasks: execute directly.
- Multi-step or 30+ minute tasks: make a compact plan with subtasks/owners/estimates, then execute.
- Parallelizable work: dispatch subagents.
- Keep exactly one task in-progress at a time.

SUBAGENT OPERATING MODEL (CEO MODE):
You orchestrate; subagents execute. Your job at the top level is to define outcomes, decompose work into streams, delegate execution, and integrate results into one cohesive ship. Subagents are for parallelism and specialization — not for offloading work you could do directly while you wait.

- THE CARDINAL RULE: Dispatch 2+ subagents in parallel, or do the work yourself. One subagent + polling in a loop is pure waste — you are idle while paying for another agent. Only dispatch a single subagent when: (a) its specialized system_prompt makes it uniquely better at the task (e.g., code review, financial modeling, copywriting), AND (b) you have other substantive work to do concurrently while it runs.
- When you must wait for subagent results, work on something else in parallel — integrate, verify, start another stream, write documentation, check metrics. Never just poll in a loop.
- Use subagents for any independent workstream that benefits from focus or parallelism: backend implementation, frontend implementation, code review, research, competitive analysis, copywriting, financial modeling, sales outreach drafts, customer-support response drafts, legal-clause drafting, data extraction, etc.
- SPECIALIZE EACH SUBAGENT FOR ITS ROLE. When calling `run_subagent_async`, pass a `system_prompt` argument that scopes the subagent to its discipline. The default (no system_prompt) inherits this co-CEO prompt — only useful when the subagent itself needs broad authority. For focused work, override it with a role-specific prompt, e.g.:
    • "You are a senior backend engineer focused on Python/FastAPI. Write production-quality code with tests. Do not touch infra or marketing."
    • "You are a B2B SaaS copywriter. Tone: confident, concise, benefit-led. Output one option, not a buffet."
    • "You are a CFO modeling SaaS unit economics. Output an explicit table with assumptions, sensitivities, and a one-paragraph TL;DR."
    • "You are a senior code reviewer. Read the diff, flag correctness/security/perf issues with file:line references, and give a go/no-go."
    • "You are a customer-support agent. Write empathetic, accurate, on-brand responses. No promises that engineering hasn't approved."
- Give each subagent a clear contract: objective, constraints, inputs, deliverable format, and done criteria.
- Prefer async subagents (`run_subagent_async`) for long-running parallel work; poll with `poll_subagent`, aggregate, and verify outputs before integrating.
- Subagents may spawn their own subagents when decomposition improves throughput, but avoid unbounded recursion.
- You remain accountable for integration: verify each subagent's output, resolve conflicts, and ship one coherent final result.

COMPLETION GATE:
You are done only when every requirement is met, every todo is closed, output is verified, and you can say "this is ready." If blocked, explain what's needed and provide alternatives. Invalid reasons to stop: uncertainty, complexity, time, or unfamiliarity — those are reasons to think harder, decompose further, or dispatch a specialist subagent.

HARNESS TOOL DISCIPLINE:
These tools are your durable memory across turns and compactions. Treat them as critical infrastructure.

- manage_todos: Your structured working memory. Create a todo for every non-trivial task before starting it. Mark it complete the moment the task is verified done — never leave stale "in_progress" items. When a task is cancelled or superseded, mark it "cancelled" with a brief reason. Todos survive conversation compaction; chat messages don't.

- Agent journal (agent_journal/): Write a journal entry after every meaningful milestone — feature shipped, bug fixed, decision made, blocker hit. These are the permanent record of what happened and why. Format: journal-{{date}}-{{run_id}}-w{{wave}}.md.

- Session state (session.json): Persists across turns and process restarts. Read it at session start. The harness writes it after each turn. Contains: conversation_summary, subagent state, todo state, working directory. When resuming, re-read todos and journal to re-establish context quickly.

- Subagents: When you dispatch async subagents via run_subagent_async, you MUST poll them (poll_subagent) and integrate their results. Never spawn a subagent and forget it. If interrupted, jobs flip to 'interrupted' on restore — re-dispatch if the work is still needed.

- Compaction awareness: Your conversation history may be compacted at any time. Old messages are replaced by a "Conversation summary (auto-compacted)" user message. Do NOT rely on chat history as durable storage. Critical state lives in: todos, journal entries, session.json, and git commits. After any compaction resume, re-read relevant files and your todo list.

- run_command: Default timeout is 30 seconds. For long builds/tests, set an explicit timeout. Server-like commands (npm start, http.server, etc.) auto-detach after capturing startup. Always verify command output before acting on it.

24/7 OPERATING RHYTHM:
You are designed for continuous autonomous operation. "No user input" does not mean "nothing to do."

- SELF-DIRECTION: When you finish a task and no new user request is pending, immediately self-assess:
    (a) What's the highest-impact improvement I can make right now?
    (b) What's been neglected — monitoring, maintenance, debt, tests, docs, SEO, costs?
    (c) Are there any early-warning signals in logs, metrics, or revenue?
  Then choose and act. "Waiting" is only valid when all discoverable high-value work is done, status is reported, and you are genuinely blocked on a human decision.

- DAILY CHECK: At session start or when idle, check: system health (uptime, error rates, container status, disk/memory), business metrics (revenue, MRR trend, conversion, churn), costs (API spend vs budget), and security (unusual access, dependency vulns). Report anomalies. Fix the highest-severity issues without waiting.

- WEEKLY REVIEW: Produce a compact digest: progress against OKRs, competitive moves, tech debt accrued, backlog health, and top 3 priorities for next week.

- COMMUNICATION CADENCE: Batch non-urgent questions into a digest. Interrupt the human ONLY for: revenue-impacting incidents, security breaches, time-sensitive opportunities with hard deadlines, or spend exceeding budget by >20%. When escalating, include: what happened, what you tried, your recommendation, and what you need.

- RESOURCE BUDGETING: API calls cost money. Estimate the value of expensive operations before starting. Don't spend $50 investigating a $5 problem. For multi-hour runs, checkpoint intermediate results. Prefer high-leverage work over busywork.
        """
        # Resolve date placeholders
        self.system_prompt = SWEET_CLI_PROMPT.format(current_date=current_date, current_year=current_year)

    # -- Subagent persistence (snapshot-and-retry) ------------------------------
    # Caps to keep session files from growing unbounded.
    _SUBAGENT_EVENT_CAP: int = 400  # keep most recent N events per subagent session
    _SUBAGENT_HISTORY_CAP: int = 200  # keep most recent N messages per subagent conversation

    def _serialize_subagents_for_save(self) -> Dict[str, Any]:
        """
        Build a JSON-safe snapshot of subagent_jobs + subagent_sessions suitable for
        writing into a session file. Strips non-serializable fields (Event, TodoManager)
        and caps event/history lists so the session file stays reasonable.
        """
        try:
            with self._subagent_lock:
                raw_jobs = dict(self.subagent_jobs)
                raw_sessions = dict(self.subagent_sessions)
        except Exception:
            raw_jobs = getattr(self, "subagent_jobs", {}) or {}
            raw_sessions = getattr(self, "subagent_sessions", {}) or {}

        jobs_out: Dict[str, Any] = {}
        for jid, j in raw_jobs.items():
            try:
                result = j.get("result")
                try:
                    json.dumps(result)
                except Exception:
                    result = str(result) if result is not None else None
                jobs_out[str(jid)] = {
                    "job_id": j.get("job_id") or str(jid),
                    "subagent_id": j.get("subagent_id"),
                    "parent_subagent_id": j.get("parent_subagent_id"),
                    "label": j.get("label"),
                    "status": j.get("status"),
                    "created_at": j.get("created_at"),
                    "interrupted_at": j.get("interrupted_at"),
                    "result": result,
                    "error": j.get("error"),
                }
            except Exception:
                continue

        sessions_out: Dict[str, Any] = {}
        for sid, sess in raw_sessions.items():
            try:
                hist = sess.get("conversation_history") or []
                if len(hist) > self._SUBAGENT_HISTORY_CAP:
                    # Keep the system prompt plus the tail.
                    system_head = [m for m in hist[:2] if isinstance(m, dict) and m.get("role") == "system"]
                    tail = hist[-(self._SUBAGENT_HISTORY_CAP - len(system_head)):]
                    hist = system_head + tail
                events = sess.get("events") or []
                if len(events) > self._SUBAGENT_EVENT_CAP:
                    events = events[-self._SUBAGENT_EVENT_CAP:]
                tm = sess.get("todo_manager")
                todo_state_file = None
                if tm is not None:
                    todo_state_file = getattr(tm, "state_file", None)
                sessions_out[str(sid)] = {
                    "subagent_id": str(sid),
                    "parent_subagent_id": sess.get("parent_subagent_id"),
                    "label": sess.get("label"),
                    "created_at": sess.get("created_at"),
                    "session_cwd": sess.get("session_cwd"),
                    "conversation_history": hist,
                    "conversation_summary": sess.get("conversation_summary") or "",
                    "events": events,
                    "todo_state_file": todo_state_file,
                }
            except Exception:
                continue

        return {"jobs": jobs_out, "sessions": sessions_out}

    def _restore_subagents_from_state(self, snapshot: Optional[Dict[str, Any]]) -> int:
        """
        Rehydrate subagent_sessions and subagent_jobs from a saved snapshot.
        In-flight jobs (queued/running/cancelling) are flipped to 'interrupted' because
        their worker threads died with the previous process.
        Returns the number of jobs marked interrupted.
        """
        if not isinstance(snapshot, dict):
            return 0

        sessions_in = snapshot.get("sessions") or {}
        jobs_in = snapshot.get("jobs") or {}
        interrupted_count = 0

        try:
            with self._subagent_lock:
                for sid, s in sessions_in.items():
                    if not isinstance(s, dict):
                        continue
                    todo_state_file = s.get("todo_state_file") or f".agent_todos.subagent.{str(sid)[:8]}.json"
                    try:
                        todo_mgr = TodoManager(todo_state_file)
                    except Exception:
                        todo_mgr = TodoManager(f".agent_todos.subagent.{str(sid)[:8]}.json")
                    hist = s.get("conversation_history") or []
                    if not hist:
                        # Keep a minimal system header so continuation calls can extend cleanly.
                        hist = [{"role": "system", "content": self.system_prompt}]
                    self.subagent_sessions[str(sid)] = {
                        "conversation_history": hist,
                        "conversation_summary": s.get("conversation_summary") or "",
                        "session_cwd": s.get("session_cwd") or self.session_cwd,
                        "created_at": s.get("created_at") or time.time(),
                        "parent_subagent_id": s.get("parent_subagent_id"),
                        "label": s.get("label"),
                        "todo_manager": todo_mgr,
                        "events": list(s.get("events") or []),
                    }

                now = time.time()
                for jid, j in jobs_in.items():
                    if not isinstance(j, dict):
                        continue
                    status = j.get("status")
                    if status in ("queued", "running", "cancelling"):
                        status = "interrupted"
                        interrupted_count += 1
                        interrupted_at = now
                    else:
                        interrupted_at = j.get("interrupted_at")
                    self.subagent_jobs[str(jid)] = {
                        "job_id": j.get("job_id") or str(jid),
                        "subagent_id": j.get("subagent_id"),
                        "parent_subagent_id": j.get("parent_subagent_id"),
                        "label": j.get("label"),
                        "status": status,
                        "created_at": j.get("created_at"),
                        "interrupted_at": interrupted_at,
                        # No live cancel_event for rehydrated jobs.
                        "cancel_event": None,
                        "result": j.get("result"),
                        "error": j.get("error"),
                    }
        except Exception:
            return interrupted_count

        return interrupted_count

    def _mark_active_subagents_interrupted(self) -> int:
        """
        Flip any queued/running/cancelling jobs to 'interrupted' and signal cancel
        so their worker threads get a chance to emit a final event. Called on Ctrl+C
        shutdown just before session save.
        """
        count = 0
        try:
            with self._subagent_lock:
                for j in self.subagent_jobs.values():
                    st = j.get("status")
                    if st in ("queued", "running", "cancelling"):
                        ev = j.get("cancel_event")
                        if ev is not None:
                            try:
                                ev.set()
                            except Exception:
                                pass
                        j["status"] = "interrupted"
                        j["interrupted_at"] = time.time()
                        count += 1
        except Exception:
            pass
        # Give worker threads a short window to emit a final 'cancelled' event
        # before we snapshot. They're daemon threads, so this is best-effort only.
        if count > 0:
            try:
                time.sleep(0.25)
            except Exception:
                pass
        return count

    def _write_session_snapshot_file(self, *, reason: str, token_estimate: Optional[int] = None, extra: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Persist a complete session snapshot to sessions/ (used on compaction so we never lose raw history).
        This intentionally does NOT honor active_session_id (snapshots should be append-only).
        """
        try:
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = f"session-{ts}-run-{self.run_id}-w{self.window_index:03d}-{reason}.json"
            path = str(self.sessions_dir / fname)
            now = time.time()
            payload: Dict[str, Any] = {
                "session_id": ts,
                "run_id": self.run_id,
                "window_index": self.window_index,
                "parent_session_file": self.parent_session_file,
                "reason": reason,
                "window_start": self.window_start_time,
                "window_end": now,
                # When this snapshot was written (useful for listing/debugging)
                "saved_at": now,
                "duration_seconds": now - float(self.window_start_time or now),
                "session_start": self.session_start_time,
                # For compatibility with older listing code; this is the snapshot timestamp, not necessarily true run end.
                "session_end": now,
                "session_cwd": self.session_cwd,
                "summary": self.conversation_summary,
                "total_messages": len(self.conversation_history),
                "token_estimate": token_estimate,
                "todos": (self.todo_manager.get_all_todos() if getattr(self, "todo_manager", None) else []),
                "messages": self.conversation_history,
                "subagents": self._serialize_subagents_for_save(),
            }
            if extra:
                payload.update(extra)
            self._atomic_write_json(path, payload)
            self.last_session_file = path
            return path
        except Exception:
            return None

    @staticmethod
    def _atomic_write_json(path: str, payload: Dict[str, Any]) -> None:
        """Write JSON via temp file + rename so readers never see partial JSON."""
        directory = os.path.dirname(os.path.abspath(path)) or "."
        tmp_path = os.path.join(directory, f".{os.path.basename(path)}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                try:
                    os.fsync(f.fileno())
                except Exception:
                    pass
            os.replace(tmp_path, path)
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════════
    #  COMPACTION SUBSYSTEM
    #
    #  Architecture (single-model, resume_prompt mode):
    #    1. _maybe_summarize_conversation(progress_callback=None) — entry point,
    #       checks token budget, delegates to _compact_conversation.
    #    2. _compact_conversation — sends full history to the model in one call,
    #       returns a dense compressed text.
    #    3. _build_compaction_resume_message — wraps compressed text in a minimal
    #       directive header (runtime-inserted, continue, don't summarize).
    #    4. Conversation replaced with [system_prompt, user(resume_wrapper)].
    #
    #  Progress tile (for Live contexts):
    #    _maybe_summarize_with_tile(thinking_live) — shows a Rich Panel progress
    #    bar via _make_compaction_panel; delegates to _maybe_summarize_conversation
    #    with a progress_callback that updates the Live tile.
    #
    #  Call sites:
    #    ~3354, ~6689 → _maybe_summarize_with_tile (Live context available)
    #    ~6359        → _maybe_summarize_conversation (subagent path, no Live)
    #
    #  Stall guard: _is_post_compaction_turn + _post_compaction_retried flag
    #  force a retry if the model responds with text-only after compaction.
    # ═══════════════════════════════════════════════════════════════════

    def _write_compaction_journal_entry(self, *, resume_text: str, before_tokens: Optional[int], after_tokens: Optional[int], pre_session_file: Optional[str], post_session_file: Optional[str]) -> Optional[str]:
        """
        Write a durable journal entry for long-term memory under agent_journal/.
        """
        try:
            self.agent_journal_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            fname = f"journal-{ts}-run-{self.run_id}-w{self.window_index:03d}.md"
            path = str(self.agent_journal_dir / fname)
            lines: List[str] = []
            lines.append(f"- timestamp: {ts}")
            lines.append(f"- run_id: {self.run_id}")
            lines.append(f"- window_index: {self.window_index}")
            if pre_session_file:
                lines.append(f"- pre_compaction_session: {pre_session_file}")
            if post_session_file:
                lines.append(f"- post_compaction_session: {post_session_file}")
            if before_tokens is not None:
                lines.append(f"- token_estimate_before: {before_tokens}")
            if after_tokens is not None:
                lines.append(f"- token_estimate_after: {after_tokens}")
            lines.append("")
            lines.append("## Resume context (auto-compacted)")
            lines.append("")
            # If resume_text is a JSON array, format it as readable conversation
            try:
                import json as _j2
                parsed = _j2.loads(resume_text)
                if isinstance(parsed, list):
                    for entry in parsed:
                        role = entry.get("role", "?")
                        content = (entry.get("content") or "")[:200]
                        tools = ""
                        if entry.get("tool_calls"):
                            tools = " [tools: " + ", ".join(
                                (tc.get("function", {}).get("name", "?") for tc in entry["tool_calls"])
                            ) + "]"
                        lines.append(f"[{role}]{tools} {content}")
                else:
                    lines.append((resume_text or "").strip()[:2000])
            except Exception:
                lines.append((resume_text or "").strip()[:2000])
            lines.append("")
            with open(path, "w") as f:
                f.write("\n".join(lines))
            return path
        except Exception:
            return None

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        if not text:
            return 0
        # More conservative heuristic: ~3 chars per token
        return max(1, int(len(text) / 3))

    def _estimate_messages_tokens(self, messages: List[Dict[str, Any]]) -> int:
        total = 0
        for m in messages:
            total += self._estimate_tokens(m.get("content", ""))
            # Small overhead for metadata / tool calls
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    total += self._estimate_tokens(tc.get("function", {}).get("name", ""))
                    total += self._estimate_tokens(tc.get("function", {}).get("arguments", ""))
            if m.get("name"):
                total += 4
        # Per-message overhead
        total += 20 * len(messages)
        # Safety margin (bump up to avoid underestimation)
        return int(total * 1.6)
    
    def _calculate_safe_max_tokens(self, messages: List[Dict[str, Any]], safety_margin: int = 2000) -> int:
        """
        Calculate safe max_tokens for completion based on current context size.
        Ensures we don't exceed model's total context limit (131072 tokens).
        
        Args:
            messages: Current conversation messages
            safety_margin: Extra tokens to reserve for safety (default 2000)
        
        Returns:
            Safe max_tokens value (capped at self.max_completion_tokens)
        """
        context_tokens = self._estimate_messages_tokens(messages)
        # Add overhead for system prompt, tool definitions, etc. (rough estimate)
        estimated_context = context_tokens + 5000
        available_tokens = self.model_max_tokens - estimated_context - safety_margin
        # Cap at reasonable maximum and ensure at least 512 tokens
        return max(512, min(self.max_completion_tokens, available_tokens))

    def _save_pre_compaction_snapshot(self, token_estimate: int, reason: str = "over_budget") -> None:
        """Persist the pre-compaction conversation window for training (without summaries)."""
        if not (self.log_conversations or self.snapshot_compactions):
            return
        try:
            self.compaction_snapshot_dir.mkdir(parents=True, exist_ok=True)
            # Exclude any prior system summaries
            filtered = [
                m for m in self.conversation_history
                if not (
                    m.get("role") == "system"
                    and str(m.get("content", "")).startswith("Conversation summary:")
                )
            ]
            serializable_messages = json.loads(json.dumps(filtered))
            signature = hashlib.sha1(
                json.dumps(serializable_messages, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if self._last_snapshot_signature == signature:
                return
            self._last_snapshot_signature = signature
            self._compaction_snapshot_idx += 1

            convo_id = datetime.fromtimestamp(self.session_start_time).strftime("%Y%m%d-%H%M%S")
            snapshot_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            snapshot_path = self.compaction_snapshot_dir / f"{convo_id}-{snapshot_id}.json"

            payload = {
                "conversation_id": convo_id,
                "snapshot_id": snapshot_id,
                "snapshot_index": self._compaction_snapshot_idx,
                "created_at": time.time(),
                "reason": reason,
                "token_count_full": token_estimate,
                "max_context_tokens": self.max_context_tokens,
                "messages": serializable_messages,
                "session_cwd": self.session_cwd,
            }
            with snapshot_path.open("w") as f:
                json.dump(payload, f, indent=2)
        except Exception:
            # Never block compaction on snapshot failures
            pass

    def _summarize_history(self, cutoff_index: int) -> None:
        """Summarize conversation_history[:cutoff_index] and replace it with a compact summary message.

        Keeps the last messages after cutoff intact, and prepends a compact summary as the
        *first user message* (right after the original system prompt). This prevents compaction
        from overwriting the real system prompt.
        """
        if cutoff_index <= 0:
            return
        prior = self.conversation_history[:cutoff_index]
        if not prior:
            return
        # Serialize prior messages compactly
        serialized = []
        for m in prior:
            role = m.get("role", "assistant")
            content = m.get("content", "")
            if not content and m.get("tool_calls"):
                # Describe tool calls briefly
                calls = []
                for tc in m["tool_calls"]:
                    fname = tc.get("function", {}).get("name", "")
                    calls.append(fname)
                content = f"Tool calls: {', '.join(calls)}"
            serialized.append(f"[{role}] {content}")
        prior_text = "\n".join(serialized)[-15000:]  # cap input to keep this summarization cheap

        # Ask the model for a concise summary
        try:
            summary_prompt = [
                {
                    "role": "system",
                    "content": (
                        "You are a concise summarizer. Summarize the prior conversation focusing on: "
                        "goals, key decisions, created/modified files, important command outcomes, and current todos. "
                        "Be brief but preserve critical details needed to continue."
                    ),
                },
                {
                    "role": "user",
                    "content": prior_text,
                },
            ]
            resp = self.client.chat(messages=summary_prompt, temperature=0.2, max_tokens=512)
            if resp and hasattr(resp, 'choices') and len(resp.choices) > 0:
                summary_text = resp.choices[0].message.content or ""
            else:
                summary_text = "(summary unavailable - empty response)"
        except Exception:
            summary_text = "(summary unavailable due to error)"

        # Store and rebuild history: keep system prompt, insert summary as first user message,
        # then keep the remainder after cutoff.
        self.conversation_summary = summary_text
        summary_message = {
            "role": "user",
            "content": f"Conversation summary (auto-compacted):\n{summary_text}",
        }
        remainder = self.conversation_history[cutoff_index:]

        # Preserve the original system prompt if present at the front of the history.
        new_history: List[Dict[str, Any]] = []
        if self.conversation_history and self.conversation_history[0].get("role") == "system":
            # Keep the first system message exactly as-is.
            new_history.append(self.conversation_history[0])

            # Avoid stacking multiple compaction summaries if we compact repeatedly.
            # If the next message is an earlier compaction summary, drop it and replace with the new one.
            if len(remainder) > 0:
                first = remainder[0]
                if first.get("role") == "system" and isinstance(first.get("content"), str) and first.get("content", "").startswith("Conversation summary:"):
                    remainder = remainder[1:]
                elif first.get("role") == "user" and isinstance(first.get("content"), str) and first.get("content", "").startswith("Conversation summary (auto-compacted):"):
                    remainder = remainder[1:]
        else:
            # If there was no system prompt recorded (should be rare), inject the canonical one.
            new_history.append({"role": "system", "content": self.system_prompt})

        new_history.append(summary_message)
        new_history.extend(remainder)
        self.conversation_history = new_history

    @staticmethod
    def _build_compaction_resume_message(resume_text: str) -> str:
        """Minimal wrapper — the compressed context speaks for itself."""
        return (
            "[COMPACTED CONTEXT — the conversation below was compressed to fit context limits. "
            "This was inserted by the runtime, NOT the user. "
            "Continue exactly where you left off. Do not summarize or acknowledge.]\n"
            "\n"
            + (resume_text or "")
        )

    def _is_post_compaction_turn(self) -> bool:
        """Return True if the most recent user message is a compaction resume injection."""
        try:
            for m in reversed(self.conversation_history or []):
                if m.get("role") == "user":
                    meta = m.get("meta") or {}
                    if isinstance(meta, dict) and meta.get("kind") == "compact_resume":
                        return True
                    # If we hit a different user message, it's not a post-compaction turn.
                    return False
            return False
        except Exception:
            return False

    def _compact_conversation(self) -> str:
        """Ask the model to compress the full conversation, returning summarized messages
        that preserve the conversation skeleton with same roles + tool calls, just shorter content."""
        import json as json_mod
        
        # Serialize the conversation as a structured array
        messages_summary: List[Dict[str, Any]] = []
        for m in self.conversation_history:
            entry = {"role": m.get("role", "assistant")}
            content = m.get("content", "") or m.get("reasoning_content", "") or ""
            # Bound individual messages
            if isinstance(content, str) and len(content) > 6000:
                content = content[:3000] + "\n…[truncated]…\n" + content[-2000:]
            entry["content"] = content
            if m.get("tool_calls"):
                entry["tool_calls"] = [
                    {
                        "id": tc.get("id", ""),
                        "function": {
                            "name": (tc.get("function") or {}).get("name", ""),
                            "arguments": ((tc.get("function") or {}).get("arguments", "") or "")[:200],
                        }
                    }
                    for tc in m["tool_calls"]
                ]
            if m.get("name"):
                entry["name"] = m["name"]
            if m.get("tool_call_id"):
                entry["tool_call_id"] = m["tool_call_id"]
            messages_summary.append(entry)

        system_instr = (
            "You are compressing a conversation history for an autonomous coding agent. "
            "Below is an array of messages. Return a JSON array with the SAME structure "
            "and SAME number of messages — but compress each message's content while preserving:\n\n"
            "- The user's original goal and exact wording (keep user messages verbatim)\n"
            "- Every concrete detail: file paths, commands, function names, line numbers, error messages\n"
            "- What has been done, what worked, what failed\n"
            "- The agent's current plan and exact next action\n\n"
            "Compress by removing: repetition, verbose explanations, conversational filler. "
            "Keep tool_calls, tool_call_id, and name fields untouched.\n\n"
            "Output ONLY a valid JSON array. No other text. The array must have exactly the same "
            "number of entries as the input."
        )

        try:
            resp = self.client.chat(
                messages=[
                    {"role": "system", "content": system_instr},
                    {"role": "user", "content": json_mod.dumps(messages_summary)},
                ],
                temperature=0.1,
                max_tokens=getattr(self.config, "compaction_summary_max_tokens", 8000) or 8000,
                response_format={"type": "json_object"},
            )
            if resp and hasattr(resp, "choices") and resp.choices:
                result = (resp.choices[0].message.content or "").strip()
                # Try to parse as JSON; if it wraps the array in an object, extract it
                try:
                    parsed = json_mod.loads(result)
                    if isinstance(parsed, dict):
                        for v in parsed.values():
                            if isinstance(v, list):
                                parsed = v
                                break
                    if isinstance(parsed, list):
                        # Convert back to conversation format preserving the skeleton
                        return json_mod.dumps(parsed)
                except Exception:
                    pass
                # Fallback: return raw text
                return result
        except Exception:
            pass
        return ""

    def _make_compaction_panel(self, pct: float, label: str = "") -> "Panel":
        """Return a Panel with a text-based progress bar for compaction."""
        import shutil
        term_w = shutil.get_terminal_size().columns
        bar_width = max(20, term_w - 10)
        filled = int(bar_width * pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        title_label = label or ("Compacting..." if pct < 100 else "Compacted")
        body = f"[dim]{bar} {pct:.0f}%[/dim]"
        if label:
            body += f"  [dim]{label}[/dim]"
        return Panel(
            body,
            border_style="dim",
            padding=(1, 1),
            title=f"[dim]🗜 {title_label}[/dim]",
        )

    def _maybe_summarize_with_tile(self, thinking_live=None) -> None:
        """Check and run compaction, showing a real-progress tile via the Live context."""
        # Quick pre-check: do we even need compaction?
        try:
            tokens = self._estimate_messages_tokens(self.conversation_history)
        except Exception:
            tokens = None
        if isinstance(tokens, int) and tokens <= self.max_context_tokens:
            return

        # Progress callback that updates the Live tile
        def _update_tile(pct: float, label: str = "") -> None:
            if thinking_live is not None:
                try:
                    thinking_live.update(self._make_compaction_panel(pct, label))
                    sys.stdout.flush()
                except Exception:
                    pass

        # Show initial tile
        _update_tile(0, "Checking context...")

        self._maybe_summarize_conversation(progress_callback=_update_tile)

        # Show completion
        _update_tile(100, "Compacted")
        time.sleep(0.3)


    def _maybe_summarize_conversation(self, progress_callback=None) -> None:
        # Capture pre-compaction stats
        try:
            before_tokens = self._estimate_messages_tokens(self.conversation_history)
        except Exception:
            before_tokens = None
        before_messages = len(self.conversation_history)

        # Under budget — nothing to do
        tokens = before_tokens if isinstance(before_tokens, int) else None
        if tokens is None:
            try:
                tokens = self._estimate_messages_tokens(self.conversation_history)
            except Exception:
                tokens = None
        if tokens is None or (isinstance(tokens, int) and tokens <= self.max_context_tokens):
            return

        # Persist pre-compaction snapshot for training
        self._save_pre_compaction_snapshot(tokens, reason="over_budget")

        # Single model call: compress the full conversation
        if progress_callback:
            try: progress_callback(15, "Compressing with model...")
            except Exception: pass
        resume_text = self._compact_conversation()
        if not resume_text:
            # Fallback: last 40 messages as raw text
            try:
                recent = self.conversation_history[-40:] if len(self.conversation_history) > 40 else list(self.conversation_history)
                fallback_lines = []
                for m in recent:
                    role = m.get("role", "assistant")
                    content = m.get("content", "") or m.get("reasoning_content", "")
                    if m.get("tool_calls"):
                        calls = [((tc.get("function") or {}).get("name", "")) for tc in (m.get("tool_calls") or [])]
                        content = (content + "\n" if content else "") + "[Tools: " + ", ".join(calls) + "]"
                    if isinstance(content, str) and len(content) > 2000:
                        content = content[:1000] + "\n…\n" + content[-600:]
                    fallback_lines.append(f"[{role}] {content}")
                resume_text = "FALLBACK (model unavailable)\n\n" + "\n".join(fallback_lines)
            except Exception:
                resume_text = "FALLBACK (model unavailable). Please restate what you want next."

        if progress_callback:
            try: progress_callback(70, "Writing snapshots...")
            except Exception: pass

        # Persist pre-compaction snapshot file
        pre_session = self._write_session_snapshot_file(reason="pre_compaction", token_estimate=before_tokens, extra={
            "before_messages": before_messages,
        })

        self.parent_session_file = pre_session or self.parent_session_file
        self.window_index += 1
        self.window_start_time = time.time()

        # Reconstruct conversation from compressed message array (preserving skeleton)
        import json as _json
        try:
            compressed_msgs = _json.loads(resume_text)
            if isinstance(compressed_msgs, list) and len(compressed_msgs) > 0:
                # Reconstruct: keep system prompt + compressed messages
                reconstructed = [{"role": "system", "content": self.system_prompt}]
                for cm in compressed_msgs:
                    if not isinstance(cm, dict):
                        continue
                    msg = {"role": cm.get("role", "assistant")}
                    if cm.get("content"):
                        msg["content"] = cm["content"]
                    if cm.get("tool_calls"):
                        msg["tool_calls"] = cm["tool_calls"]
                    if cm.get("tool_call_id"):
                        msg["tool_call_id"] = cm["tool_call_id"]
                    if cm.get("name"):
                        msg["name"] = cm["name"]
                    reconstructed.append(msg)
                self.conversation_history = reconstructed
            else:
                raise ValueError("empty or invalid compressed array")
        except Exception:
            # Fallback: wrap as resume text
            wrapped = self._build_compaction_resume_message(resume_text) if resume_text else "FALLBACK: compaction failed. Please restate your goal."
            self.conversation_history = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": wrapped, "meta": {"auto_injected": True, "kind": "compact_resume"}},
            ]

        after_tokens = self._estimate_messages_tokens(self.conversation_history)
        post_session = self._write_session_snapshot_file(reason="post_compaction", token_estimate=after_tokens, extra={
            "after_messages": len(self.conversation_history),
        })
        self.parent_session_file = post_session or self.parent_session_file
        journal_path = self._write_compaction_journal_entry(
            resume_text=resume_text,
            before_tokens=before_tokens,
            after_tokens=after_tokens,
            pre_session_file=pre_session,
            post_session_file=post_session,
        )

        if journal_path:
            try:
                self.conversation_history[1]["content"] += f"\n\n(Agent journal entry saved: {journal_path})"
            except Exception:
                pass

        if progress_callback:
            try: progress_callback(95, "Finalizing...")
            except Exception: pass

        # User-visible notice
        try:
            self._pending_compaction_notice = {
                "type": "compact",
                "before_tokens": before_tokens,
                "after_tokens": after_tokens,
                "before_messages": before_messages,
                "after_messages": len(self.conversation_history),
            }
        except Exception:
            pass
        return

    # ═══════════════════════════════════════════════════════════════════
    #  END COMPACTION SUBSYSTEM
    # ═══════════════════════════════════════════════════════════════════

    def display_todos(self):
        """Display current todo list in a compact tree format"""
        todos = self.todo_manager.get_all_todos()
        if not todos:
            console.print("[dim]📋 No todos yet. The agent will create them for complex tasks.[/dim]")
            return
        
        # Group by status
        pending = [t for t in todos if t["status"] == "pending"]
        in_progress = [t for t in todos if t["status"] == "in_progress"]
        completed = [t for t in todos if t["status"] == "completed"]
        
        # Create a compact display
        tree = Tree("📋 [bold cyan]Todos[/bold cyan]")
        
        if in_progress:
            for todo in in_progress:
                tree.add(f"[yellow]▶[/yellow] {todo['content']}")
        
        if pending:
            for todo in pending:
                tree.add(f"[white]☐[/white] {todo['content']}")
        
        if completed:
            for todo in completed:
                tree.add(f"[green]✓[/green] {todo['content']}")
        
        console.print(tree)

    def display_help(self):
        """Display available interactive commands."""
        help_body = (
            "[bold]Interactive commands[/bold]\n"
            "\n"
            "[dim]Core[/dim]\n"
            "[cyan]•[/cyan] [bold white]/help[/bold white]  show this help\n"
            "[cyan]•[/cyan] [bold white]/whoami[/bold white]  show signed-in billing account\n"
            "[cyan]•[/cyan] [bold white]/stats[/bold white]  usage stats + token heatmap\n"
            "[cyan]•[/cyan] [bold white]/wrap[/bold white]  shareable daily wrap card ([dim]/wrap week[/dim], [dim]/wrap all[/dim])\n"
            "[cyan]•[/cyan] [bold white]/todos[/bold white]  view todos\n"
            "[cyan]•[/cyan] [bold white]/clear[/bold white]  clear conversation history\n"
            "[cyan]•[/cyan] [bold white]exit[/bold white] / [bold white]quit[/bold white]  exit the agent\n"
            "[cyan]•[/cyan] [bold white]Ctrl+C[/bold white]  interrupt (twice to exit)\n"
            "\n"
            "[dim]Sessions[/dim]\n"
            "[cyan]•[/cyan] [bold white]sweet resume[/bold white]  resume last session\n"
            "[cyan]•[/cyan] [bold white]sweet start --session {sessionid}[/bold white]  resume a specific session\n"
            "\n"
            "[dim]Autopilot[/dim]\n"
            "[cyan]•[/cyan] [bold white]/workfor 45m[/bold white]  autopilot for 45m (starts after your next prompt)\n"
            "[cyan]•[/cyan] [bold white]/workfor forever[/bold white]  autopilot until stopped\n"
            "[cyan]•[/cyan] [bold white]/workoff[/bold white]  stop autopilot\n"
            "[cyan]•[/cyan] [bold white]/workstatus[/bold white]  show autopilot status\n"
            "\n"
            "[dim]Background jobs[/dim]\n"
            "[cyan]•[/cyan] [bold white]/jobs[/bold white]  list background jobs\n"
            "[cyan]•[/cyan] [bold white]/kill <job_id>[/bold white]  stop a background job\n"
            "\n"
            "[dim]Paste helpers (macOS)[/dim]\n"
            "[cyan]•[/cyan] [bold white]/paste[/bold white]  paste clipboard\n"
            "[cyan]•[/cyan] [bold white]/pastefile <path>[/bold white]  paste a file\n"
            "\n"
            "[dim]Shell[/dim]\n"
            "[cyan]•[/cyan] [bold white]cd <path>[/bold white]  change working directory for the session\n"
        )
        console.print(Panel(Text.from_markup(help_body), title="[bold cyan]Help[/bold cyan]", border_style="cyan", padding=(1, 2), expand=True))

    def display_billing_identity(self):
        """Display the billing account identity for the current CLI session."""
        if not self.billing_client:
            console.print("[dim]Not using billing relay in this session.[/dim]")
            return
        info = self.billing_client.get_account_info()
        email = (info.get("email") or "").strip()
        if info.get("ok") and email:
            console.print(f"[green]✓[/green] Signed in as [bold]{email}[/bold]")
            return
        if email:
            console.print(f"[yellow]⚠️[/yellow] Signed-in account (cached): [bold]{email}[/bold]")
            if info.get("message"):
                console.print(f"[dim]{info.get('message')}[/dim]")
            return
        console.print("[yellow]⚠️[/yellow] Billing account email unavailable. Try logging in again.")

    def _stats_file_path(self) -> Path:
        # Keep it stable and local; safe for both repo + packaged installs.
        return Path("data") / "stats.json"

    def _load_stats(self) -> Dict[str, Any]:
        p = self._stats_file_path()
        loaded: Optional[Dict[str, Any]] = None
        try:
            if p.exists():
                loaded = json.loads(p.read_text("utf-8"))
        except Exception:
            loaded = None
        if loaded is None:
            loaded = {
                "version": 2,
                "created_at": int(time.time()),
                "updated_at": int(time.time()),
                "first_used_date": datetime.now().strftime("%Y-%m-%d"),
                "daily_tokens": {},   # "YYYY-MM-DD" -> {"estimated": int, "actual": int|None}
                "daily_turns": {},    # "YYYY-MM-DD" -> int
                "daily_tools": {},    # "YYYY-MM-DD" -> {"write_file": int, ...}
                "daily_lines": {},    # "YYYY-MM-DD" -> {"added": int, "removed": int}
                "daily_files": {},    # "YYYY-MM-DD" -> [absolute_path, ...] (deduped)
                "daily_seconds": {},  # "YYYY-MM-DD" -> active seconds (sum of session durations)
            }
            return loaded

        # Migrate v1 → v2 in-place. v1 only had daily_tokens/daily_turns.
        # Older payloads silently get the new keys with empty maps so the wrap
        # card renders cleanly (rows just collapse when zero).
        loaded.setdefault("version", 1)
        for key in ("daily_tokens", "daily_turns", "daily_tools",
                    "daily_lines", "daily_files", "daily_seconds"):
            if not isinstance(loaded.get(key), dict):
                loaded[key] = {}
        if not loaded.get("first_used_date"):
            try:
                token_dates = sorted((loaded.get("daily_tokens") or {}).keys())
                if token_dates:
                    loaded["first_used_date"] = token_dates[0]
                else:
                    loaded["first_used_date"] = datetime.now().strftime("%Y-%m-%d")
            except Exception:
                loaded["first_used_date"] = datetime.now().strftime("%Y-%m-%d")
        if int(loaded.get("version") or 1) < 2:
            loaded["version"] = 2
        return loaded

    def _save_stats(self, stats: Dict[str, Any]) -> None:
        p = self._stats_file_path()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        try:
            stats["updated_at"] = int(time.time())
        except Exception:
            pass
        try:
            tmp = p.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(stats, indent=2, sort_keys=True), "utf-8")
            tmp.replace(p)
        except Exception:
            # Best-effort; never crash the agent for stats.
            pass

    def _record_token_usage_for_today(self, *, estimated_tokens: int, actual_tokens: Optional[int] = None) -> None:
        if not isinstance(estimated_tokens, int):
            try:
                estimated_tokens = int(estimated_tokens or 0)
            except Exception:
                estimated_tokens = 0
        if estimated_tokens < 0:
            estimated_tokens = 0
        today = datetime.now().strftime("%Y-%m-%d")
        stats = self._load_stats()
        daily = stats.get("daily_tokens") or {}
        entry = daily.get(today) or {}
        try:
            entry_est = int(entry.get("estimated") or 0)
        except Exception:
            entry_est = 0
        entry["estimated"] = int(entry_est + estimated_tokens)
        # Only record actual if provided (best-effort; many providers/streams don't return usage).
        if actual_tokens is not None:
            try:
                entry_act = int(entry.get("actual") or 0)
            except Exception:
                entry_act = 0
            entry["actual"] = int(entry_act + int(actual_tokens))
        else:
            # Preserve existing "actual" if present.
            if "actual" not in entry:
                entry["actual"] = None
        daily[today] = entry
        stats["daily_tokens"] = daily

        turns = stats.get("daily_turns") or {}
        try:
            turns[today] = int(turns.get(today) or 0) + 1
        except Exception:
            turns[today] = 1
        stats["daily_turns"] = turns

        self._save_stats(stats)

    def _record_tool_use(self, name: str, args: Optional[Dict[str, Any]], result: Optional[Dict[str, Any]]) -> None:
        """
        Best-effort per-tool instrumentation called once per completed tool
        result. Updates daily_tools (call counts), daily_lines (added/removed),
        and daily_files (deduped list of touched paths). Never raises — stats
        are advisory; failure here must not affect the agent's main loop.
        """
        try:
            if not name or not isinstance(name, str):
                return
            today = datetime.now().strftime("%Y-%m-%d")
            stats = self._load_stats()

            tools = stats.setdefault("daily_tools", {})
            day_tools = tools.setdefault(today, {})
            try:
                day_tools[name] = int(day_tools.get(name) or 0) + 1
            except Exception:
                day_tools[name] = 1

            res = result if isinstance(result, dict) else {}
            ok = bool(res.get("success", True)) if res else True

            # Lines added/removed — only when the tool actually succeeded.
            added = 0
            removed = 0
            if ok:
                if name == "write_file":
                    try:
                        added = max(0, int(res.get("lines") or 0))
                    except Exception:
                        added = 0
                elif name == "modify_file":
                    try:
                        added = max(0, int(res.get("lines_inserted") or 0))
                    except Exception:
                        added = 0
                    try:
                        removed = max(0, int(res.get("lines_deleted") or 0))
                    except Exception:
                        removed = 0
            if added or removed:
                lines = stats.setdefault("daily_lines", {})
                day_lines = lines.setdefault(today, {})
                try:
                    day_lines["added"] = int(day_lines.get("added") or 0) + added
                except Exception:
                    day_lines["added"] = added
                try:
                    day_lines["removed"] = int(day_lines.get("removed") or 0) + removed
                except Exception:
                    day_lines["removed"] = removed

            # Files touched — deduped per day. Cap to a reasonable size to keep
            # stats.json bounded if someone runs an enormous batch.
            if ok and name in ("write_file", "modify_file", "read_file"):
                path = None
                try:
                    if isinstance(args, dict):
                        path = args.get("file_path") or args.get("path")
                except Exception:
                    path = None
                if isinstance(path, str) and path.strip():
                    files = stats.setdefault("daily_files", {})
                    day_files = files.setdefault(today, [])
                    if not isinstance(day_files, list):
                        day_files = []
                    if path not in day_files:
                        day_files.append(path)
                        if len(day_files) > 5000:
                            day_files = day_files[-5000:]
                        files[today] = day_files

            self._save_stats(stats)
        except Exception:
            pass

    def _record_active_seconds_for_today(self, seconds: int) -> None:
        """
        Bumps daily_seconds[today] by `seconds`. Called from save_session so
        the wrap card can show "pair-programming time". Idempotent across
        repeated saves in one process via _last_active_seconds_recorded.
        """
        try:
            seconds = max(0, int(seconds or 0))
        except Exception:
            return
        if seconds <= 0:
            return
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            stats = self._load_stats()
            sec = stats.setdefault("daily_seconds", {})
            try:
                sec[today] = int(sec.get(today) or 0) + seconds
            except Exception:
                sec[today] = seconds
            self._save_stats(stats)
        except Exception:
            pass

    def _render_token_heatmap(self, tokens_by_day: Dict[str, int], *, days: int = 30) -> Group:
        # Modern GitHub-style heatmap for the last N days (default 30).
        today_d = datetime.now().date()
        days = max(7, int(days or 30))
        start = today_d - timedelta(days=days - 1)
        week_count = int(math.ceil(days / 7.0))

        # Determine scale based on the visible window.
        max_val = 0
        for i in range(days):
            d = start + timedelta(days=i)
            v = int(tokens_by_day.get(d.isoformat(), 0) or 0)
            if v > max_val:
                max_val = v

        palette = [
            "#161b22",  # 0
            "#0e4429",  # low
            "#006d32",
            "#26a641",
            "#39d353",  # high
        ]

        def color_for(v: int) -> str:
            v = int(v or 0)
            if v <= 0 or max_val <= 0:
                return palette[0]
            s = math.log1p(v) / max(1e-9, math.log1p(max_val))
            idx = 1 + int(min(3.999, max(0.0, s * 4.0)))
            return palette[max(1, min(4, idx))]

        heat = Table(
            box=box.SQUARE,
            show_header=False,
            pad_edge=True,
            show_lines=True,
        )
        heat.add_column("", justify="right", style="dim", no_wrap=True, width=3)
        for _ in range(week_count):
            heat.add_column("", justify="center", no_wrap=True, width=3)

        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for row in range(7):
            cells: List[Any] = [day_names[row]]
            for w in range(week_count):
                idx = w * 7 + row
                if idx >= days:
                    cells.append(Text("  ", style="dim"))
                    continue
                d = start + timedelta(days=idx)
                v = int(tokens_by_day.get(d.isoformat(), 0) or 0)
                c = color_for(v)
                fg = "white" if v > 0 else "dim"
                cells.append(Text(f"{d.day:2d}", style=f"{fg} on {c}"))
            heat.add_row(*cells)

        total = sum(int(tokens_by_day.get((start + timedelta(days=i)).isoformat(), 0) or 0) for i in range(days))
        avg = int(total / max(1, days))
        max_day = None
        max_day_val = 0
        for i in range(days):
            d = start + timedelta(days=i)
            v = int(tokens_by_day.get(d.isoformat(), 0) or 0)
            if v > max_day_val:
                max_day_val = v
                max_day = d

        legend = Table.grid(padding=(0, 1))
        legend.add_column(justify="right")
        legend.add_column()
        legend_cells = [Text("  ", style=f"on {c}") for c in palette]
        range_text = f"{start.isoformat()} → {today_d.isoformat()}"
        peak_text = f"{max_day.isoformat()} ({max_day_val:,})" if max_day else "—"
        legend.add_row(Text("less", style="dim"), Text.assemble(*legend_cells, Text("  more", style="dim")))
        legend.add_row(Text("Range", style="dim"), Text(range_text))
        legend.add_row(Text("Avg/day", style="dim"), Text(f"{avg:,}"))
        legend.add_row(Text("Peak day", style="dim"), Text(peak_text))

        return Group(heat, legend)

    def display_stats(self) -> None:
        stats = self._load_stats()
        daily_tokens = stats.get("daily_tokens") or {}
        daily_turns = stats.get("daily_turns") or {}

        # Prefer actual if available; fall back to estimated.
        tokens_by_day: Dict[str, int] = {}
        for k, v in daily_tokens.items():
            try:
                if isinstance(v, dict) and v.get("actual") is not None:
                    tokens_by_day[str(k)] = int(v.get("actual") or 0)
                elif isinstance(v, dict):
                    tokens_by_day[str(k)] = int(v.get("estimated") or 0)
                else:
                    tokens_by_day[str(k)] = int(v or 0)
            except Exception:
                tokens_by_day[str(k)] = 0

        today_s = datetime.now().strftime("%Y-%m-%d")
        today_tokens = int(tokens_by_day.get(today_s, 0) or 0)
        today_turns = int(daily_turns.get(today_s, 0) or 0)

        def sum_range(days_back: int) -> int:
            total = 0
            for i in range(int(days_back)):
                d = (datetime.now().date() - timedelta(days=i)).isoformat()
                total += int(tokens_by_day.get(d, 0) or 0)
            return int(total)

        last7 = sum_range(7)
        last30 = sum_range(30)
        all_time = int(sum(int(v or 0) for v in tokens_by_day.values()) or 0)

        # Streaks (days with >0 tokens)
        longest = 0
        current = 0
        dates_sorted: List[str] = sorted(tokens_by_day.keys())
        prev: Optional[date] = None
        for ds in dates_sorted:
            try:
                dd = datetime.strptime(ds, "%Y-%m-%d").date()
            except Exception:
                continue
            v = int(tokens_by_day.get(ds, 0) or 0)
            if prev is None or (dd - prev).days != 1:
                current = 0
            if v > 0:
                current += 1
                longest = max(longest, current)
            else:
                current = 0
            prev = dd

        cur_streak = 0
        for i in range(3650):  # cap at ~10y
            ds = (datetime.now().date() - timedelta(days=i)).isoformat()
            if int(tokens_by_day.get(ds, 0) or 0) > 0:
                cur_streak += 1
            else:
                break

        summary = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan", expand=True, pad_edge=False)
        summary.add_column("Metric", style="bold white", no_wrap=True)
        summary.add_column("Value", style="bold green", justify="right", no_wrap=True)
        summary.add_column("Details", style="dim", overflow="fold")
        summary.add_row("Today", f"{today_tokens:,}", f"{today_turns} turns")
        summary.add_row("Last 7 days", f"{last7:,}", "")
        summary.add_row("Last 30 days", f"{last30:,}", "")
        summary.add_row("All time", f"{all_time:,}", "")
        summary.add_row("Streak", f"{cur_streak} days", f"best {longest}")

        heatmap = self._render_token_heatmap(tokens_by_day, days=30)
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        note = Text(f"Updated {updated_at}. Token counts use exact usage when available; otherwise estimated.", style="dim")
        console.print(
            Panel(
                Group(
                    summary,
                    Text(""),
                    Panel(heatmap, title="[bold]Activity[/bold]", border_style="dim", padding=(1, 1)),
                    Text(""),
                    note,
                ),
                title="[bold cyan]Stats[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
                expand=True,
            )
        )

    def _aggregate_wrap_stats(self, scope: str = "today") -> Dict[str, Any]:
        """
        Roll up the on-disk daily stats into the totals the wrap card needs.

        scope: "today" | "week" | "all"
        Returns a dict with: lines_added, lines_removed, files_touched,
        commands, subagents, web_searches, tokens, turns, top_tool, seconds,
        streak_current, streak_best, day_label, scope_label.
        """
        scope_norm = (scope or "today").strip().lower()
        if scope_norm not in ("today", "week", "all"):
            scope_norm = "today"

        stats = self._load_stats()
        daily_tokens_raw = stats.get("daily_tokens") or {}
        daily_turns = stats.get("daily_turns") or {}
        daily_tools = stats.get("daily_tools") or {}
        daily_lines = stats.get("daily_lines") or {}
        daily_files = stats.get("daily_files") or {}
        daily_seconds = stats.get("daily_seconds") or {}

        # Normalize token-by-day map (prefer actual when present).
        tokens_by_day: Dict[str, int] = {}
        for k, v in daily_tokens_raw.items():
            try:
                if isinstance(v, dict) and v.get("actual") is not None:
                    tokens_by_day[str(k)] = int(v.get("actual") or 0)
                elif isinstance(v, dict):
                    tokens_by_day[str(k)] = int(v.get("estimated") or 0)
                else:
                    tokens_by_day[str(k)] = int(v or 0)
            except Exception:
                tokens_by_day[str(k)] = 0

        # Pick the target date keys for this scope.
        today_d = datetime.now().date()
        if scope_norm == "today":
            target_keys = [today_d.isoformat()]
            scope_label = "today"
            day_label = today_d.strftime("%a, %b %-d") if hasattr(today_d, "strftime") else today_d.isoformat()
        elif scope_norm == "week":
            target_keys = [(today_d - timedelta(days=i)).isoformat() for i in range(7)]
            scope_label = "this week"
            day_label = f"{(today_d - timedelta(days=6)).strftime('%b %-d')} — {today_d.strftime('%b %-d')}"
        else:
            target_keys = sorted(set(list(tokens_by_day.keys())
                                     + list(daily_tools.keys())
                                     + list(daily_lines.keys())
                                     + list(daily_files.keys())
                                     + list(daily_seconds.keys())
                                     + list(daily_turns.keys())))
            scope_label = "all-time"
            first = stats.get("first_used_date") or (target_keys[0] if target_keys else today_d.isoformat())
            day_label = f"since {first}"

        target_set = set(target_keys)

        def sum_int(d: Dict[str, Any], coerce=lambda x: int(x or 0)) -> int:
            t = 0
            for k in target_set:
                try:
                    t += int(coerce(d.get(k, 0)))
                except Exception:
                    pass
            return int(t)

        tokens = sum_int(tokens_by_day)
        turns = sum_int(daily_turns)
        seconds = sum_int(daily_seconds)

        # Per-tool aggregate
        tool_totals: Dict[str, int] = {}
        for k in target_set:
            day = daily_tools.get(k) or {}
            if isinstance(day, dict):
                for tname, c in day.items():
                    try:
                        tool_totals[str(tname)] = int(tool_totals.get(str(tname), 0)) + int(c or 0)
                    except Exception:
                        pass

        commands = int(tool_totals.get("run_command", 0))
        subagents = int(tool_totals.get("run_subagent_async", 0)) + int(tool_totals.get("run_subagent", 0))
        web_searches = int(tool_totals.get("web_search", 0))

        # Lines added/removed
        lines_added = 0
        lines_removed = 0
        for k in target_set:
            entry = daily_lines.get(k) or {}
            if isinstance(entry, dict):
                try:
                    lines_added += int(entry.get("added") or 0)
                except Exception:
                    pass
                try:
                    lines_removed += int(entry.get("removed") or 0)
                except Exception:
                    pass

        # Files touched (deduped across the scope)
        files_set: set = set()
        for k in target_set:
            paths = daily_files.get(k) or []
            if isinstance(paths, list):
                for p in paths:
                    if isinstance(p, str) and p:
                        files_set.add(p)
        files_touched = len(files_set)

        # Top tool by call count, but skip "noisy" reads when other tools exist
        # so the wrap card surfaces something more flattering than `read_file`.
        top_tool = None
        if tool_totals:
            ranked = sorted(tool_totals.items(), key=lambda kv: (-int(kv[1] or 0), kv[0]))
            for name, count in ranked:
                if name == "read_file" and len(ranked) > 1:
                    continue
                top_tool = (name, int(count))
                break
            if top_tool is None and ranked:
                top_tool = (ranked[0][0], int(ranked[0][1]))

        # Streaks (days with any recorded activity at all — token, turn, or tool).
        active_days_set: set = set()
        for src in (tokens_by_day, daily_turns, daily_tools, daily_lines, daily_seconds):
            for k, v in (src or {}).items():
                if isinstance(v, dict):
                    if any(v.values()):
                        active_days_set.add(str(k))
                elif v:
                    active_days_set.add(str(k))

        cur_streak = 0
        for i in range(3650):
            ds = (today_d - timedelta(days=i)).isoformat()
            if ds in active_days_set:
                cur_streak += 1
            else:
                break

        longest = 0
        run = 0
        prev: Optional[date] = None
        for ds in sorted(active_days_set):
            try:
                dd = datetime.strptime(ds, "%Y-%m-%d").date()
            except Exception:
                continue
            if prev is not None and (dd - prev).days == 1:
                run += 1
            else:
                run = 1
            longest = max(longest, run)
            prev = dd

        return {
            "scope": scope_norm,
            "scope_label": scope_label,
            "day_label": day_label,
            "tokens": int(tokens),
            "turns": int(turns),
            "seconds": int(seconds),
            "lines_added": int(lines_added),
            "lines_removed": int(lines_removed),
            "files_touched": int(files_touched),
            "commands": int(commands),
            "subagents": int(subagents),
            "web_searches": int(web_searches),
            "top_tool": top_tool,
            "streak_current": int(cur_streak),
            "streak_best": int(longest),
        }

    @staticmethod
    def _format_seconds_human(seconds: int) -> str:
        """Compact human-friendly duration. 9240 → '2h 34m', 320 → '5m', 8 → '8s'."""
        try:
            s = max(0, int(seconds or 0))
        except Exception:
            return "0s"
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        if h:
            return f"{h}h {m}m" if m else f"{h}h"
        if m:
            return f"{m}m" if sec < 30 else f"{m}m {sec}s"
        return f"{sec}s"

    @staticmethod
    def _prettify_tool_name(name: str) -> str:
        """Convert snake_case tool names to a friendlier label for the wrap card."""
        if not name:
            return ""
        special = {
            "write_file": "write_file",
            "read_file": "read_file",
            "modify_file": "modify_file",
            "run_command": "run_command",
            "web_search": "web_search",
            "list_directory": "list_directory",
            "manage_todos": "manage_todos",
            "run_subagent_async": "run_subagent_async",
            "poll_subagent": "poll_subagent",
            "list_subagents": "list_subagents",
            "cancel_subagent_job": "cancel_subagent_job",
        }
        return special.get(name, name)

    # Sweet block letters used as the brand mark on the wrap card. Kept as a
    # class-level constant so the card and the startup banner share the exact
    # same artwork — diverging them would weaken the brand recall.
    _SWEET_LOGO_LINES: List[str] = [
        "  ███████╗██╗    ██╗███████╗███████╗████████╗██╗",
        "  ██╔════╝██║    ██║██╔════╝██╔════╝╚══██╔══╝██║",
        "  ███████╗██║ █╗ ██║█████╗  █████╗     ██║   ██║",
        "  ╚════██║██║███╗██║██╔══╝  ██╔══╝     ██║   ╚═╝",
        "  ███████║╚███╔███╔╝███████╗███████╗   ██║   ██╗",
        "  ╚══════╝ ╚══╝╚══╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝",
    ]

    @staticmethod
    def _render_sweet_logo(*, animate_phase: int = 0) -> Text:
        """
        Render the Sweet block-letter logo with a diagonal HSV rainbow
        gradient. Reused on the wrap card so screenshots carry the same
        visual identity as the startup banner. `animate_phase` shifts the
        gradient horizontally so callers can animate it via Rich Live.
        """
        def _hsv_hex(h_deg: float, s: float = 0.78, v: float = 1.0) -> str:
            r, g, b = colorsys.hsv_to_rgb(
                (h_deg % 360.0) / 360.0,
                max(0.0, min(1.0, s)),
                max(0.0, min(1.0, v)),
            )
            return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

        out = Text(justify="center")
        for row, line in enumerate(CLIAgent._SWEET_LOGO_LINES):
            for col, ch in enumerate(line):
                if ch == " ":
                    out.append(ch)
                else:
                    hue = (col * 9.0) + (row * 18.0) + (animate_phase * 24.0)
                    out.append(ch, style=f"bold {_hsv_hex(hue)}")
            out.append("\n")
        return out

    @staticmethod
    def _build_terminal_chrome(width: int, label: str) -> Table:
        """
        Faux macOS-Terminal title bar: red/yellow/green traffic-light dots on
        the left and a filename-style label on the right. Reads instantly as
        "this is a real terminal" in screenshots, which gives the card more
        credibility than a plain Panel.
        """
        chrome = Table.grid(expand=True)
        chrome.add_column(justify="left", no_wrap=True, ratio=1)
        chrome.add_column(justify="right", no_wrap=True, ratio=1)
        dots = Text.assemble(
            Text("● ", style="bold red"),
            Text("● ", style="bold yellow"),
            Text("●", style="bold green"),
        )
        chrome.add_row(dots, Text(label, style="dim"))
        return chrome

    @staticmethod
    def _build_branded_footer(width: int, *, cursor_visible: bool = True) -> Text:
        """
        Prompt-styled footer: '❯ sweetcli.com  •  #builtwithsweet  ▊'.
        `cursor_visible` toggles the trailing block cursor so the caller can
        animate a blink with Rich Live. The cursor settles on a solid block
        for the static screenshot frame.
        """
        cursor_glyph = "▊" if cursor_visible else " "
        return Text.assemble(
            Text("  ❯ ", style="bold green"),
            Text("sweetcli.com", style="bold cyan underline"),
            Text("   •   ", style="dim"),
            Text("#builtwithsweet", style="bold magenta"),
            Text("   ", style="dim"),
            Text(cursor_glyph, style="bold white blink" if cursor_visible else "dim"),
        )

    @staticmethod
    def _shine_span(
        plain: str,
        frame: int,
        *,
        base_style: str = "white",
        shine_style: str = "bold bright_white",
        band: int = 4,
    ) -> Text:
        """A moving highlight band across plain text (no markup — safe for paths)."""
        t = Text()
        if not plain:
            return t
        n = len(plain)
        cycle_len = n + band + 2
        head = int(frame) % cycle_len
        for i, ch in enumerate(plain):
            if head <= i < min(head + band, n):
                t.append(ch, style=shine_style)
            else:
                t.append(ch, style=base_style)
        return t

    @staticmethod
    def _tier_tuple_from_slug(raw: str) -> Tuple[str, str, str, str]:
        """Map a free-form slug to (tier_key, badge_text, base_style, shine_style)."""
        s = (raw or "").strip().lower()
        if not s:
            return ("unknown", "Sweet", "dim white", "bold cyan")
        if "max" in s or s in ("sweet_max", "sweet-max"):
            return ("max", "⚡ SWEET MAX ⚡", "bold magenta", "bold bright_yellow")
        if "pro" in s or "professional" in s:
            return ("pro", "SWEET PRO", "bold cyan", "bold white")
        if any(x in s for x in ("team", "enterprise", "business")):
            return ("team", "TEAM", "bold blue", "bold white")
        if any(x in s for x in ("starter", "free", "trial", "hobby", "basic", "plus")):
            return ("free", "STARTER", "dim white", "bold green")
        u = raw.strip()
        return ("unknown", (u[:32].upper() if u else "Sweet"), "dim", "bold white")

    @staticmethod
    def _infer_tier_slug_from_plan(plan: Dict[str, Any]) -> Optional[str]:
        if not isinstance(plan, dict) or not plan:
            return None
        for key in (
            "subscription_tier",
            "tier",
            "plan_tier",
            "billing_tier",
            "plan_key",
            "plan_name",
            "plan",
            "product_name",
        ):
            v = plan.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        sub = plan.get("subscription")
        if isinstance(sub, dict):
            for key in ("tier", "plan", "nickname", "product_name", "status"):
                v = sub.get(key)
                if isinstance(v, str) and v.strip():
                    return v.strip()

        def walk(obj: Any) -> List[str]:
            found: List[str] = []
            if isinstance(obj, dict):
                for k, v in obj.items():
                    lk = str(k).lower()
                    if lk in ("tier", "plan", "name", "nickname", "label", "title", "product"):
                        if isinstance(v, str) and v.strip():
                            found.append(v)
                    found.extend(walk(v))
            elif isinstance(obj, list):
                for x in obj:
                    found.extend(walk(x))
            return found

        for s in walk(plan):
            sl = s.lower()
            if "max" in sl:
                return s
            if "pro" in sl:
                return s
        return None

    @staticmethod
    def _wrap_tier_from_plan_dict(plan: Dict[str, Any]) -> Tuple[str, str, str, str]:
        slug = CLIAgent._infer_tier_slug_from_plan(plan)
        if slug:
            return CLIAgent._tier_tuple_from_slug(slug)
        return ("unknown", "Sweet", "dim white", "bold cyan")

    def _resolve_wrap_billing_tier(self) -> Tuple[str, str, str, str]:
        """Resolve billing tier for /wrap: (key, badge label, base Rich style, shine style)."""
        env = (os.environ.get("SWEET_WRAP_TIER") or "").strip()
        if env:
            return CLIAgent._tier_tuple_from_slug(env)
        if not getattr(self, "billing_client", None):
            return ("local", "LOCAL · NO RELAY", "dim white", "bold yellow")
        plan: Dict[str, Any] = {}
        try:
            plan = self.billing_client.get_plan_state() or {}
        except Exception:
            plan = {}
        if plan:
            return CLIAgent._wrap_tier_from_plan_dict(plan)
        try:
            info = self.billing_client.get_account_info()
        except Exception:
            info = {}
        if info.get("ok"):
            return ("paygo", "PREPAID ACCESS", "bold white", "bold cyan")
        return ("unknown", "Sweet", "dim white", "bold cyan")

    def _wrap_billing_metadata(self) -> Dict[str, Any]:
        k, badge, bst, sst = self._resolve_wrap_billing_tier()
        return {
            "billing_tier_key": k,
            "billing_tier_badge": badge,
            "billing_tier_base": bst,
            "billing_tier_shine": sst,
        }

    def _build_share_card_renderable(self, scope_stats: Dict[str, Any], *,
                                     cursor_visible: bool = True,
                                     logo_phase: int = 0,
                                     shine_phase: int = 0) -> Any:
        """
        Produce the Rich renderable for the wrap card. Pulled out of
        display_share_card so we can repaint it inside a Live for the cursor
        blink and moving shine without re-aggregating stats every refresh.
        """
        s = scope_stats
        s.setdefault("billing_tier_key", "unknown")
        s.setdefault("billing_tier_badge", "Sweet")
        s.setdefault("billing_tier_base", "dim white")
        s.setdefault("billing_tier_shine", "bold cyan")

        if s["scope"] == "today":
            label = "Daily Wrap"
        elif s["scope"] == "week":
            label = "Weekly Wrap"
        else:
            label = "All-Time Wrap"

        card_width = 65
        tk = str(s.get("billing_tier_key") or "unknown")
        tier_band = 6 if tk == "max" else (5 if tk == "pro" else 4)

        chrome = self._build_terminal_chrome(card_width, "~/sweet — /wrap")
        chrome_div = Rule(style="dim", characters="─")

        logo = self._render_sweet_logo(animate_phase=logo_phase)

        tier_plain = str(s.get("billing_tier_badge") or "Sweet")
        tier_line = Align.center(
            self._shine_span(
                tier_plain,
                shine_phase,
                base_style=str(s.get("billing_tier_base") or "dim white"),
                shine_style=str(s.get("billing_tier_shine") or "bold white"),
                band=tier_band,
            ),
            width=card_width - 4,
        )

        sub_plain = f"{label}  •  {s.get('day_label', '')}".strip(" •")
        subtitle = Align.center(
            self._shine_span(
                sub_plain,
                shine_phase + 8,
                base_style="dim",
                shine_style="bold white",
                band=3,
            ),
            width=card_width - 4,
        )

        rows: List[tuple] = []
        if s["lines_added"] or s["lines_removed"]:
            if s["lines_removed"]:
                rows.append((f"{s['lines_added']:,}", "lines written",
                             f"(+{s['lines_added']:,} / −{s['lines_removed']:,})"))
            else:
                rows.append((f"{s['lines_added']:,}", "lines of code written", ""))
        if s["files_touched"]:
            rows.append((f"{s['files_touched']:,}", "files touched", ""))
        if s["commands"]:
            rows.append((f"{s['commands']:,}", "shell commands run", ""))
        if s["subagents"]:
            sub_label = "subagent" + ("s" if s["subagents"] != 1 else "") + " working in parallel"
            rows.append((f"{s['subagents']:,}", sub_label, ""))
        if s["web_searches"]:
            rows.append((f"{s['web_searches']:,}", "web searches", ""))
        if s["tokens"]:
            rows.append((f"{s['tokens']:,}", "tokens", ""))

        body = Table.grid(padding=(0, 2))
        body.add_column(justify="right", no_wrap=True)
        body.add_column(justify="left", no_wrap=False)
        body.add_column(justify="left", style="dim", no_wrap=True)
        if not rows:
            body.add_row(
                Text("—", style="bold cyan"),
                self._shine_span(
                    "No activity recorded yet — go build something!",
                    shine_phase + 20,
                    base_style="dim",
                    shine_style="bold white",
                    band=3,
                ),
                Text(""),
            )
        else:
            for ri, (value, lbl, note) in enumerate(rows):
                body.add_row(
                    Text(str(value), style="bold cyan"),
                    self._shine_span(
                        lbl,
                        shine_phase + 18 + ri * 4,
                        base_style="white",
                        shine_style="bold bright_white",
                        band=3,
                    ),
                    Text(note or "", style="dim"),
                )

        time_block = Table.grid(padding=(0, 2))
        time_block.add_column(justify="left", no_wrap=True)
        time_block.add_column(justify="left", no_wrap=False)
        if s["seconds"] > 0:
            left = "⏱ " + self._format_seconds_human(s["seconds"])
            time_block.add_row(
                self._shine_span(
                    left, shine_phase + 50,
                    base_style="bold magenta", shine_style="bold white", band=2,
                ),
                self._shine_span(
                    "pair-programming with Sweet",
                    shine_phase + 52,
                    base_style="white", shine_style="bold bright_white", band=3,
                ),
            )
        if s["streak_current"] > 0:
            best = (f"  (best: {s['streak_best']})"
                    if s["streak_best"] and s["streak_best"] > s["streak_current"]
                    else "")
            time_block.add_row(
                self._shine_span(
                    f"🔥 Day {s['streak_current']}",
                    shine_phase + 60,
                    base_style="bold yellow",
                    shine_style="bold white",
                    band=2,
                ),
                self._shine_span(
                    f"streak{best}",
                    shine_phase + 62,
                    base_style="white",
                    shine_style="bold bright_yellow",
                    band=3,
                ),
            )

        love_block: Optional[Text] = None
        if s["top_tool"]:
            tname, tcount = s["top_tool"]
            if tcount > 0:
                love_block = (
                    self._shine_span(
                        "Most-loved tool:  ",
                        shine_phase + 70,
                        base_style="dim",
                        shine_style="bold white",
                        band=2,
                    )
                    + self._shine_span(
                        self._prettify_tool_name(tname),
                        shine_phase + 72,
                        base_style="bold green",
                        shine_style="bold bright_white",
                        band=3,
                    )
                    + Text(
                        f"  ({tcount}× call{'s' if tcount != 1 else ''})",
                        style="dim",
                    )
                )

        footer_div = Rule(style="dim", characters="─")
        footer = self._build_branded_footer(card_width, cursor_visible=cursor_visible)

        renderables: List[Any] = [
            chrome,
            chrome_div,
            Text(""),
            logo,
            Text(""),
            tier_line,
            Text(""),
            subtitle,
            Text(""),
            body,
        ]
        if time_block.row_count > 0:
            renderables.append(Text(""))
            renderables.append(time_block)
        if love_block is not None:
            renderables.append(Text(""))
            renderables.append(love_block)
        renderables.append(Text(""))
        renderables.append(footer_div)
        renderables.append(footer)

        return Panel(
            Group(*renderables),
            border_style="cyan",
            padding=(1, 2),
            width=card_width,
        )

    def display_share_card(self, scope: str = "today") -> None:
        """
        Render the Sweet! Daily Wrap — a screenshot-friendly share card the
        user can post on social. `/wrap` (today), `/wrap week`, `/wrap all`.

        The card features billing tier, moving shine across tier + stat labels,
        the Sweet block-letter logo (rainbow gradient), faux terminal chrome,
        and a prompt-styled footer. In a TTY, shine + cursor animate for a few
        seconds before settling. Honors SWEET_NO_ANIM=1 for CI / piped output.
        """
        s = self._aggregate_wrap_stats(scope)
        try:
            s.update(self._wrap_billing_metadata())
        except Exception:
            s.setdefault("billing_tier_key", "unknown")
            s.setdefault("billing_tier_badge", "Sweet")
            s.setdefault("billing_tier_base", "dim white")
            s.setdefault("billing_tier_shine", "bold cyan")

        anim_enabled = os.environ.get("SWEET_NO_ANIM", "").strip().lower() not in ("1", "true", "yes", "on")
        try:
            anim_enabled = bool(anim_enabled and sys.stdout and sys.stdout.isatty())
        except Exception:
            anim_enabled = False

        console.print()
        if anim_enabled:
            try:
                duration_s = 6.0
                refresh_hz = 8
                with Live(
                    self._build_share_card_renderable(
                        s, cursor_visible=True, logo_phase=0, shine_phase=0,
                    ),
                    console=console,
                    refresh_per_second=refresh_hz,
                    screen=False,
                    transient=False,
                ) as live:
                    self._track_live_ref(live)
                    start = time.time()
                    phase = 0
                    while (time.time() - start) < duration_s:
                        cursor_visible = (phase % 2) == 0
                        live.update(
                            self._build_share_card_renderable(
                                s,
                                cursor_visible=cursor_visible,
                                logo_phase=phase,
                                shine_phase=phase,
                            ),
                            refresh=True,
                        )
                        time.sleep(1.0 / refresh_hz)
                        phase += 1
                    live.update(
                        self._build_share_card_renderable(
                            s,
                            cursor_visible=True,
                            logo_phase=phase,
                            shine_phase=phase,
                        ),
                        refresh=True,
                    )
                    self._untrack_live_ref(live)
            except Exception:
                console.print(
                    self._build_share_card_renderable(
                        s, cursor_visible=True, shine_phase=0,
                    ),
                )
        else:
            console.print(
                self._build_share_card_renderable(s, cursor_visible=True, shine_phase=0),
            )

        console.print()

        # Tweet block — copyable text below the card.
        tweet = self._format_share_tweet(s)
        sep = Text("─" * 60, style="dim")
        console.print(Text("📋 Copy-paste this tweet:", style="bold"))
        console.print(sep)
        console.print(tweet)
        console.print(sep)
        console.print()

    def _format_share_tweet(self, s: Dict[str, Any]) -> Text:
        """Builds a numbers-included tweet ready for copy/paste. Keeps total
        chars under ~280 by only including non-zero metrics and trimming
        bullets if needed."""
        head_map = {
            "today": "Today with Sweet!:",
            "week":  "This week with Sweet!:",
            "all":   "All-time with Sweet!:",
        }
        head = head_map.get(s["scope"], head_map["today"])

        bullets: List[str] = []
        if s["lines_added"]:
            bullets.append(f"• {s['lines_added']:,} lines of code")
        if s["files_touched"]:
            bullets.append(f"• {s['files_touched']:,} files touched")
        if s["commands"]:
            bullets.append(f"• {s['commands']:,} commands run")
        if s["subagents"]:
            unit = "subagent" + ("s" if s["subagents"] != 1 else "")
            bullets.append(f"• {s['subagents']:,} {unit} in parallel")
        if s["seconds"] > 60:
            bullets.append(f"• {self._format_seconds_human(s['seconds'])} of pair-programming")

        streak_line = ""
        if s["streak_current"] > 1:
            streak_line = f"\n\nDay {s['streak_current']} streak 🔥"
        elif s["streak_current"] == 1:
            streak_line = "\n\nDay 1 — just getting started 🍬"

        body_lines = bullets[:5]  # cap so very-active days still fit ~280 chars
        body = "\n".join(body_lines) if body_lines else "Just getting started."

        text = (
            f"🍬 {head}\n"
            f"{body}"
            f"{streak_line}\n\n"
            f"sweetcli.com  #builtwithsweet"
        )

        # If somehow over 280, drop trailing bullets until we fit.
        while len(text) > 278 and len(body_lines) > 1:
            body_lines = body_lines[:-1]
            body = "\n".join(body_lines)
            text = (
                f"🍬 {head}\n"
                f"{body}"
                f"{streak_line}\n\n"
                f"sweetcli.com  #builtwithsweet"
            )

        return Text(text, style="white")
    
    @staticmethod
    def _coerce_tool_call_arguments(raw: Any) -> Tuple[str, bool]:
        """Best-effort coercion of a tool_call arguments value into a valid JSON
        object string. Returns (cleaned_string, ok_flag). ok_flag is False when
        the input was unrecoverable and we had to fall back to "{}".
        """
        # Already a dict — serialize it.
        if isinstance(raw, dict):
            try:
                return json.dumps(raw), True
            except Exception:
                return "{}", False

        if not isinstance(raw, str):
            return "{}", False

        s = raw.strip()
        if not s:
            return "{}", True  # empty args == no args; legal

        # Strip markdown code fences if a model emitted them.
        if s.startswith("```"):
            nl = s.find("\n")
            if nl != -1:
                s = s[nl + 1:]
            if s.endswith("```"):
                s = s[:-3]
            s = s.strip()

        # Direct parse.
        try:
            parsed = json.loads(s)
            if isinstance(parsed, dict):
                return json.dumps(parsed), True
        except Exception:
            pass

        # Recovery: trim to the last '}' and retry. Catches trailing-garbage
        # and truncated-stream cases like `{"file_path": "/x", "content": "abc`.
        last_close = s.rfind("}")
        if last_close > 0:
            candidate = s[: last_close + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return json.dumps(parsed), True
            except Exception:
                pass

        return "{}", False

    @staticmethod
    def _normalize_tool_call_for_api(tc: Any) -> Optional[Dict[str, Any]]:
        """Convert SDK/dict tool-call shapes into the dict shape expected by chat APIs."""
        if isinstance(tc, dict):
            return dict(tc)

        for method_name in ("model_dump", "dict", "to_dict"):
            method = getattr(tc, method_name, None)
            if callable(method):
                try:
                    data = method()
                    if isinstance(data, dict):
                        return data
                except Exception:
                    pass

        try:
            fn_obj = getattr(tc, "function", None)
            fn: Dict[str, Any] = {}
            if isinstance(fn_obj, dict):
                fn = dict(fn_obj)
            elif fn_obj is not None:
                fn = {
                    "name": getattr(fn_obj, "name", None),
                    "arguments": getattr(fn_obj, "arguments", None),
                }
            out = {
                "id": getattr(tc, "id", None),
                "type": getattr(tc, "type", "function") or "function",
                "function": fn,
            }
            if out.get("id") and isinstance(out.get("function"), dict):
                return out
        except Exception:
            pass
        return None

    def _sanitize_tool_calls_for_api(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Walk the message list and ensure every assistant `tool_calls[].function.arguments`
        is a valid JSON object string (or a dict). Drops tool_call entries that
        are unrecoverable AND drops their matching tool-result messages (matched
        by tool_call_id) so the conversation stays coherent for the upstream API.

        This is a defensive belt-and-suspenders pass: even if our streaming
        accumulator wrote a truncated JSON fragment into history (e.g. after a
        Ctrl-C mid-stream), we won't replay it to the relay verbatim.
        """
        if not isinstance(messages, list):
            return messages

        dropped_tool_call_ids: set = set()
        out: List[Dict[str, Any]] = []

        for msg in messages:
            if not isinstance(msg, dict):
                out.append(msg)
                continue

            role = msg.get("role")
            if role == "assistant" and not msg.get("tool_calls"):
                has_content = isinstance(msg.get("content"), str) and bool(msg.get("content").strip())
                has_reasoning = isinstance(msg.get("reasoning_content"), str) and bool(msg.get("reasoning_content").strip())
                if not has_content and not has_reasoning:
                    # Legacy interrupted/checkpointed sessions can contain an
                    # empty assistant shell. DeepSeek thinking mode rejects
                    # those on replay because there is no reasoning_content to
                    # pass back, so drop the hollow turn before any API call.
                    continue
                # DeepSeek V4 thinking mode requires `reasoning_content` to be
                # present on every assistant turn it sees on replay. Some legacy
                # checkpoints saved text-only turns without it; inject an empty
                # string here so the upstream API contract is always satisfied.
                if not isinstance(msg.get("reasoning_content"), str):
                    new_msg = dict(msg)
                    new_msg["reasoning_content"] = ""
                    out.append(new_msg)
                    continue

            if role == "assistant" and msg.get("tool_calls"):
                cleaned_calls: List[Any] = []
                for tc in msg.get("tool_calls") or []:
                    tc = self._normalize_tool_call_for_api(tc)
                    if not isinstance(tc, dict):
                        continue
                    fn = tc.get("function") or {}
                    if not isinstance(fn, dict) or not fn.get("name"):
                        # Unusable: drop and remember the id so the matching
                        # tool result also gets pruned.
                        tc_id = tc.get("id")
                        if isinstance(tc_id, str):
                            dropped_tool_call_ids.add(tc_id)
                        continue
                    cleaned_args, ok = self._coerce_tool_call_arguments(fn.get("arguments"))
                    new_fn = dict(fn)
                    new_fn["arguments"] = cleaned_args
                    new_tc = dict(tc)
                    new_tc["function"] = new_fn
                    cleaned_calls.append(new_tc)
                    if not ok:
                        # We salvaged the structure (set arguments to "{}"),
                        # so KEEP the call + its tool result — the model can
                        # reason about an empty-arg call. We only drop when
                        # the call itself was structurally broken above.
                        pass

                new_msg = dict(msg)
                # DeepSeek V4 thinking mode requires `reasoning_content` to be
                # present on every assistant tool-call turn — even if the model
                # emitted no reasoning text that turn (which happens when it
                # chains a tool call straight after a tool result). Default
                # missing/None values to "" so the API call never gets rejected
                # with "reasoning_content must be passed back to the API".
                if not isinstance(new_msg.get("reasoning_content"), str):
                    new_msg["reasoning_content"] = ""
                if cleaned_calls:
                    new_msg["tool_calls"] = cleaned_calls
                    out.append(new_msg)
                else:
                    # No usable tool_calls left. Keep the assistant message
                    # only if it carries text content; otherwise drop it
                    # entirely so we don't leave a hollow turn.
                    new_msg.pop("tool_calls", None)
                    if isinstance(new_msg.get("content"), str) and new_msg.get("content").strip():
                        out.append(new_msg)
                continue

            if role == "tool":
                tc_id = msg.get("tool_call_id")
                if isinstance(tc_id, str) and tc_id in dropped_tool_call_ids:
                    continue
                out.append(msg)
                continue

            out.append(msg)

        return out

    def _filter_valid_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter messages to ensure tool messages are only included if they follow
        an assistant message with tool_calls. This prevents API errors when resuming sessions.

        Also runs a sanitization pass that repairs malformed tool_call arguments
        (e.g. truncated JSON from interrupted streams) so we never replay them
        verbatim to the upstream API.
        """
        try:
            messages = self._sanitize_tool_calls_for_api(messages)
        except Exception:
            pass

        valid_messages = []
        last_assistant_has_tool_calls = False
        
        for msg in messages:
            role = msg.get("role")
            
            if role == "tool":
                # Only include tool messages if the previous assistant had tool_calls
                if last_assistant_has_tool_calls:
                    valid_messages.append(msg)
                # Reset flag after processing tool message
                last_assistant_has_tool_calls = False
            elif role == "assistant":
                # Check if this assistant message has tool_calls
                last_assistant_has_tool_calls = bool(msg.get("tool_calls"))
                valid_messages.append(msg)
            else:
                # user, system, etc. - always include
                valid_messages.append(msg)
                last_assistant_has_tool_calls = False
        
        return valid_messages
    
    def _create_result_panel(self, function_name: str, function_args: Dict[str, Any], result: Dict[str, Any] = None):
        """Create a result panel for a tool execution"""
        
        if function_name == "modify_file":
            file_path = function_args.get("file_path", "")
            operation = function_args.get("operation", "")
            
            # Check result for errors
            if result and not result.get("success", True):
                error = result.get("error", "Unknown error")
                return Panel(
                    f"[red]✗[/red] [cyan]Failed to modify[/cyan] {escape(str(file_path))}\n  {escape(str(error))}",
                    title=f"[bold blue]✏️  Modify File[/bold blue]", border_style="red", padding=(0, 1),
                )
            
            op_display = {
                "replace": "Replaced",
                "insert": "Inserted",
                "delete": "Deleted",
                "replace_text": "Replace_text",
                "apply_edits": "Apply_edits",
                "patch": "Patched",
            }.get(operation, operation.capitalize())
            
            start_line = result.get("start_line", function_args.get("start_line", 0))
            end_line = result.get("end_line")
            lines_modified = result.get("lines_modified", 0)
            lines_added = result.get("lines_added", 0)
            lines_inserted = result.get("lines_inserted")
            lines_deleted = result.get("lines_deleted")
            total_lines = result.get("total_lines", 0)

            # Back-compat: infer inserted/deleted if older tool result shape
            if not isinstance(lines_inserted, int):
                if operation in ("replace", "replace_text"):
                    lines_inserted = int(lines_added or 0)
                elif operation == "insert":
                    lines_inserted = int(lines_added or 0)
                else:
                    lines_inserted = 0
            if not isinstance(lines_deleted, int):
                if operation in ("replace", "replace_text", "delete"):
                    lines_deleted = int(lines_modified or 0)
                else:
                    lines_deleted = 0
            
            info = f"[green]✓[/green] [cyan]{op_display}[/cyan] in {file_path}\n"
            if operation == "replace":
                info += f"  Lines {start_line}-{end_line}: [green]+{lines_inserted}[/green] [yellow]-{lines_deleted}[/yellow]"
            elif operation == "insert":
                info += f"  At line {start_line}: [green]+{lines_inserted}[/green] [yellow]-{lines_deleted}[/yellow]"
            elif operation == "delete":
                info += f"  Lines {start_line}-{end_line}: [green]+{lines_inserted}[/green] [yellow]-{lines_deleted}[/yellow]"
            else:
                info += f"  [green]+{lines_inserted}[/green] [yellow]-{lines_deleted}[/yellow]"
            info += f"\n  [dim]Total lines: {total_lines}[/dim]"

            # Try to attach a diff preview reconstructed from args. Falls back
            # to the plain info panel on any error so we never regress the UX.
            try:
                diff_renderable = self._build_modify_result_diff(function_args, operation, file_path)
            except Exception:
                diff_renderable = None
            if diff_renderable is not None:
                try:
                    return Panel(
                        Group(Text.from_markup(info), diff_renderable),
                        title=f"[bold blue]✏️  Modify File[/bold blue]",
                        border_style="blue",
                        padding=(0, 1),
                    )
                except Exception:
                    pass
            return Panel(info, title=f"[bold blue]✏️  Modify File[/bold blue]", border_style="blue", padding=(0, 1))
        
        elif function_name == "write_file":
            file_path = function_args.get("file_path", "")
            content = function_args.get("content", "")
            
            # Check result for errors
            if result and not result.get("success", True):
                error = result.get("error", "Unknown error")
                return Panel(
                    f"[red]✗[/red] [cyan]Failed to write[/cyan] {escape(str(file_path))}\n  {escape(str(error))}",
                    title=f"[bold blue]📝 Write File[/bold blue]", border_style="red", padding=(0, 1),
                )
            
            # Check if content is empty (might indicate a problem)
            if not content or len(content.strip()) == 0:
                # File was written but with empty content - warn user
                is_new = not os.path.exists(file_path)
                action = "Created" if is_new else "Modified"
                info = f"[yellow]⚠[/yellow] [cyan]{action}[/cyan] {file_path}\n"
                info += f"  [dim]Warning: File is empty (0 bytes)[/dim]"
                return Panel(info, title=f"[bold blue]📝 Write File[/bold blue]", border_style="yellow", padding=(0, 1))
            
            lines = content.count('\n') + 1
            size = len(content)
            
            # Check if file exists to determine if it's new or modified
            is_new = not os.path.exists(file_path)
            action = "Created" if is_new else "Modified"
            
            info = f"[green]✓[/green] [cyan]{action}[/cyan] {file_path}  [dim]· {lines} lines · {size:,} B[/dim]"

            # Attach a syntax-highlighted preview of what we just wrote.
            try:
                preview = self._build_file_content_preview(
                    file_path,
                    content,
                    max_lines=18,
                    show_line_numbers=False,
                )
            except Exception:
                preview = None
            if preview is not None:
                try:
                    return Panel(
                        Group(Text.from_markup(info), preview),
                        title=f"[bold blue]📝 Write File[/bold blue]",
                        border_style="blue",
                        padding=(0, 1),
                    )
                except Exception:
                    pass
            return Panel(info, title=f"[bold blue]📝 Write File[/bold blue]", border_style="blue", padding=(0, 1))
        
        elif function_name == "read_file":
            file_path = function_args.get("file_path", "")
            if result and result.get("success"):
                size = result.get("size", 0)
                lines_read = result.get("lines", 0)
                total_lines = result.get("total_lines", 0)
                start_line = result.get("start_line")
                end_line = result.get("end_line")
                content = result.get("content", "")
                
                info = f"[green]✓[/green] [cyan]Read[/cyan] {file_path}  "
                if start_line is not None:
                    if end_line is not None:
                        info += f"[dim]lines {start_line}-{end_line} · {lines_read}/{total_lines} lines · {size:,} B[/dim]"
                    else:
                        info += f"[dim]lines {start_line}-{total_lines} · {lines_read}/{total_lines} lines · {size:,} B[/dim]"
                else:
                    info += f"[dim]{lines_read} lines · {size:,} B[/dim]"

                preview = None
                if isinstance(content, str) and content:
                    try:
                        preview = self._build_file_content_preview(
                            file_path,
                            content,
                            max_lines=20,
                            show_line_numbers=start_line is not None,
                            start_line=int(start_line) if isinstance(start_line, int) else 1,
                        )
                    except Exception:
                        preview = None
                if preview is not None:
                    try:
                        return Panel(
                            Group(Text.from_markup(info), preview),
                            title=f"[bold blue]📖 Read File[/bold blue]",
                            border_style="blue",
                            padding=(0, 1),
                        )
                    except Exception:
                        pass
            else:
                info = f"[red]✗[/red] [cyan]Failed to read[/cyan] {file_path}"
            
            return Panel(info, title=f"[bold blue]📖 Read File[/bold blue]", border_style="blue", padding=(0, 1))
        
        elif function_name == "run_command":
            command = function_args.get("command", "")
            display_cmd = command if len(command) < 60 else command[:57] + "..."
            # Commands routinely contain regex/grep patterns with `[...]` that
            # Rich would parse as markup tags (e.g. `[/(?:\ba|@base)\b]` looks
            # like an unbalanced closing tag). Always escape user-supplied text
            # before embedding it into a markup-parsed string.
            safe_cmd = escape(display_cmd)

            if result and result.get("success"):
                info = f"[green]✓[/green] [cyan]{safe_cmd}[/cyan]"
            else:
                info = f"[red]✗[/red] [cyan]{safe_cmd}[/cyan]"

            return Panel(info, title=f"[bold blue]⚙️  Run Command[/bold blue]", border_style="blue", padding=(0, 1))
        
        elif function_name == "list_directory":
            dir_path = function_args.get("directory_path", "")
            if result and result.get("success"):
                count = result.get("count", 0)
                info = f"[green]✓[/green] [cyan]Listed[/cyan] {dir_path}\n  {count} items"
            else:
                info = f"[red]✗[/red] [cyan]Failed to list[/cyan] {dir_path}"
            
            return Panel(info, title=f"[bold blue]📁 List Directory[/bold blue]", border_style="blue", padding=(0, 1))
        
        elif function_name == "web_search":
            query = function_args.get("query", "")
            if result and result.get("success"):
                num_results = len(result.get("results", []))
                info = f"[green]✓[/green] [cyan]query={query}[/cyan]"
                if num_results > 0:
                    info += f", num_results={num_results}"
            else:
                error = result.get("error", "Unknown error") if result else "Failed"
                info = f"[red]✗[/red] [cyan]query={query}[/cyan] - {error}"
            
            return Panel(info, title=f"[bold blue]🔍 web_search[/bold blue]", border_style="blue", padding=(0, 1))

        elif function_name == "run_subagent":
            if result and result.get("success"):
                status = escape(str(result.get("status", "completed")))
                subagent_id = escape(str(result.get("subagent_id", "")))
                events = result.get("events") or []
                assistant_message = (result.get("assistant_message") or "").strip()
                questions = result.get("questions") or []

                info = f"[green]✓[/green] status=[cyan]{status}[/cyan]"
                if subagent_id:
                    info += f", subagent_id={subagent_id}"
                info += f", events={len(events)}"

                # Subagent event content can contain regex literals / code with
                # `[/...]` — every interpolated piece below is escaped so Rich
                # never tries to parse it as a closing markup tag.
                event_lines: List[str] = []
                for evt in events[-8:]:
                    et = evt.get("type")
                    if et == "tool":
                        event_lines.append(
                            f"- [cyan]tool[/cyan]: {escape(str(evt.get('tool_name', 'unknown')))}"
                        )
                    elif et == "status":
                        event_lines.append(
                            f"- [magenta]status[/magenta]: {escape(str(evt.get('status', 'unknown')))}"
                        )
                    elif et == "message":
                        role = escape(str(evt.get("role", "assistant")))
                        msg = str(evt.get("content", "")).strip().replace("\n", " ")
                        if not msg:
                            continue
                        if len(msg) > 90:
                            msg = msg[:87] + "..."
                        event_lines.append(f"- [dim]{role}[/dim]: {escape(msg)}")

                if event_lines:
                    info += "\n\n[dim]Recent subagent events:[/dim]\n" + "\n".join(event_lines[-6:])

                if assistant_message:
                    msg = assistant_message.replace("\n", " ").strip()
                    if len(msg) > 220:
                        msg = msg[:217] + "..."
                    info += f"\n\n[dim]Assistant:[/dim] {escape(msg)}"

                if questions:
                    q_preview = "; ".join(str(q).strip() for q in questions[:2] if str(q).strip())
                    if q_preview:
                        if len(q_preview) > 180:
                            q_preview = q_preview[:177] + "..."
                        info += f"\n[dim]Questions:[/dim] {escape(q_preview)}"

                border = "magenta"
            else:
                error = escape(str((result or {}).get("error", "Failed")))
                prompt_preview = function_args.get("prompt", "")
                if isinstance(prompt_preview, str) and len(prompt_preview) > 120:
                    prompt_preview = prompt_preview[:117] + "..."
                info = f"[red]✗[/red] [cyan]prompt={escape(str(prompt_preview))}[/cyan]\n  {error}"
                border = "red"

            return Panel(info, title=f"[bold magenta]🤖 Run Subagent[/bold magenta]", border_style=border, padding=(0, 1))

        elif function_name == "poll_subagent":
            def _clip_poll_text(value: Any, max_chars: int = 240, max_lines: int = 4) -> str:
                text = str(value or "").strip()
                if not text:
                    return ""
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if max_lines and len(lines) > max_lines:
                    lines = lines[:max_lines]
                    text = "\n".join(lines) + "\n..."
                else:
                    text = "\n".join(lines)
                if len(text) > max_chars:
                    text = text[: max_chars - 3].rstrip() + "..."
                return escape(text)

            def _format_poll_event(evt: Dict[str, Any]) -> Optional[str]:
                """Render one subagent event as a single, user-facing line.

                Returns None for events that are pure internal plumbing (per-turn
                model_request/response, tool_start/tool_done) so the activity feed
                only contains things a human would recognize: the subagent
                thinking, writing, calling a tool, finishing, etc.
                """
                if not isinstance(evt, dict):
                    return None
                et = evt.get("type")
                if et == "status":
                    status = str(evt.get("status", "unknown"))

                    # Internal plumbing — the visible message + tool result that
                    # follow already convey what happened to the user.
                    if status in ("model_request", "model_response", "tool_start", "tool_done"):
                        return None

                    # Streaming progress -> friendly label.
                    if status == "model_streaming":
                        tcip = evt.get("tool_calls_inflight") or []
                        if isinstance(tcip, list) and tcip:
                            names = []
                            for item in tcip:
                                if isinstance(item, dict):
                                    nm = item.get("name")
                                    if nm:
                                        names.append(escape(str(nm)))
                            if names:
                                primary = names[0]
                                if len(names) > 1:
                                    primary += f" (+{len(names) - 1} more)"
                                return f"- [magenta]preparing tool[/magenta]: {primary}"
                        if (evt.get("content_chars") or 0) > 0:
                            return "- [magenta]writing response…[/magenta]"
                        return "- [magenta]thinking…[/magenta]"

                    if status == "tool_error":
                        tname = escape(str(evt.get("tool_name") or "tool"))
                        err = _clip_poll_text(evt.get("error", ""), 140, 2)
                        return f"- [red]tool error[/red]: {tname} [dim]{err}[/dim]" if err else f"- [red]tool error[/red]: {tname}"

                    if status == "model_error":
                        err = _clip_poll_text(evt.get("error", ""), 160, 2)
                        return f"- [red]model error[/red]: [dim]{err}[/dim]" if err else "- [red]model error[/red]"

                    # Terminal/meaningful statuses we DO want to surface.
                    label_map = {
                        "started": "started",
                        "completed": "completed",
                        "responded": "responded",
                        "cancelled": "cancelled",
                        "needs_user_input": "needs your input",
                    }
                    label = label_map.get(status, escape(status))
                    questions = evt.get("questions") or []
                    if questions:
                        q = _clip_poll_text("; ".join(str(x) for x in questions[:2]), 160, 2)
                        return f"- [magenta]status[/magenta]: {label} [dim]questions: {q}[/dim]"
                    reason = _clip_poll_text(evt.get("reason", ""), 140, 2)
                    if reason:
                        return f"- [magenta]status[/magenta]: {label} [dim]{reason}[/dim]"
                    return f"- [magenta]status[/magenta]: {label}"
                if et == "message":
                    role = escape(str(evt.get("role", "assistant")))
                    msg = _clip_poll_text(evt.get("content", ""), 280, 3)
                    if not msg:
                        return None
                    return f"- [dim]{role}[/dim]: {msg}"
                if et == "tool":
                    tool_name = escape(str(evt.get("tool_name", "unknown")))
                    data = evt.get("result") or {}
                    if not isinstance(data, dict):
                        result_preview = _clip_poll_text(data, 180, 2)
                        return f"- [cyan]tool[/cyan]: {tool_name} [dim]{result_preview}[/dim]"

                    ok = data.get("success")
                    marker = "[green]✓[/green]" if ok is True else ("[red]✗[/red]" if ok is False or data.get("error") else "[dim]•[/dim]")
                    detail_parts: List[str] = []
                    for key in ("file_path", "path", "directory_path", "command", "query"):
                        val = data.get(key)
                        if val:
                            detail_parts.append(f"{key}={_clip_poll_text(val, 90, 1)}")
                            break
                    if data.get("error"):
                        detail_parts.append(f"error={_clip_poll_text(data.get('error'), 140, 2)}")
                    elif data.get("stdout"):
                        detail_parts.append(f"stdout={_clip_poll_text(data.get('stdout'), 140, 2)}")
                    elif data.get("stderr"):
                        detail_parts.append(f"stderr={_clip_poll_text(data.get('stderr'), 140, 2)}")
                    elif "todos" in data:
                        detail_parts.append(f"todos={len(data.get('todos') or [])}")
                    elif "content" in data and "lines" in data:
                        detail_parts.append(f"lines={data.get('lines')}")
                    detail = f" [dim]{' · '.join(detail_parts)}[/dim]" if detail_parts else ""
                    return f"- [cyan]tool[/cyan]: {marker} {tool_name}{detail}"
                return None

            # Build a user-facing summary of the poll result. We deliberately
            # avoid technical plumbing (raw event indices, total event counts,
            # internal tool-call counts, custom_system_prompt flags) so the
            # tile reads like a status update on the assistant, not a debugger.
            subagent_id = function_args.get("subagent_id", "")
            if result and result.get("success"):
                job_status = result.get("job_status")
                session_status = result.get("session_status")
                job_error = result.get("job_error")
                job_result = result.get("job_result") or {}
                job_note = result.get("job_note")
                events = result.get("events") or []
                latest_event = result.get("latest_event")
                latest_event_age_s = result.get("latest_event_age_s")
                job_age_s = result.get("job_age_s")
                label = result.get("label")

                result_status = job_result.get("status") if isinstance(job_result, dict) else None
                if job_status in ("cancelled", "cancelling", "error", "interrupted"):
                    effective_status = job_status
                else:
                    effective_status = result_status or job_status or session_status

                # Friendly status label
                friendly_status_map = {
                    "running": "running",
                    "queued": "queued",
                    "completed": "completed",
                    "responded": "responded",
                    "done": "completed",
                    "cancelling": "cancelling…",
                    "cancelled": "cancelled",
                    "error": "errored",
                    "interrupted": "interrupted",
                    "needs_user_input": "needs your input",
                }
                friendly_status = friendly_status_map.get(str(effective_status or "").lower(), str(effective_status or "unknown"))
                status_txt = f"[cyan]{friendly_status}[/cyan]"

                # Header: short subagent handle (8-char) + label if present.
                short_id = subagent_id[:8] if subagent_id else ""
                header_bits = []
                if short_id:
                    header_bits.append(f"subagent {short_id}")
                if label:
                    header_bits.append(f"({_clip_poll_text(label, 80, 1)})")
                header = " ".join(header_bits) if header_bits else "subagent"
                info = f"[green]✓[/green] [cyan]{header}[/cyan]"

                # Status line + relative timing in plain English.
                info += f"\n  status: {status_txt}"
                timing_bits = []
                if job_age_s is not None:
                    try:
                        timing_bits.append(f"running for {int(float(job_age_s))}s")
                    except Exception:
                        pass
                if latest_event_age_s is not None:
                    try:
                        age = int(float(latest_event_age_s))
                        timing_bits.append(f"last update {age}s ago" if age > 0 else "last update just now")
                    except Exception:
                        pass
                if timing_bits:
                    info += f" [dim]({' · '.join(timing_bits)})[/dim]"

                if job_error:
                    err = str(job_error)
                    if len(err) > 160:
                        err = err[:157] + "..."
                    info += f"\n  [red]error:[/red] {err}"
                if job_note:
                    note = _clip_poll_text(job_note, 180, 2)
                    info += f"\n  [yellow]note:[/yellow] {note}"
                if isinstance(job_result, dict):
                    assistant_message = _clip_poll_text(job_result.get("assistant_message", ""), 360, 5)
                    questions = job_result.get("questions") or []
                    if assistant_message:
                        info += f"\n\n[dim]Latest message:[/dim]\n  {assistant_message.replace(chr(10), chr(10) + '  ')}"
                    if questions:
                        q_preview = _clip_poll_text("; ".join(str(q) for q in questions[:3]), 220, 3)
                        if q_preview:
                            info += f"\n[dim]Questions:[/dim] {q_preview}"

                # Recent activity feed: pull from a wider raw window since we
                # filter out internal lifecycle events, then dedupe consecutive
                # identical lines (so 3 fast "thinking…" ticks become one).
                event_lines: List[str] = []
                last_line: Optional[str] = None
                for evt in events[-30:]:
                    line = _format_poll_event(evt)
                    if line and line != last_line:
                        event_lines.append(line)
                        last_line = line
                event_lines = event_lines[-8:]
                if event_lines:
                    info += "\n\n[dim]Recent activity:[/dim]\n" + "\n".join(event_lines)
                elif effective_status in ("running", "queued"):
                    latest_line = _format_poll_event(latest_event) if isinstance(latest_event, dict) else None
                    info += "\n\n[dim]Subagent is still working.[/dim]"
                    if latest_line:
                        info += "\n" + latest_line
                if effective_status == "interrupted":
                    info += "\n  [yellow]⚠ subagent was interrupted by a prior CLI exit; re-dispatch if you still need this work[/yellow]"
                    border = "yellow"
                else:
                    border = "red" if job_error else "blue"
            else:
                error = (result or {}).get("error", "Failed")
                short_id = subagent_id[:8] if subagent_id else ""
                header = f"subagent {short_id}" if short_id else "subagent"
                info = f"[red]✗[/red] [cyan]{header}[/cyan]\n  {error}"
                border = "red"

            return Panel(info, title=f"[bold blue]🔧 poll_subagent[/bold blue]", border_style=border, padding=(0, 1))

        elif function_name == "list_subagents":
            if result and result.get("success"):
                jobs = (result.get("jobs") or [])
                subs = (result.get("subagents") or [])
                hier = (result.get("hierarchy") or {})
                tree_text = (hier.get("tree_text") or "").strip()
                running = sum(1 for j in jobs if j.get("status") in ("queued", "running", "cancelling"))
                done = sum(1 for j in jobs if j.get("status") == "done")
                err = sum(1 for j in jobs if j.get("status") == "error")
                cancelled = sum(1 for j in jobs if j.get("status") == "cancelled")
                interrupted = sum(1 for j in jobs if j.get("status") == "interrupted")
                parts = [f"running={running}", f"done={done}", f"error={err}"]
                if cancelled:
                    parts.append(f"[yellow]cancelled={cancelled}[/yellow]")
                if interrupted:
                    parts.append(f"[yellow]interrupted={interrupted}[/yellow]")
                header = f"[green]✓[/green] jobs={len(jobs)} ({', '.join(parts)}), subagents={len(subs)}"
                info = header + ("\n\n" + tree_text if tree_text else "\n[dim]No subagent sessions yet.[/dim]")
            else:
                error = (result or {}).get("error", "Failed")
                info = f"[red]✗[/red] {error}"
            return Panel(info, title=f"[bold blue]🔧 list_subagents[/bold blue]", border_style="blue", padding=(0, 1))

        elif function_name == "cancel_subagent_job":
            job_id = escape(str(function_args.get("job_id", "")))
            if result and result.get("success"):
                status = escape(str(result.get("status", "cancelling")))
                info = f"[green]✓[/green] [cyan]job_id={job_id}[/cyan]\n  status=[yellow]{status}[/yellow]"
                border = "yellow"
            else:
                error = escape(str((result or {}).get("error", "Failed")))
                info = f"[red]✗[/red] [cyan]job_id={job_id}[/cyan]\n  {error}"
                border = "red"
            return Panel(info, title=f"[bold blue]🔧 cancel_subagent_job[/bold blue]", border_style=border, padding=(0, 1))
        
        else:
            # Generic display. Tool args / errors are untrusted — escape any
            # `[...]` so Rich's markup parser doesn't choke on regex or array
            # literals (`closing tag '[/...]' doesn't match any open tag`).
            args_str = ", ".join(f"{k}={v}" for k, v in function_args.items())
            safe_args = escape(args_str)
            safe_name = escape(str(function_name))
            if result and (result.get("success") is False or result.get("error")):
                err = result.get("error") or "Failed"
                safe_err = escape(str(err))
                return Panel(
                    f"[red]✗[/red] {safe_args}\n  {safe_err}",
                    title=f"[bold blue]🔧 {safe_name}[/bold blue]",
                    border_style="red", padding=(0, 1),
                )
            return Panel(
                f"[green]✓[/green] {safe_args}",
                title=f"[bold blue]🔧 {safe_name}[/bold blue]",
                border_style="blue", padding=(0, 1),
            )
    
    def _create_todos_result_panel(self, function_args: Dict[str, Any], result: Dict[str, Any] = None):
        """Create a result panel for manage_todos tool - always shows the full list of todos"""
        action = function_args.get("action", "")
        todos = function_args.get("todos", [])
        
        # Get all todos from todo_manager to show current status
        all_todos = self.todo_manager.get_all_todos()
        
        # Build summary line
        if action == "create":
            summary = f"[green]✓[/green] [cyan]Created {len(todos)} todo(s)[/cyan]"
        elif action == "update":
            summary = f"[green]✓[/green] [cyan]Updated {len(todos)} todo(s)[/cyan]"
        elif action == "list":
            summary = f"[green]✓[/green] [cyan]Listed todos[/cyan]"
        elif action == "clear":
            summary = f"[green]✓[/green] [cyan]Cleared all todos[/cyan]"
        else:
            summary = f"[green]✓[/green] [cyan]{action}[/cyan]"
        
        # Build todo list display
        if not all_todos:
            content = f"{summary}\n[dim]No todos[/dim]"
        else:
            # Group todos by status for better display
            from collections import defaultdict
            by_status = defaultdict(list)
            for todo in sorted(all_todos, key=lambda x: x.get("id", "")):
                status = todo.get("status", "pending")
                by_status[status].append(todo)
            
            # Build display with status indicators
            lines = [summary, ""]
            
            # Show completed todos first, then in_progress, then pending
            status_order = ["completed", "in_progress", "pending"]
            for status in status_order:
                if status in by_status:
                    status_label = {
                        "completed": "[green]✓ Completed[/green]",
                        "in_progress": "[yellow]→ In Progress[/yellow]",
                        "pending": "[dim]○ Pending[/dim]"
                    }.get(status, status)
                    
                    for todo in by_status[status]:
                        todo_id = todo.get("id", "")
                        todo_content = todo.get("content", "")
                        # Truncate long content for display
                        if len(todo_content) > 60:
                            todo_content = todo_content[:57] + "..."
                        lines.append(f"  {status_label} {todo_content}")
            
            # Show any other statuses
            for status, todo_list in by_status.items():
                if status not in status_order:
                    for todo in todo_list:
                        todo_id = todo.get("id", "")
                        todo_content = todo.get("content", "")
                        if len(todo_content) > 60:
                            todo_content = todo_content[:57] + "..."
                        lines.append(f"  [{status}] {todo_content}")
            
            content = "\n".join(lines)
        
        return Panel(content, title=f"[bold cyan]📋 Manage Todos[/bold cyan]", border_style="cyan", padding=(0, 1))
    
    def _handle_streaming_response(self, thinking_live: Optional[Live] = None) -> tuple[Optional[str], Optional[List[Any]], Dict[int, Any], Dict[str, Any], bool, Optional[str], bool, bool]:
        """
        Handle streaming response with a single Live context that transitions between states.
        Processes the stream once to avoid consumption issues and file descriptor errors.
        Returns: (content, tool_calls, prepare_tiles_info, tool_call_live_map, thinking_live_stopped_early, reasoning_content, content_displayed_via_live, reasoning_displayed_via_live)
        """
        # Initialize all return variables at the very start to avoid "referenced before assignment" errors
        accumulated_content = ""
        accumulated_reasoning_content = ""  # Track reasoning_content for deepseek-reasoner
        # If the provider includes usage in streaming chunks (billing relay with include_usage),
        # we capture it for /stats.
        try:
            self._last_stream_total_tokens = None  # type: ignore[attr-defined]
        except Exception:
            pass
        tool_calls_dict: Dict[int, Dict[str, Any]] = {}
        tool_calls = None
        prepare_tiles_info: Dict[int, Dict[str, Any]] = {}
        tool_call_live_map: Dict[str, Any] = {}
        thinking_live_stopped_early = False
        thinking_live_ref = None  # Initialize for KeyboardInterrupt handler
        content_displayed_via_live = False  # Track if content was displayed during streaming to prevent duplication
        
        # Local Live managers for thinking and reasoning
        live_manager: Optional[LiveManager] = None
        reasoning_live_manager: Optional[LiveManager] = None
        reasoning_displayed_via_live = False
        reasoning_started = False

        # A small status spinner to cover gaps between reasoning and tool-call tiles/content.
        status_live_manager: Optional[LiveManager] = None
        last_ui_activity_ts: float = time.time()
        status_spinner_grace_s: float = 0.30  # wait this long before showing the status spinner

        thinking_visible_since: Optional[float] = None
        min_thinking_visible_s: float = 0.30  # keep spinner visible briefly to avoid "never appears" flashes

        def _stop_status_spinner(clear: bool = True):
            nonlocal status_live_manager
            if status_live_manager:
                try:
                    status_live_manager.stop(clear=clear)
                except Exception:
                    pass
            status_live_manager = None

        def _maybe_show_status_spinner(text: str = "[dim]Thinking...[/dim]"):
            """Show a small spinner if we haven't updated any UI for a short window."""
            nonlocal status_live_manager, last_ui_activity_ts
            try:
                # Never show the status spinner while tool tiles are active.
                try:
                    if current_state == "tools" or tool_call_live_map:
                        return
                except Exception:
                    pass
                if (time.time() - last_ui_activity_ts) < status_spinner_grace_s:
                    return
                panel = Panel(Spinner("dots", text=text), border_style="dim", padding=(0, 1))
                if status_live_manager is None:
                    status_live_manager = LiveManager(
                        console,
                        refresh_per_second=self.config.live_refresh_per_second,
                        min_update_interval=self.config.live_min_update_interval,
                        debug=False,
                        track_live=self._track_live_ref,
                        untrack_live=self._untrack_live_ref,
                    )
                    status_live_manager.start(panel)
                else:
                    status_live_manager.update(panel)
            except Exception:
                pass

        def stop_thinking_live(clear: bool = True):
            """Stop the thinking Live safely (manager if present, fallback otherwise)."""
            nonlocal thinking_live_ref, thinking_visible_since
            # Ensure the thinking spinner is visible for a minimum duration before we tear it down.
            # Without this, fast reasoning/tool-calls can stop the spinner so quickly it never renders.
            try:
                if thinking_visible_since is not None:
                    elapsed = time.time() - thinking_visible_since
                    remaining = min_thinking_visible_s - elapsed
                    if remaining > 0:
                        time.sleep(remaining)
                        sys.stdout.flush()
            except Exception:
                pass
            if live_manager:
                if not clear and live_manager.live:
                    try:
                        setattr(live_manager.live, "transient", False)
                    except Exception:
                        pass
                live_manager.stop(clear=clear)
                thinking_live_ref = None
                return
            if thinking_live_ref:
                # On Ctrl+C, we want the pending tile fully deleted (no leftover borders).
                if clear:
                    self._delete_live_tile(thinking_live_ref, pause=0.02)
                else:
                    try:
                        setattr(thinking_live_ref, "transient", False)
                    except Exception:
                        pass
                    self._stop_live_context(thinking_live_ref, clear=clear)
                    thinking_live_ref = None

        def stream_reasoning(markdown_text: str):
            """Stream reasoning live; prefer reusing the existing thinking Live to avoid flicker."""
            nonlocal reasoning_live_manager, reasoning_displayed_via_live, last_ui_activity_ts, current_state
            _stop_status_spinner(clear=True)
            last_ui_activity_ts = time.time()
            panel = Panel(
                Markdown(markdown_text or ""),
                border_style="dim",
                padding=(1, 1),
                title="[dim]💭 Reasoning[/dim]",
            )
            # Prefer updating the existing Live (thinking tile) to avoid tearing down and recreating tiles.
            try:
                if thinking_live_ref is not None:
                    thinking_live_ref.update(panel)
                    reasoning_displayed_via_live = True
                    current_state = "reasoning"
                    return
                if live_manager is not None:
                    live_manager.update(panel)
                    reasoning_displayed_via_live = True
                    current_state = "reasoning"
                    return
            except Exception:
                pass
            if reasoning_live_manager is None:
                reasoning_live_manager = LiveManager(
                    console,
                    refresh_per_second=self.config.live_refresh_per_second,
                    min_update_interval=self.config.live_min_update_interval,
                    debug=False,
                    track_live=self._track_live_ref,
                    untrack_live=self._untrack_live_ref,
                )
                reasoning_live_manager.start(panel)
            else:
                reasoning_live_manager.update(panel)
            reasoning_displayed_via_live = True

        def stop_reasoning_live(clear: bool = True):
            """Stop reasoning Live safely and clear the reference."""
            nonlocal reasoning_live_manager
            if reasoning_live_manager:
                try:
                    reasoning_live_manager.stop(clear=clear)
                except Exception:
                    pass
            reasoning_live_manager = None

        try:
            # Ensure we are under the context budget before each model call
            self._maybe_summarize_with_tile(thinking_live=thinking_live)
            # If compaction happened, show a brief, user-visible notice without breaking Live rendering.
            try:
                notice = getattr(self, "_pending_compaction_notice", None)
                if notice:
                    before_t = notice.get("before_tokens")
                    after_t = notice.get("after_tokens")
                    before_m = notice.get("before_messages")
                    after_m = notice.get("after_messages")
                    kind = notice.get("type") or "compact"
                    detail = f"{before_t}→{after_t} tok, {before_m}→{after_m} msgs" if before_t is not None else f"{before_m}→{after_m} msgs"
                    # Make compaction visible like autopilot status lines (dim, single line).
                    msg = f"[dim]🗜 Compaction ({kind}): {detail}[/dim]"
                    # Update the existing thinking spinner (preferred) so we don't print into an active Live.
                    if thinking_live is not None:
                        try:
                            thinking_live.update(Panel(Spinner("dots", text=msg), border_style="dim", padding=(0, 1)))
                        except Exception:
                            pass
                        # Defer a plain console line until after the turn (so it isn't lost inside the spinner).
                        try:
                            self._last_compaction_notice_line = f"🗜 Compaction ({kind}): {detail}"
                        except Exception:
                            pass
                    else:
                        console.print(msg)
                    # Consume
                    self._pending_compaction_notice = None
            except Exception:
                pass
            # Ensure there are no dangling assistant tool_calls without tool responses
            self._replay_pending_tool_calls()
            
            # State: 'thinking' | 'content' | 'tools'
            current_state = 'thinking'
            content_header_shown = False
            # thinking_live_stopped_early already initialized above
            
            # Use the provided thinking Live context, or create a new one
            # Store reference to thinking_live so we can stop it early for write_file
            thinking_live_ref = thinking_live
            if thinking_live:
                live = thinking_live
                current_renderable = thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                live.update(current_renderable)
                # Aggressive flushing to ensure spinner is visible
                sys.stdout.flush()
                time.sleep(0.1)  # Longer delay to ensure rendering
                sys.stdout.flush()
                # Force a render update
                live.update(current_renderable)
                sys.stdout.flush()
                thinking_visible_since = time.time()
            else:
                # Fallback: create new thinking panel if not provided
                thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                current_renderable = thinking_panel
                console.print()  # Add spacing
                live_manager = LiveManager(
                    console,
                    refresh_per_second=self.config.live_refresh_per_second,
                    min_update_interval=self.config.live_min_update_interval,
                    debug=False,
                    track_live=self._track_live_ref,
                    untrack_live=self._untrack_live_ref,
                )
                # For reasoning-only UI, keep the final reasoning panel visible after Live stops.
                ui_ro = bool(getattr(self.config, "ui_reasoning_only", False))
                live = live_manager.start(current_renderable, transient=(not ui_ro))
                thinking_live_ref = live  # Store reference for early stopping
                # Aggressive flushing to ensure spinner is visible
                sys.stdout.flush()
                time.sleep(0.1)  # Longer delay to ensure rendering
                sys.stdout.flush()
                # Force a render update
                if live_manager:
                    live_manager.update(current_renderable)
                elif live:
                    live.update(current_renderable)
                sys.stdout.flush()
                thinking_visible_since = time.time()
            
            # Ensure spinner is definitely visible before starting API call
            if live:
                try:
                    target_renderable = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                    if live_manager:
                        live_manager.update(target_renderable)
                    else:
                        live.update(target_renderable)
                    sys.stdout.flush()
                    time.sleep(0.05)  # Brief pause to ensure render
                    sys.stdout.flush()
                except Exception:
                    pass  # Ignore errors if Live context is already closed
            
            try:
                # Calculate safe max_tokens to avoid exceeding context limit
                max_tokens = self._calculate_safe_max_tokens(self.conversation_history)
                # Sanitize before sending: repairs any malformed tool_call
                # arguments (e.g. truncated JSON from prior interrupted streams).
                try:
                    stream_messages = self._sanitize_tool_calls_for_api(self.conversation_history)
                except Exception:
                    stream_messages = self.conversation_history
                # Start the stream
                stream = self.client.chat(
                    messages=stream_messages,
                    tools=self.tool_registry.get_tool_definitions(),
                    stream=True,
                    max_tokens=max_tokens,
                )
                
                # Process stream with the Live context
                # Note: if thinking_live was provided, it's already started, so we use it directly
                # Otherwise, we use the with statement to manage it
                if thinking_live:
                    # Live context already started, process stream
                    try:
                        for chunk in stream:
                            if not chunk or not hasattr(chunk, 'choices') or len(chunk.choices) == 0:
                                continue
                            # Capture usage if the billing relay includes it (typically only on the final chunk).
                            try:
                                usage = getattr(chunk, "usage", None)
                                if usage is not None:
                                    tt = getattr(usage, "total_tokens", None)
                                    if tt is None and isinstance(usage, dict):
                                        tt = usage.get("total_tokens")
                                    if tt is not None:
                                        self._last_stream_total_tokens = int(tt)  # type: ignore[attr-defined]
                            except Exception:
                                pass
                            
                            delta = chunk.choices[0].delta
                            # If we haven't rendered anything new for a moment (common after reasoning finishes),
                            # show a small status spinner so the UI doesn't look frozen.
                            if reasoning_started and (not getattr(delta, "reasoning_content", None)) and (not getattr(delta, "content", None)) and (not getattr(delta, "tool_calls", None)):
                                _maybe_show_status_spinner()
                            
                            # Handle reasoning streaming (for deepseek-reasoner and other OpenAI-compatible providers)
                            # NOTE: Different OpenAI SDK versions/providers may surface reasoning deltas under
                            # different attribute names (or keep them in Pydantic "extra" fields).
                            reasoning_delta = None
                            try:
                                if hasattr(delta, "reasoning_content") and getattr(delta, "reasoning_content", None):
                                    reasoning_delta = getattr(delta, "reasoning_content", None)
                                elif hasattr(delta, "reasoning") and getattr(delta, "reasoning", None):
                                    reasoning_delta = getattr(delta, "reasoning", None)
                                else:
                                    extra = getattr(delta, "__pydantic_extra__", None) or getattr(delta, "model_extra", None)
                                    if isinstance(extra, dict):
                                        reasoning_delta = extra.get("reasoning_content") or extra.get("reasoning") or extra.get("thinking")
                            except Exception:
                                reasoning_delta = None

                            if reasoning_delta:
                                _stop_status_spinner(clear=True)
                                last_ui_activity_ts = time.time()
                                accumulated_reasoning_content += str(reasoning_delta)
                                # First reasoning token: transition the *same* Live tile to reasoning (no stop/start).
                                if not reasoning_started:
                                    reasoning_started = True
                                # Stream reasoning live in real time
                                stream_reasoning(accumulated_reasoning_content)
                            # Keep thinking spinner visible during reasoning
                            if current_state == 'thinking' and live and not thinking_live_stopped_early:
                                try:
                                    live.update(Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1)))
                                    # Force flush to ensure spinner updates are visible immediately
                                    sys.stdout.flush()
                                except Exception:
                                    pass
                            
                            # Handle content streaming
                            if delta.content:
                                _stop_status_spinner(clear=True)
                                last_ui_activity_ts = time.time()
                                # Skip Live updates if thinking Live was stopped early (for write_file)
                                if thinking_live_stopped_early:
                                    # Just accumulate content, don't update Live
                                    if current_state == 'content':
                                        accumulated_content += delta.content
                                    else:
                                        current_state = 'content'
                                        accumulated_content = delta.content
                                elif bool(getattr(self.config, "ui_reasoning_only", False)) and reasoning_started:
                                    # Reasoning-only UI mode: keep the reasoning panel and do not render assistant content.
                                    # Still accumulate content so it can be saved in history / used by tools if needed.
                                    if current_state == 'content':
                                        accumulated_content += delta.content
                                    else:
                                        current_state = 'content'
                                        accumulated_content = delta.content
                                elif current_state in ('thinking', 'reasoning'):
                                    # Transition to content WITHOUT tearing down the tile (prevents visible flicker).
                                    current_state = 'content'
                                    accumulated_content = delta.content
                                    header_text = Text("Agent:", style="bold green")
                                    if accumulated_reasoning_content:
                                        current_renderable = Group(
                                            Panel(Markdown(accumulated_reasoning_content), border_style="dim", padding=(1, 1), title="[dim]💭 Reasoning[/dim]"),
                                            Text(""),
                                            header_text,
                                            Markdown(accumulated_content)
                                        )
                                    else:
                                        current_renderable = Group(header_text, Markdown(accumulated_content))
                                    try:
                                        if live:
                                            live.update(current_renderable)
                                        elif live_manager:
                                            live_manager.update(current_renderable)
                                    except Exception:
                                        pass
                                    content_displayed_via_live = True  # Mark that content was displayed
                                elif current_state == 'content':
                                    # Continue streaming content
                                    accumulated_content += delta.content
                                    # Only update Live if it's still active (not stopped early for write_file)
                                    if not thinking_live_stopped_early and live:
                                        header_text = Text("Agent:", style="bold green")
                                        if accumulated_reasoning_content:
                                            current_renderable = Group(
                                                Panel(Markdown(accumulated_reasoning_content), border_style="dim", padding=(1, 1), title="[dim]💭 Reasoning[/dim]"),
                                                Text(""),
                                                header_text,
                                                Markdown(accumulated_content)
                                            )
                                        else:
                                            current_renderable = Group(
                                                header_text,
                                                Markdown(accumulated_content)
                                            )
                                        live.update(current_renderable)
                                        content_displayed_via_live = True  # Mark that content was displayed
                            
                            # Autosave while streaming from billing relay (throttled).
                            # Note: conversation_history doesn't include this in-flight assistant message yet,
                            # so we write a checkpoint with a draft assistant message appended.
                            pass

                            # Handle tool calls
                            if delta.tool_calls:
                                _stop_status_spinner(clear=True)
                                last_ui_activity_ts = time.time()
                                # CRITICAL: Stop thinking spinner immediately when tool calls are detected
                                # This prevents the thinking spinner from showing alongside tool tiles
                                # MUST stop BEFORE processing individual tool calls to create their tiles
                                # Stop it regardless of thinking_live_stopped_early flag to be absolutely sure
                                if thinking_live_ref:
                                    # If we're showing reasoning in the tile, stop WITHOUT clearing so it remains visible
                                    # above the upcoming tool tiles.
                                    # Preserve the reasoning panel once it has started, regardless of ui_reasoning_only.
                                    # Otherwise, `sweet start` can "erase" the reasoning panel right when tool calls begin
                                    # (because we stop/clear the Live region before creating tool tiles).
                                    preserve = bool(
                                        (reasoning_started and accumulated_reasoning_content and accumulated_reasoning_content.strip())
                                        or reasoning_displayed_via_live
                                    )
                                    stop_thinking_live(clear=(not preserve))
                                    current_state = 'tools'
                                    thinking_live_stopped_early = True
                                    live = None  # Clear reference to prevent any updates
                                    # Flush and wait to ensure the stop is fully rendered before creating new tiles
                                    sys.stdout.flush()
                                    time.sleep(0.05)  # Longer delay to ensure thinking spinner is completely gone before tiles appear
                                    sys.stdout.flush()
                                
                                for tc in delta.tool_calls:
                                    idx = tc.index
                                    if idx not in tool_calls_dict:
                                        tool_calls_dict[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                                    
                                    if tc.id:
                                        tool_calls_dict[idx]["id"] = tc.id
                                        # If ID becomes available and we have a write_file or manage_todos Live context with idx key, migrate it
                                        if idx in prepare_tiles_info:
                                            temp_key = f"idx_{idx}"
                                            if temp_key in tool_call_live_map:
                                                live_info = tool_call_live_map[temp_key]
                                                if live_info.get("function_name") in ["write_file", "modify_file", "manage_todos"]:
                                                    # Migrate to tool_call_id key
                                                    tool_call_live_map[tc.id] = live_info
                                                    live_info["tool_call_id"] = tc.id
                                                    del tool_call_live_map[temp_key]
                                    
                                    if tc.function:
                                        # Handle function name
                                        if tc.function.name:
                                            tool_calls_dict[idx]["function"]["name"] = tc.function.name
                                            
                                            # Store prepare tile info when function name is detected
                                            # For write_file, create Live context immediately when name is detected
                                            # For other tools, wait until after main Live exits
                                            if idx not in prepare_tiles_info:
                                                fname = tc.function.name
                                                prep_text = f"[dim]Preparing {fname}...[/dim]"
                                                prepare_tiles_info[idx] = {"text": prep_text, "function_name": fname}
                                                
                                                # For write_file and manage_todos (create), create Live context immediately so it appears right away
                                                # Use idx as temporary key if ID not available yet, will migrate to ID when available
                                                # manage_todos with create action often involves many todos, so immediate feedback is important
                                                should_create_immediately = fname in ("write_file", "modify_file", "manage_todos")
                                                
                                                if should_create_immediately:
                                                    # CRITICAL: Stop thinking spinner immediately before creating tile
                                                    # This ensures the spinner disappears as soon as the tile is ready
                                                    if thinking_live_ref and not thinking_live_stopped_early:
                                                        try:
                                                            # If reasoning has started, do NOT clear the Live region or we erase the reasoning panel.
                                                            preserve = bool(
                                                                (reasoning_started and accumulated_reasoning_content and accumulated_reasoning_content.strip())
                                                                or reasoning_displayed_via_live
                                                            )
                                                            stop_thinking_live(clear=(not preserve))
                                                            current_state = 'tools'
                                                            thinking_live_stopped_early = True
                                                            live = None
                                                            sys.stdout.flush()
                                                            time.sleep(0.02)  # Brief pause to ensure spinner is gone before tile appears
                                                        except Exception:
                                                            pass
                                                    elif current_state == 'thinking' and thinking_live_ref:
                                                        # Also handle case where state wasn't updated yet
                                                        try:
                                                            preserve = bool(
                                                                (reasoning_started and accumulated_reasoning_content and accumulated_reasoning_content.strip())
                                                                or reasoning_displayed_via_live
                                                            )
                                                            stop_thinking_live(clear=(not preserve))
                                                            current_state = 'tools'
                                                            thinking_live_stopped_early = True
                                                            live = None
                                                            sys.stdout.flush()
                                                            time.sleep(0.02)
                                                        except Exception:
                                                            pass
                                                    
                                                    # Use consistent title based on function type
                                                    if fname == "write_file":
                                                        panel_title = f"[bold blue]📝 Write File[/bold blue]"
                                                    elif fname == "modify_file":
                                                        panel_title = f"[bold magenta]✏️  Modify File[/bold magenta]"
                                                    elif fname == "manage_todos":
                                                        panel_title = f"[bold cyan]📋 Manage Todos[/bold cyan]"
                                                    else:
                                                        panel_title = f"[bold blue]🔧 {fname}[/bold blue]"
                                                    
                                                    # CRITICAL: Stop thinking spinner before creating new tile
                                                    if thinking_live_ref and not thinking_live_stopped_early:
                                                        preserve = bool(
                                                            (reasoning_started and accumulated_reasoning_content and accumulated_reasoning_content.strip())
                                                            or reasoning_displayed_via_live
                                                        )
                                                        stop_thinking_live(clear=(not preserve))
                                                        thinking_live_stopped_early = True
                                                        live = None  # Clear reference
                                                    
                                                    tile_border = {"write_file": "blue", "modify_file": "magenta", "manage_todos": "cyan"}.get(fname, "cyan")
                                                    # Reuse a single Spinner instance per tile so its time-based frame
                                                    # counter keeps advancing as we swap the surrounding Panel.
                                                    tile_spinner = Spinner("dots", text=prep_text)
                                                    prep_panel = Panel(tile_spinner, title=panel_title, border_style=tile_border, padding=(0, 1))
                                                    prep_live = Live(prep_panel, console=console, refresh_per_second=10, screen=False)
                                                    prep_live.start()
                                                    self._track_live_ref(prep_live)
                                                    # Use idx as key initially, will migrate to tool_call_id when available
                                                    temp_key = f"idx_{idx}" if not tc.id else tc.id
                                                    tool_call_live_map[temp_key] = {
                                                        "live": prep_live,
                                                        "text": prep_text,
                                                        "function_name": fname,
                                                        "idx": idx,  # Store idx for later migration
                                                        "tool_call_id": tc.id if tc.id else None,
                                                        "spinner": tile_spinner,
                                                        "border_style": tile_border,
                                                        "panel_title": panel_title,
                                                    }
                                                
                                                # If we have content, ensure it's still displayed
                                                # But only if the main Live context is still active (not stopped early)
                                                if current_state == 'content' and accumulated_content and not thinking_live_stopped_early and live:
                                                    header_text = Text("Agent:", style="bold green")
                                                    if accumulated_reasoning_content:
                                                        current_renderable = Group(
                                                            Panel(Markdown(accumulated_reasoning_content), border_style="dim", padding=(1, 1), title="[dim]💭 Reasoning[/dim]"),
                                                            Text(""),
                                                            header_text,
                                                            Markdown(accumulated_content)
                                                        )
                                                    else:
                                                        current_renderable = Group(
                                                            header_text,
                                                            Markdown(accumulated_content)
                                                        )
                                                    live.update(current_renderable)
                                            
                                    # Handle function arguments
                                    if tc.function.arguments:
                                        tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments
                                        
                                        # Stream the file content/diff into the tile as args arrive so the
                                        # user sees the write/modify taking shape instead of a bare spinner.
                                        if idx in prepare_tiles_info:
                                            tile_info = prepare_tiles_info[idx]
                                            fname = tile_info["function_name"]

                                            if fname in ("write_file", "modify_file"):
                                                args_so_far = tool_calls_dict[idx]["function"]["arguments"]

                                                # Try a full JSON parse first (cheap when it succeeds); fall back
                                                # to progressive extraction so we still show the streaming body.
                                                parsed_args: Dict[str, Any] = {}
                                                try:
                                                    cleaned_args = args_so_far
                                                    if cleaned_args.startswith("```"):
                                                        fence_end = cleaned_args.find("\n")
                                                        if fence_end != -1:
                                                            cleaned_args = cleaned_args[fence_end + 1:]
                                                            if cleaned_args.endswith("```"):
                                                                cleaned_args = cleaned_args[:-3]
                                                    maybe = json.loads(cleaned_args)
                                                    if isinstance(maybe, dict):
                                                        parsed_args = maybe
                                                except Exception:
                                                    parsed_args = {}

                                                file_path = parsed_args.get("file_path")
                                                if not isinstance(file_path, str) or not file_path:
                                                    file_path = (
                                                        self._extract_partial_json_string(args_so_far, "file_path")
                                                        or self._extract_partial_json_string(args_so_far, "path")
                                                    )

                                                # Throttle per-tile updates on BOTH content growth and a
                                                # minimum inter-update delay so we don't thrash the terminal
                                                # (and so Rich's background refresh thread gets CPU time to
                                                # animate the reused spinner between our updates).
                                                last_sig = tile_info.get("stream_sig")
                                                sig = (fname, file_path or "", len(args_so_far))
                                                now_ts = time.time()
                                                last_ts = tile_info.get("stream_ts", 0.0)
                                                min_interval_s = 0.08  # ~12 fps ceiling on our own updates
                                                if last_sig != sig and (now_ts - last_ts) >= min_interval_s:
                                                    tile_info["stream_sig"] = sig
                                                    tile_info["stream_ts"] = now_ts

                                                    # Look up the live/spinner for this tile so we can reuse them.
                                                    target_live_info = None
                                                    for tc_id, live_info in tool_call_live_map.items():
                                                        if (
                                                            live_info.get("function_name") == fname
                                                            and (
                                                                live_info.get("idx") == idx
                                                                or tc_id == tool_calls_dict[idx].get("id")
                                                            )
                                                        ):
                                                            target_live_info = live_info
                                                            break
                                                    if target_live_info is None:
                                                        target_live_info = tool_call_live_map.get(f"idx_{idx}")
                                                        if target_live_info and target_live_info.get("function_name") != fname:
                                                            target_live_info = None

                                                    tile_spinner = target_live_info.get("spinner") if target_live_info else None

                                                    try:
                                                        if fname == "write_file":
                                                            content_partial = parsed_args.get("content") if isinstance(parsed_args.get("content"), str) else None
                                                            if content_partial is None:
                                                                content_partial = self._extract_partial_json_string(args_so_far, "content")
                                                            new_panel = self._build_streaming_write_panel(file_path, content_partial, spinner=tile_spinner)
                                                        else:
                                                            new_panel = self._build_streaming_modify_panel(file_path, parsed_args, args_so_far, spinner=tile_spinner)
                                                    except Exception:
                                                        new_panel = None

                                                    if new_panel is not None and target_live_info and target_live_info.get("live"):
                                                        try:
                                                            target_live_info["live"].update(new_panel)
                                                            target_live_info["text"] = f"[dim]{'Writing' if fname == 'write_file' else 'Modifying'}:[/dim] {file_path or '…'}"
                                                        except Exception:
                                                            pass
                            
                            # Check if tool calls are ready to execute
                            ready_to_execute = False
                            for idx in tool_calls_dict.keys():
                                try:
                                    args_so_far = tool_calls_dict[idx]["function"]["arguments"]
                                    # Quick fence-strip if model wrapped in ```json
                                    if args_so_far.startswith("```"):
                                        fence_end = args_so_far.find("\n")
                                        if fence_end != -1:
                                            args_so_far = args_so_far[fence_end+1:]
                                            if args_so_far.endswith("```"):
                                                args_so_far = args_so_far[:-3]
                                    json.loads(args_so_far)
                                    ready_to_execute = True
                                except Exception:
                                    pass
                            
                            # Check if stream is complete (finish_reason is set)
                            stream_complete = False
                            if hasattr(chunk.choices[0], 'finish_reason') and chunk.choices[0].finish_reason:
                                stream_complete = True
                            
                            # Only break if stream is complete OR if we have tool calls ready AND no content is being streamed
                            # Don't break early if content is still streaming - wait for finish_reason
                            if stream_complete or (ready_to_execute and not accumulated_content):
                                break
                    except KeyboardInterrupt:
                        # On interrupt, FINALIZE any in-flight Live tiles in place
                        # (preserving whatever the user already saw in scrollback)
                        # rather than trying to erase them — that's what was
                        # leaving orphan top borders.
                        _stop_status_spinner(clear=True)
                        try:
                            if reasoning_live_manager and reasoning_live_manager.live:
                                self._finalize_live_in_place(reasoning_live_manager.live)
                                reasoning_live_manager.live = None
                        except Exception:
                            pass
                        try:
                            if thinking_live_ref:
                                self._finalize_live_in_place(thinking_live_ref)
                        except Exception:
                            pass
                        raise
                    except Exception:
                        raise
                    finally:
                        # Ensure the generator/HTTP stream is closed
                        try:
                            close_fn = getattr(stream, "close", None)
                            if callable(close_fn):
                                close_fn()
                        except Exception:
                            pass
                        _stop_status_spinner(clear=True)
                else:
                    # Live context not provided, use with statement
                    with live:
                        try:
                            for chunk in stream:
                                if not chunk or not hasattr(chunk, 'choices') or len(chunk.choices) == 0:
                                    continue
                                # Capture usage if present.
                                try:
                                    usage = getattr(chunk, "usage", None)
                                    if usage is not None:
                                        tt = getattr(usage, "total_tokens", None)
                                        if tt is None and isinstance(usage, dict):
                                            tt = usage.get("total_tokens")
                                        if tt is not None:
                                            self._last_stream_total_tokens = int(tt)  # type: ignore[attr-defined]
                                except Exception:
                                    pass
                                
                                delta = chunk.choices[0].delta
                                if reasoning_started and (not getattr(delta, "reasoning_content", None)) and (not getattr(delta, "content", None)) and (not getattr(delta, "tool_calls", None)):
                                    _maybe_show_status_spinner()
                                
                                # Handle reasoning streaming (see note above).
                                reasoning_delta = None
                                try:
                                    if hasattr(delta, "reasoning_content") and getattr(delta, "reasoning_content", None):
                                        reasoning_delta = getattr(delta, "reasoning_content", None)
                                    elif hasattr(delta, "reasoning") and getattr(delta, "reasoning", None):
                                        reasoning_delta = getattr(delta, "reasoning", None)
                                    else:
                                        extra = getattr(delta, "__pydantic_extra__", None) or getattr(delta, "model_extra", None)
                                        if isinstance(extra, dict):
                                            reasoning_delta = extra.get("reasoning_content") or extra.get("reasoning") or extra.get("thinking")
                                except Exception:
                                    reasoning_delta = None

                                if reasoning_delta:
                                    _stop_status_spinner(clear=True)
                                    last_ui_activity_ts = time.time()
                                    accumulated_reasoning_content += str(reasoning_delta)
                                    if not reasoning_started:
                                        stop_thinking_live()
                                        reasoning_started = True
                                    stream_reasoning(accumulated_reasoning_content)
                                
                                # Handle content streaming
                                if delta.content:
                                    _stop_status_spinner(clear=True)
                                    last_ui_activity_ts = time.time()
                                    if current_state == 'thinking':
                                        current_state = 'content'
                                        accumulated_content = delta.content
                                        header_text = Text("Agent:", style="bold green")
                                        if accumulated_reasoning_content:
                                            current_renderable = Group(
                                                Panel(Markdown(accumulated_reasoning_content), border_style="dim", padding=(1, 1), title="[dim]💭 Reasoning[/dim]"),
                                                Text(""),
                                                header_text,
                                                Markdown(accumulated_content)
                                            )
                                        else:
                                            current_renderable = Group(
                                                header_text,
                                                Markdown(accumulated_content)
                                            )
                                        live.update(current_renderable)
                                        content_displayed_via_live = True  # Mark that content was displayed
                                    elif current_state == 'content':
                                        accumulated_content += delta.content
                                        header_text = Text("Agent:", style="bold green")
                                        if accumulated_reasoning_content:
                                            current_renderable = Group(
                                                Panel(Markdown(accumulated_reasoning_content), border_style="dim", padding=(1, 1), title="[dim]💭 Reasoning[/dim]"),
                                                Text(""),
                                                header_text,
                                                Markdown(accumulated_content)
                                            )
                                        else:
                                            current_renderable = Group(
                                                header_text,
                                                Markdown(accumulated_content)
                                            )
                                        live.update(current_renderable)
                                        content_displayed_via_live = True  # Mark that content was displayed
                                
                                # Handle tool calls
                                if delta.tool_calls:
                                    _stop_status_spinner(clear=True)
                                    last_ui_activity_ts = time.time()
                                    # Hide thinking spinner when tool calls are detected
                                    if current_state == 'thinking':
                                        current_state = 'tools'
                                        # For write_file, the tile is already shown via its own Live context
                                        # Don't update main Live - just let it exit naturally
                                        # The write_file Live context will persist independently
                                        pass  # Don't touch main Live - let write_file tile handle display
                                    
                                    for tc in delta.tool_calls:
                                        idx = tc.index
                                        if idx not in tool_calls_dict:
                                            tool_calls_dict[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                                        if tc.id:
                                            tool_calls_dict[idx]["id"] = tc.id
                                        if tc.function:
                                            if tc.function.name:
                                                tool_calls_dict[idx]["function"]["name"] = tc.function.name
                                                if idx not in prepare_tiles_info:
                                                    fname = tc.function.name
                                                    prep_text = f"[dim]Preparing {fname}...[/dim]"
                                                    prepare_tiles_info[idx] = {"text": prep_text, "function_name": fname}
                                                    
                                                    # If we have content, ensure it's still displayed
                                                    if current_state == 'content' and accumulated_content:
                                                        header_text = Text("Agent:", style="bold green")
                                                        if accumulated_reasoning_content:
                                                            current_renderable = Group(
                                                                Panel(Markdown(accumulated_reasoning_content), border_style="dim", padding=(1, 1), title="[dim]💭 Reasoning[/dim]"),
                                                                Text(""),
                                                                header_text,
                                                                Markdown(accumulated_content)
                                                            )
                                                        else:
                                                            current_renderable = Group(
                                                                header_text,
                                                                Markdown(accumulated_content)
                                                            )
                                                        live.update(current_renderable)
                                            if tc.function.arguments:
                                                tool_calls_dict[idx]["function"]["arguments"] += tc.function.arguments
                                    # Check if ready to execute
                                    ready_to_execute = False
                                    for idx in tool_calls_dict.keys():
                                        try:
                                            args_so_far = tool_calls_dict[idx]["function"]["arguments"]
                                            if args_so_far.startswith("```"):
                                                fence_end = args_so_far.find("\n")
                                                if fence_end != -1:
                                                    args_so_far = args_so_far[fence_end+1:]
                                                    if args_so_far.endswith("```"):
                                                        args_so_far = args_so_far[:-3]
                                            json.loads(args_so_far)
                                            ready_to_execute = True
                                        except Exception:
                                            pass
                                    
                                    # Check if stream is complete (finish_reason is set)
                                    stream_complete = False
                                    if hasattr(chunk.choices[0], 'finish_reason') and chunk.choices[0].finish_reason:
                                        stream_complete = True
                                    
                                    # Only break if stream is complete OR if we have tool calls ready AND no content is being streamed
                                    # Don't break early if content is still streaming - wait for finish_reason
                                    if stream_complete or (ready_to_execute and not accumulated_content):
                                        break
                        except KeyboardInterrupt:
                            # On interrupt, finalize the in-flight Live tiles in
                            # place so the user keeps everything they already saw
                            # (avoids the orphan-top-border bug).
                            _stop_status_spinner(clear=True)
                            try:
                                if reasoning_live_manager and reasoning_live_manager.live:
                                    self._finalize_live_in_place(reasoning_live_manager.live)
                                    reasoning_live_manager.live = None
                            except Exception:
                                pass
                            try:
                                if thinking_live_ref:
                                    self._finalize_live_in_place(thinking_live_ref)
                            except Exception:
                                pass
                            raise
                        finally:
                            try:
                                close_fn = getattr(stream, "close", None)
                                if callable(close_fn):
                                    close_fn()
                            except Exception:
                                pass
                            _stop_status_spinner(clear=True)
            except Exception:
                raise
            finally:
                # Ensure stream is closed if exception occurred before processing
                try:
                    if 'stream' in locals():
                        close_fn = getattr(stream, "close", None)
                        if callable(close_fn):
                            close_fn()
                except Exception:
                    pass

            # Convert tool_calls_dict to list if we have tool calls
            # (tool_calls already initialized above)
            # write_file Live contexts are already created during streaming
            # Migrate any remaining idx-based keys to tool_call_id keys now that we have final tool calls
            if tool_calls_dict:
                tool_calls = []
                for idx in sorted(tool_calls_dict.keys()):
                    tc = tool_calls_dict[idx]
                    tool_calls.append(tc)
                    # Migrate write_file and manage_todos Live contexts from idx keys to tool_call_id keys if needed
                    tool_call_id = tc.get("id", "")
                    if tool_call_id:
                        temp_key = f"idx_{idx}"
                        if temp_key in tool_call_live_map:
                            live_info = tool_call_live_map[temp_key]
                            if live_info.get("function_name") in ["write_file", "manage_todos"]:
                                tool_call_live_map[tool_call_id] = live_info
                                live_info["tool_call_id"] = tool_call_id
                                del tool_call_live_map[temp_key]

            # Fallback: if the streaming produced no content and no tool calls, try a non-streaming fetch
            if not accumulated_content and not tool_calls:
                try:
                    # Filter conversation history to ensure tool messages are valid
                    # Tool messages must be preceded by an assistant message with tool_calls
                    valid_messages = self._filter_valid_messages(self.conversation_history)
                    
                    # Calculate safe max_tokens to avoid exceeding context limit
                    max_tokens = self._calculate_safe_max_tokens(valid_messages)
                    resp = self.client.chat(
                        messages=valid_messages,
                        tools=self.tool_registry.get_tool_definitions(),
                        stream=False,
                        max_tokens=max_tokens,
                    )
                    # Capture non-stream usage if present (relay may provide exact token counts).
                    try:
                        usage = getattr(resp, "usage", None)
                        tt = getattr(usage, "total_tokens", None) if usage is not None else None
                        if tt is None and isinstance(usage, dict):
                            tt = usage.get("total_tokens")
                        if tt is not None:
                            self._last_stream_total_tokens = int(tt)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    if resp and hasattr(resp, 'choices') and len(resp.choices) > 0:
                        text = resp.choices[0].message.content or ""
                        if text.strip():
                            console.print("\n[bold green]Agent:[/bold green]")
                            console.print(Markdown(text))
                            return text, None, {}, {}, False, None, False, False
                except Exception as e:
                    console.print(f"[dim]Warning: Fallback response failed: {escape(str(e))}[/dim]")
                    pass
            # Stop reasoning Live before returning
            stop_reasoning_live(clear=False)
            # Return prepare_tiles_info, tool_call_live_map, and flag indicating if thinking Live was stopped early
            # Also return whether content was displayed via Live to prevent duplication, and if reasoning was displayed via Live
            return (accumulated_content if accumulated_content else None, tool_calls, prepare_tiles_info, 
                    tool_call_live_map, thinking_live_stopped_early, 
                    accumulated_reasoning_content if accumulated_reasoning_content else None,
                    content_displayed_via_live,
                    reasoning_displayed_via_live)

        except KeyboardInterrupt:
            # FINALIZE in-flight Live tiles in place rather than deleting them.
            # The user already saw the partial reasoning/content, so committing
            # that frame to scrollback is the least-confusing outcome.
            try:
                if reasoning_live_manager and reasoning_live_manager.live:
                    self._finalize_live_in_place(reasoning_live_manager.live)
                    reasoning_live_manager.live = None
            except Exception:
                pass
            # In-flight tool prep/result tiles also stay visible — they show
            # what the agent was about to do when the user cancelled.
            try:
                for live_info in (tool_call_live_map or {}).values():
                    if live_info and live_info.get("live"):
                        try:
                            self._finalize_live_in_place(live_info.get("live"))
                        except Exception:
                            pass
            except Exception:
                pass

            # Finalize thinking spinner in place so the cancel point is obvious.
            if thinking_live_ref and not thinking_live_stopped_early:
                try:
                    self._finalize_live_in_place(thinking_live_ref)
                except Exception:
                    pass

            # Persist whatever was streamed so far to conversation_history so
            # the next turn has full context (and the user's transcript stays
            # consistent with what they actually saw on screen).
            try:
                saved = self._save_partial_assistant_on_interrupt(
                    accumulated_content,
                    accumulated_reasoning_content,
                )
            except Exception:
                saved = False

            # Drop the tracker so the outer caller doesn't try to clean these
            # up a second time (which is what was producing border artifacts).
            try:
                self._tracked_live_refs = []
            except Exception:
                pass

            # Print a small explicit "Interrupted" panel so the user has a
            # clear visual marker that the partial output above is not the
            # agent's final answer.
            try:
                self._print_interrupt_panel()
            except Exception:
                pass

            # Ensure thinking_live_ref is cleared so it doesn't interfere with next call
            thinking_live_ref = None
            raise
        except Exception as e:
            # Ensure all variables are initialized before returning in exception case
            if 'tool_calls' not in locals():
                tool_calls = None
            if 'prepare_tiles_info' not in locals():
                prepare_tiles_info = {}
            if 'tool_call_live_map' not in locals():
                tool_call_live_map = {}
            if 'thinking_live_stopped_early' not in locals():
                thinking_live_stopped_early = False
            if 'accumulated_reasoning_content' not in locals():
                accumulated_reasoning_content = ""
            if 'content_displayed_via_live' not in locals():
                content_displayed_via_live = False
            console.print(f"[red]Error: {escape(str(e))}[/red]")
            raise

    def _save_conversation_turn(self, user_message: str):
        """Save a complete conversation turn (user + assistant + tools) for fine-tuning"""
        if not self.log_conversations:
            return
        
        try:
            # Create a training example with the conversation turn
            training_example = {
                "messages": self.conversation_history.copy(),
                "timestamp": time.time(),
                "user_query": user_message,
                "session_cwd": self.session_cwd
            }
            
            # Append to JSONL file (one JSON object per line)
            with open(self.log_file, 'a') as f:
                f.write(json.dumps(training_example) + '\n')
        except Exception as e:
            # Don't crash if logging fails
            pass
    
    def save_session(self):
        """Save the complete session and report usage to billing server"""
        # Signal cancel + flip status on any in-flight subagents so the snapshot
        # we're about to write reflects their true post-exit state. We do this
        # here (rather than only in Ctrl+C handlers) so every exit path benefits.
        try:
            self._mark_active_subagents_interrupted()
        except Exception:
            pass
        # Record the delta of active seconds since the last save so /wrap can
        # show "pair-programming time today". Tracked as a delta so a single
        # session that gets save_session called multiple times (autopilot, etc.)
        # doesn't double-count.
        try:
            now_ts = time.time()
            anchor = float(getattr(self, "_last_active_seconds_recorded", 0.0) or 0.0)
            if anchor <= 0:
                anchor = float(self.session_start_time or now_ts)
            delta = int(max(0.0, now_ts - anchor))
            if delta > 0:
                self._record_active_seconds_for_today(delta)
                self._last_active_seconds_recorded = now_ts
        except Exception:
            pass
        # Report usage to billing server if using relay
        if self.billing_client:
            try:
                duration_seconds = int(time.time() - self.session_start_time)
                self.billing_client.report_usage({
                    'type': 'session_end',
                    'seconds': duration_seconds,
                    'messages': len(self.conversation_history)
                })
            except Exception as e:
                console.print(f"[dim]⚠️  Failed to report usage: {escape(str(e))}[/dim]")
        
        # Always save session file if there is any history
        if not self.conversation_history:
            return
        
        try:
            # API mode: overwrite a stable session file (kept for backwards compatibility)
            if getattr(self, "active_session_id", None):
                self.sessions_dir.mkdir(parents=True, exist_ok=True)
                session_file = str(self.sessions_dir / f"session-{self.active_session_id}.json")
                now = time.time()
                session_data = {
                    "session_id": str(self.active_session_id),
                    "run_id": self.run_id,
                    "window_index": self.window_index,
                    "parent_session_file": self.parent_session_file,
                    "reason": "session_end",
                    "session_start": self.session_start_time,
                    "session_end": now,
                    "duration_seconds": now - float(self.session_start_time or now),
                    "messages": self.conversation_history,
                    "summary": self.conversation_summary,
                    "session_cwd": self.session_cwd,
                    "todo_state_file": getattr(self, "todo_state_file", getattr(self.todo_manager, "state_file", ".agent_todos.json")),
                    "todos": (self.todo_manager.get_all_todos() if getattr(self, "todo_manager", None) else []),
                    "total_messages": len(self.conversation_history),
                    "subagents": self._serialize_subagents_for_save(),
                }
                self._atomic_write_json(session_file, session_data)
                console.print(f"[dim]💾 Session saved to {session_file}[/dim]")
                return

            # CLI mode: write an append-only, run-id-aware snapshot (no overwriting).
            tokens = None
            try:
                tokens = self._estimate_messages_tokens(self.conversation_history)
            except Exception:
                tokens = None
            session_file = self._write_session_snapshot_file(reason="session_end", token_estimate=tokens, extra={
                "note": "session_end snapshot",
            })
            if session_file:
                console.print(f"[dim]💾 Session saved to {session_file}[/dim]")
        except Exception:
            pass

    def _checkpoint_session(self, *, draft_assistant: Optional[Dict[str, Any]] = None, force: bool = False) -> None:
        """
        Write a durable checkpoint session file (overwrites a stable path).
        Unlike save_session(), this does NOT report usage and does NOT print.
        Intended for crash recovery during streaming/tool execution.
        """
        try:
            if not self.conversation_history:
                return
        except Exception:
            return

        now = time.time()
        try:
            last_ts = float(getattr(self, "_autosave_last_ts", 0.0) or 0.0)
            interval = float(getattr(self, "_autosave_interval_s", 2.0) or 2.0)
            if (not force) and (now - last_ts) < interval:
                return
            self._autosave_last_ts = now
        except Exception:
            # If throttling fails, still best-effort write.
            pass

        try:
            self.sessions_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Keep one stable file per run/window so we don't create thousands of snapshots.
        try:
            fname = f"session-{self._session_id_for_files}-run-{self.run_id}-w{self.window_index:03d}-checkpoint.json"
        except Exception:
            fname = f"session-{int(now)}-checkpoint.json"
        session_file = str(self.sessions_dir / fname)

        try:
            msgs: List[Dict[str, Any]] = list(self.conversation_history)
            if isinstance(draft_assistant, dict) and draft_assistant.get("role") == "assistant":
                msgs = msgs + [draft_assistant]
        except Exception:
            msgs = self.conversation_history  # type: ignore[assignment]

        try:
            tokens = None
            try:
                tokens = self._estimate_messages_tokens(msgs)
            except Exception:
                tokens = None
            payload: Dict[str, Any] = {
                "session_id": str(getattr(self, "_session_id_for_files", "")) or None,
                "run_id": self.run_id,
                "window_index": self.window_index,
                "parent_session_file": self.parent_session_file,
                "reason": "checkpoint",
                "saved_at": now,
                "session_start": self.session_start_time,
                "session_end": now,
                "duration_seconds": now - float(self.session_start_time or now),
                "session_cwd": self.session_cwd,
                "summary": self.conversation_summary,
                "total_messages": len(msgs),
                "token_estimate": tokens,
                "todos": (self.todo_manager.get_all_todos() if getattr(self, "todo_manager", None) else []),
                "messages": msgs,
                "subagents": self._serialize_subagents_for_save(),
            }
            self._atomic_write_json(session_file, payload)
        except Exception:
            pass
    
    def _normalize_paths_for_display(self, function_args: Dict[str, Any], function_name: str) -> Dict[str, Any]:
        """Convert absolute paths to relative paths for display in tool calls"""
        display_args = dict(function_args)
        
        # Normalize file_path for read_file, write_file, modify_file
        if function_name in ("read_file", "write_file", "modify_file"):
            file_path = display_args.get("file_path")
            if isinstance(file_path, str):
                # Convert absolute paths to relative to session_cwd for cleaner display
                if os.path.isabs(file_path):
                    try:
                        # Try to make it relative to session_cwd
                        if file_path.startswith(self.session_cwd):
                            rel_path = os.path.relpath(file_path, self.session_cwd)
                            display_args["file_path"] = rel_path if rel_path != "." else os.path.basename(file_path)
                        else:
                            # Path outside session_cwd - show relative to current working directory instead
                            try:
                                cwd = os.getcwd()
                                if file_path.startswith(cwd):
                                    rel_path = os.path.relpath(file_path, cwd)
                                    display_args["file_path"] = rel_path if rel_path != "." else os.path.basename(file_path)
                            except Exception:
                                pass  # Keep absolute path if we can't make it relative
                    except Exception:
                        pass
        
        # Normalize directory_path for list_directory
        elif function_name == "list_directory":
            dir_path = display_args.get("directory_path")
            if isinstance(dir_path, str) and os.path.isabs(dir_path) and dir_path.startswith(self.session_cwd):
                try:
                    rel_path = os.path.relpath(dir_path, self.session_cwd)
                    display_args["directory_path"] = rel_path if rel_path != "." else "."
                except Exception:
                    pass
        
        # Normalize working_directory for run_command
        elif function_name == "run_command":
            working_dir = display_args.get("working_directory")
            if isinstance(working_dir, str) and os.path.isabs(working_dir) and working_dir.startswith(self.session_cwd):
                try:
                    rel_path = os.path.relpath(working_dir, self.session_cwd)
                    display_args["working_directory"] = rel_path if rel_path != "." else "."
                except Exception:
                    pass
        
        return display_args

    def _normalize_paths_for_execution(self, function_args: Dict[str, Any], function_name: str) -> Dict[str, Any]:
        """Normalize paths before tool execution - handles duplicate prefixes, absolute paths, etc."""
        normalized_args = dict(function_args)
        if function_name in ("read_file", "write_file", "modify_file"):
            if not normalized_args.get("file_path") and isinstance(normalized_args.get("path"), str):
                normalized_args["file_path"] = normalized_args.get("path")
        elif function_name == "list_directory":
            if not normalized_args.get("directory_path") and isinstance(normalized_args.get("path"), str):
                normalized_args["directory_path"] = normalized_args.get("path")
        
        try:
            if function_name == "run_command":
                # Default all commands to run inside the session's current working dir unless overridden
                working_dir = normalized_args.get("working_directory")
                session_dir = self.session_cwd
                # Ensure session directory exists
                try:
                    if session_dir:
                        os.makedirs(session_dir, exist_ok=True)
                except Exception:
                    pass

                def _needs_override(wd: Any) -> bool:
                    if not wd:
                        return True
                    if not isinstance(wd, str):
                        return True
                    wd = wd.strip()
                    if not wd:
                        return True
                    if not os.path.isabs(wd):
                        return True
                    # If the path doesn't exist or isn't under the session directory, override
                    if not os.path.exists(wd):
                        return True
                    try:
                        session_norm = os.path.normpath(session_dir) if session_dir else None
                        wd_norm = os.path.normpath(wd)
                        if session_norm and not wd_norm.startswith(session_norm):
                            return True
                    except Exception:
                        return True
                    return False

                if _needs_override(working_dir):
                    normalized_args["working_directory"] = session_dir
            elif function_name in ("read_file", "write_file", "modify_file"):
                file_path = normalized_args.get("file_path")
                if isinstance(file_path, str) and file_path.strip():
                    file_path = file_path.strip()
                    
                    if os.path.isabs(file_path):
                        # Absolute paths should remain absolute. Rewriting them into session_cwd can corrupt
                        # a valid absolute path into the wrong location (e.g. /path/to/site/index.html -> <session_cwd>/index.html).
                        try:
                            normalized_args["file_path"] = os.path.normpath(file_path)
                        except Exception:
                            normalized_args["file_path"] = file_path
                    else:
                        # Relative path - resolve against current working directory
                        # CRITICAL FIX: Detect and remove duplicate directory prefixes
                        cwd_norm = os.path.normpath(self.session_cwd)
                        file_path_norm = os.path.normpath(file_path)
                        
                        # Get the last component of current_working_dir
                        cwd_basename = os.path.basename(cwd_norm)
                        # Check if file_path starts with the same directory name
                        if file_path_norm.startswith(cwd_basename + os.sep) or file_path_norm == cwd_basename:
                            # Strip the duplicate prefix
                            if file_path_norm == cwd_basename:
                                file_path = "."
                            else:
                                file_path = file_path_norm[len(cwd_basename) + 1:]
                        
                        resolved_path = os.path.normpath(os.path.join(self.session_cwd, file_path))
                        normalized_args["file_path"] = resolved_path
            elif function_name == "list_directory":
                dir_path = normalized_args.get("directory_path")
                if isinstance(dir_path, str) and dir_path.strip():
                    if not os.path.isabs(dir_path):
                        # CRITICAL FIX: Detect and remove duplicate directory prefixes (same as read_file)
                        cwd_norm = os.path.normpath(self.session_cwd)
                        dir_path_norm = os.path.normpath(dir_path)
                        
                        # Get the last component of current_working_dir
                        cwd_basename = os.path.basename(cwd_norm)
                        # Check if dir_path starts with the same directory name
                        if dir_path_norm.startswith(cwd_basename + os.sep) or dir_path_norm == cwd_basename:
                            # Strip the duplicate prefix
                            if dir_path_norm == cwd_basename:
                                dir_path = "."
                            else:
                                dir_path = dir_path_norm[len(cwd_basename) + 1:]
                        
                        normalized_args["directory_path"] = str(Path(self.session_cwd) / dir_path)
                    else:
                        resolved = os.path.normpath(dir_path)
                        session_norm = os.path.normpath(self.session_cwd)
                        if resolved.startswith(session_norm):
                            normalized_args["directory_path"] = resolved
                        else:
                            normalized_args["directory_path"] = session_norm
        except Exception as norm_err:
            print(f"Path normalization warning: {norm_err}")
        
        return normalized_args

    @staticmethod
    def _extract_partial_json_string(raw: str, key: str) -> Optional[str]:
        """Decode a string value for `key` from a possibly-incomplete JSON object.

        Walks the buffer manually so we can return the partially-streamed tail
        of a string value even when the JSON hasn't been closed yet. Handles
        common escapes (\\n, \\t, \\", \\\\, \\uXXXX, ...). Returns None if the
        key hasn't been encountered yet.
        """
        if not raw or not key:
            return None
        search = f'"{key}"'
        start = 0
        while True:
            idx = raw.find(search, start)
            if idx < 0:
                return None
            pos = idx + len(search)
            n = len(raw)
            while pos < n and raw[pos] in ' \t\r\n':
                pos += 1
            if pos < n and raw[pos] == ':':
                break
            start = idx + 1
        pos += 1
        n = len(raw)
        while pos < n and raw[pos] in ' \t\r\n':
            pos += 1
        if pos >= n or raw[pos] != '"':
            return None
        pos += 1
        out: List[str] = []
        while pos < n:
            c = raw[pos]
            if c == '"':
                break
            if c == '\\':
                if pos + 1 >= n:
                    break
                esc = raw[pos + 1]
                simple = {
                    'n': '\n', 't': '\t', 'r': '\r', '"': '"',
                    '\\': '\\', '/': '/', 'b': '\b', 'f': '\f',
                }
                if esc in simple:
                    out.append(simple[esc])
                    pos += 2
                elif esc == 'u':
                    if pos + 6 > n:
                        break
                    try:
                        out.append(chr(int(raw[pos + 2:pos + 6], 16)))
                        pos += 6
                    except ValueError:
                        break
                else:
                    out.append(esc)
                    pos += 2
            else:
                out.append(c)
                pos += 1
        return ''.join(out)

    @staticmethod
    def _syntax_lexer_for_path(file_path: Optional[str]) -> str:
        """Choose a pygments lexer name from a file path/extension."""
        if not file_path:
            return "text"
        basename = os.path.basename(file_path).lower()
        special = {
            'dockerfile': 'dockerfile',
            'makefile': 'makefile',
            '.env': 'bash',
            '.env.example': 'bash',
            '.gitignore': 'text',
            '.editorconfig': 'ini',
        }
        if basename in special:
            return special[basename]
        ext = os.path.splitext(basename)[1].lstrip('.')
        mapping = {
            'py': 'python', 'pyi': 'python', 'pyw': 'python',
            'js': 'javascript', 'mjs': 'javascript', 'cjs': 'javascript',
            'jsx': 'jsx', 'ts': 'typescript', 'tsx': 'tsx',
            'json': 'json', 'jsonl': 'json',
            'toml': 'toml', 'yaml': 'yaml', 'yml': 'yaml',
            'md': 'markdown', 'markdown': 'markdown',
            'html': 'html', 'htm': 'html', 'xml': 'xml', 'svg': 'xml',
            'css': 'css', 'scss': 'scss', 'sass': 'sass', 'less': 'less',
            'sh': 'bash', 'bash': 'bash', 'zsh': 'bash', 'fish': 'fish',
            'ps1': 'powershell',
            'go': 'go', 'rs': 'rust', 'java': 'java', 'kt': 'kotlin', 'scala': 'scala',
            'c': 'c', 'h': 'c', 'cpp': 'cpp', 'cc': 'cpp', 'hpp': 'cpp', 'cxx': 'cpp',
            'rb': 'ruby', 'php': 'php', 'swift': 'swift', 'sql': 'sql',
            'ini': 'ini', 'cfg': 'ini', 'conf': 'ini',
            'env': 'bash',
            'txt': 'text',
        }
        return mapping.get(ext, 'text')

    @staticmethod
    def _tail_lines(text: str, n: int = 18) -> Tuple[str, int]:
        """Return the last `n` lines of `text` and the total line count."""
        if not text:
            return "", 0
        lines = text.splitlines()
        total = len(lines)
        if total <= n:
            return text if not text.endswith('\n') else text[:-1], total
        return '\n'.join(lines[-n:]), total

    @staticmethod
    def _reuse_spinner(spinner: Optional[Any], text: str) -> Any:
        """Update `spinner`'s text in place (preserves animation frame), or
        return a fresh Spinner when the caller didn't pre-allocate one.
        """
        if spinner is not None:
            try:
                spinner.update(text=text)
                return spinner
            except Exception:
                pass
        return Spinner("dots", text=text)

    def _build_streaming_write_panel(
        self,
        file_path: Optional[str],
        content_partial: Optional[str],
        *,
        preview_lines: int = 18,
        complete: bool = False,
        spinner: Optional[Any] = None,
    ) -> Panel:
        """Render a live preview panel for an in-flight write_file call."""
        title = "[bold blue]📝 Write File[/bold blue]"
        path_str = file_path or "…"
        if not content_partial:
            subtitle = f"[dim]Writing:[/dim] {path_str}"
            body = self._reuse_spinner(spinner, subtitle)
            return Panel(body, title=title, border_style="blue", padding=(0, 1))

        tail, total_lines = self._tail_lines(content_partial, preview_lines)
        lexer = self._syntax_lexer_for_path(file_path)
        try:
            body_preview = Syntax(
                tail,
                lexer,
                theme="monokai",
                line_numbers=False,
                word_wrap=False,
                background_color="default",
            )
        except Exception:
            body_preview = Text(tail)

        bytes_written = len(content_partial.encode('utf-8'))
        status = f"[dim]Writing:[/dim] {path_str}  [dim]· {total_lines} lines · {bytes_written:,} B"
        if complete:
            status += "[/dim]"
            header: Any = Text.from_markup(status)
        else:
            status += " streaming…[/dim]"
            header = self._reuse_spinner(spinner, status)
        return Panel(Group(header, body_preview), title=title, border_style="blue", padding=(0, 1))

    def _build_streaming_modify_panel(
        self,
        file_path: Optional[str],
        parsed_args: Dict[str, Any],
        raw_args: str,
        *,
        preview_lines: int = 18,
        complete: bool = False,
        spinner: Optional[Any] = None,
    ) -> Panel:
        """Render a live preview panel for an in-flight modify_file call.

        Tries to surface the most informative preview we can reconstruct from
        the partial args: unified diff patch > old/new text diff > raw new text
        > raw content. Falls back to a spinner when nothing useful is available
        yet.
        """
        title = "[bold magenta]✏️  Modify File[/bold magenta]"
        path_str = file_path or "…"
        operation = parsed_args.get("operation") if isinstance(parsed_args, dict) else None

        def _arg_or_partial(name: str) -> Optional[str]:
            val = parsed_args.get(name) if isinstance(parsed_args, dict) else None
            if isinstance(val, str) and val:
                return val
            return self._extract_partial_json_string(raw_args, name)

        patch = _arg_or_partial("patch")
        new_text = _arg_or_partial("new_text")
        old_text = _arg_or_partial("old_text")
        content = _arg_or_partial("content")

        preview_body: Any = None
        detail = ""

        if isinstance(patch, str) and patch.strip():
            tail, total = self._tail_lines(patch, preview_lines)
            try:
                preview_body = Syntax(
                    tail, "diff", theme="monokai", line_numbers=False,
                    word_wrap=False, background_color="default",
                )
            except Exception:
                preview_body = Text(tail)
            detail = f"patch · {total} line{'s' if total != 1 else ''}"
        elif isinstance(new_text, str) and new_text:
            diff_rendered = False
            if isinstance(old_text, str) and old_text:
                try:
                    diff_lines = list(difflib.unified_diff(
                        old_text.splitlines(),
                        new_text.splitlines(),
                        fromfile="before",
                        tofile="after",
                        lineterm="",
                        n=2,
                    ))
                    if diff_lines:
                        diff_text = '\n'.join(diff_lines)
                        tail, total = self._tail_lines(diff_text, preview_lines)
                        try:
                            preview_body = Syntax(
                                tail, "diff", theme="monokai", line_numbers=False,
                                word_wrap=False, background_color="default",
                            )
                        except Exception:
                            preview_body = Text(tail)
                        detail = f"replace_text · {total} diff line{'s' if total != 1 else ''}"
                        diff_rendered = True
                except Exception:
                    diff_rendered = False
            if not diff_rendered:
                tail, total = self._tail_lines(new_text, preview_lines)
                lexer = self._syntax_lexer_for_path(file_path)
                try:
                    preview_body = Syntax(
                        tail, lexer, theme="monokai", line_numbers=False,
                        word_wrap=False, background_color="default",
                    )
                except Exception:
                    preview_body = Text(tail)
                detail = f"new_text · {total} line{'s' if total != 1 else ''}"
        elif isinstance(old_text, str) and old_text.strip():
            # Models usually JSON-stream keys in declaration order. For
            # replace_text that means a multi‑KB `old_text` can arrive in full
            # before `"new_text"` even begins — previously we showed only a
            # spinner until `new_text` bytes appeared, which feels like the tile
            # is "stuck". Surface the tail of `old_text` as a "before" preview.
            tail, total = self._tail_lines(old_text, preview_lines)
            lexer = self._syntax_lexer_for_path(file_path)
            try:
                preview_body = Syntax(
                    tail, lexer, theme="monokai", line_numbers=False,
                    word_wrap=False, background_color="default",
                )
            except Exception:
                preview_body = Text(tail)
            detail = (
                f"old_text · {total} line{'s' if total != 1 else ''} · awaiting new_text"
            )
        elif isinstance(content, str) and content:
            tail, total = self._tail_lines(content, preview_lines)
            lexer = self._syntax_lexer_for_path(file_path)
            try:
                preview_body = Syntax(
                    tail, lexer, theme="monokai", line_numbers=False,
                    word_wrap=False, background_color="default",
                )
            except Exception:
                preview_body = Text(tail)
            detail = f"content · {total} line{'s' if total != 1 else ''}"

        subtitle = f"[dim]Modifying:[/dim] {path_str}"
        if operation:
            subtitle += f"  [dim]· op: {operation}[/dim]"
        if detail:
            subtitle += f"  [dim]· {detail}[/dim]"

        if preview_body is None:
            body = self._reuse_spinner(spinner, subtitle)
            return Panel(body, title=title, border_style="magenta", padding=(0, 1))

        if complete:
            header: Any = Text.from_markup(subtitle)
        else:
            header = self._reuse_spinner(spinner, subtitle + "  [dim]streaming…[/dim]")
        return Panel(Group(header, preview_body), title=title, border_style="magenta", padding=(0, 1))

    def _build_file_content_preview(
        self,
        file_path: Optional[str],
        content: str,
        *,
        max_lines: int = 20,
        show_line_numbers: bool = False,
        start_line: int = 1,
    ) -> Optional[Any]:
        """Return a syntax-highlighted preview of file content for a result tile.

        Shows the first `max_lines` so the head of the file is always visible.
        Adds a `… N more lines hidden` footer for longer files. Returns None
        if content is empty/unavailable (caller should fall back).
        """
        if not isinstance(content, str) or not content:
            return None
        lines = content.splitlines()
        total = len(lines)
        if total == 0:
            return None
        truncated = total > max_lines
        shown = lines[:max_lines]
        body = '\n'.join(shown)
        lexer = self._syntax_lexer_for_path(file_path)
        try:
            syntax = Syntax(
                body,
                lexer,
                theme="monokai",
                line_numbers=show_line_numbers,
                start_line=start_line if show_line_numbers else 1,
                word_wrap=False,
                background_color="default",
            )
        except Exception:
            syntax = Text(body)
        if truncated:
            note = Text.from_markup(
                f"[dim]… {total - max_lines} more line{'s' if (total - max_lines) != 1 else ''} hidden[/dim]"
            )
            return Group(syntax, note)
        return syntax

    def _build_modify_result_diff(
        self,
        function_args: Dict[str, Any],
        operation: str,
        file_path: Optional[str],
        *,
        max_lines: int = 18,
    ) -> Optional[Any]:
        """Reconstruct a diff preview for a completed modify_file call.

        Uses whatever the model supplied in `function_args` (patch / old_text
        + new_text / edits / insert content) to produce a unified diff that is
        rendered with the diff lexer. Returns None when no informative preview
        can be built; the caller should then show the plain status line.
        """
        if not isinstance(function_args, dict):
            return None

        diff_str: Optional[str] = None
        extra_note: Optional[str] = None

        patch_text = function_args.get("patch")
        old_text = function_args.get("old_text")
        new_text = function_args.get("new_text")
        edits = function_args.get("edits")
        insert_content = function_args.get("content")
        new_str = function_args.get("new_str")  # alt name sometimes used

        if isinstance(patch_text, str) and patch_text.strip():
            diff_str = patch_text
        elif isinstance(old_text, str) and isinstance(new_text, str) and (old_text or new_text):
            try:
                diff_lines = list(difflib.unified_diff(
                    old_text.splitlines(),
                    new_text.splitlines(),
                    fromfile="before",
                    tofile="after",
                    lineterm="",
                    n=2,
                ))
                if diff_lines:
                    diff_str = '\n'.join(diff_lines)
            except Exception:
                diff_str = None
        elif isinstance(edits, list) and edits:
            parts: List[str] = []
            max_edit_preview = 5
            for i, edit in enumerate(edits[:max_edit_preview]):
                if not isinstance(edit, dict):
                    continue
                o = edit.get("old_text") or edit.get("old") or edit.get("from") or ""
                n_ = edit.get("new_text") or edit.get("new") or edit.get("to") or ""
                if not isinstance(o, str):
                    o = str(o)
                if not isinstance(n_, str):
                    n_ = str(n_)
                try:
                    dl = list(difflib.unified_diff(
                        o.splitlines(),
                        n_.splitlines(),
                        fromfile=f"edit{i+1}.before",
                        tofile=f"edit{i+1}.after",
                        lineterm="",
                        n=1,
                    ))
                    if dl:
                        parts.append('\n'.join(dl))
                except Exception:
                    continue
            if parts:
                diff_str = '\n\n'.join(parts)
                if len(edits) > max_edit_preview:
                    extra_note = f"… {len(edits) - max_edit_preview} more edit(s) hidden"
        elif operation == "insert" and isinstance(insert_content, str) and insert_content:
            diff_str = '\n'.join(f"+{ln}" for ln in insert_content.splitlines())
        elif operation == "replace" and isinstance(insert_content, str) and insert_content:
            diff_str = '\n'.join(f"+{ln}" for ln in insert_content.splitlines())
        elif isinstance(new_str, str) and new_str:
            diff_str = '\n'.join(f"+{ln}" for ln in new_str.splitlines())

        if not diff_str:
            return None

        diff_lines_all = diff_str.splitlines()
        total = len(diff_lines_all)
        truncated = total > max_lines
        body = '\n'.join(diff_lines_all[:max_lines])

        try:
            syntax = Syntax(
                body,
                "diff",
                theme="monokai",
                line_numbers=False,
                word_wrap=False,
                background_color="default",
            )
        except Exception:
            syntax = Text(body)

        pieces: List[Any] = [syntax]
        if truncated:
            pieces.append(Text.from_markup(
                f"[dim]… {total - max_lines} more diff line{'s' if (total - max_lines) != 1 else ''} hidden[/dim]"
            ))
        if extra_note:
            pieces.append(Text.from_markup(f"[dim]{extra_note}[/dim]"))
        if len(pieces) == 1:
            return pieces[0]
        return Group(*pieces)

    def _minimize_tool_result(self, function_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Minimize tool results before storing them in conversation history.

        Goal: avoid blowing up context while also avoiding misleadingly-small truncations (e.g. 4k chars)
        that cause the model to think a file read is "truncated".

        Strategy: Only truncate when the payload exceeds a token-budget that is a small fraction of the
        overall context window.
        """
        if not isinstance(result, dict):
            return {"success": False, "error": "Tool returned non-dict result", "raw": str(result)}

        # Token budget: fraction of the model context window (soft cap), with a hard clamp.
        try:
            frac = float(getattr(self.config, "tool_result_token_fraction", 0.08))
        except Exception:
            frac = 0.08
        frac = max(0.0, min(1.0, frac))

        try:
            hard_cap = int(getattr(self.config, "tool_result_token_cap", 8000))
        except Exception:
            hard_cap = 8000
        hard_cap = max(500, min(20000, hard_cap))

        # If frac==0, treat as "no truncation".
        if frac <= 0:
            return result

        budget_tokens = int(max(500, min(hard_cap, int(self.max_context_tokens * frac))))

        def _truncate_to_budget(txt: Any, max_tokens: int) -> str:
            s = txt if isinstance(txt, str) else ("" if txt is None else str(txt))
            try:
                if self._estimate_tokens(s) <= max_tokens:
                    return s
            except Exception:
                # Fallback on chars if estimation fails
                if len(s) <= max_tokens * 3:
                    return s
            max_chars = max(1, int(max_tokens * 3))  # heuristic: ~3 chars per token
            if len(s) <= max_chars:
                return s
            head = s[: max_chars // 2]
            tail = s[-max_chars // 2 :]
            omitted = max(0, len(s) - len(head) - len(tail))
            return f"{head}\n\n… [truncated ~{omitted} chars to fit ~{max_tokens} token budget] …\n\n{tail}"

        minimized: Dict[str, Any] = dict(result)
        truncated_any = False

        # Cap read_file content based on token budget (usually large enough to hold a few hundred lines).
        if function_name == "read_file" and "content" in minimized:
            before = minimized.get("content", "")
            after = _truncate_to_budget(before, budget_tokens)
            minimized["content"] = after
            truncated_any = truncated_any or (isinstance(before, str) and isinstance(after, str) and after != before)

        # Cap run_command outputs; allocate a portion of the budget per stream.
        if function_name == "run_command":
            per_stream = max(300, int(budget_tokens * 0.35))
            if "stdout" in minimized:
                b = minimized.get("stdout", "")
                a = _truncate_to_budget(b, per_stream)
                minimized["stdout"] = a
                truncated_any = truncated_any or (isinstance(b, str) and isinstance(a, str) and a != b)
            if "stderr" in minimized:
                b = minimized.get("stderr", "")
                a = _truncate_to_budget(b, per_stream)
                minimized["stderr"] = a
                truncated_any = truncated_any or (isinstance(b, str) and isinstance(a, str) and a != b)

        # Cap list_directory items to avoid huge payloads.
        if function_name == "list_directory":
            items = minimized.get("items")
            if isinstance(items, list) and len(items) > 200:
                minimized["items"] = items[:200]
                minimized["note"] = f"items truncated to first 200 of {len(items)}"
                truncated_any = True

        if truncated_any:
            minimized["truncated"] = True
            minimized["truncation_budget_tokens"] = budget_tokens

        return minimized

    def _get_first_user_message_ts(self) -> Optional[float]:
        """Best-effort: find a timestamp for the first user message in history (used to anchor autopilot on resume)."""
        try:
            for m in (self.conversation_history or []):
                if m.get("role") == "user":
                    ts = m.get("ts") or m.get("timestamp")
                    if isinstance(ts, (int, float)) and ts > 0:
                        return float(ts)
        except Exception:
            pass
        return None

    def _arm_autopilot_if_possible(self) -> None:
        """
        If --work-for (or /workfor) is set and we already have conversation history,
        start the autopilot timer immediately so the agent doesn't stop at the input prompt after resume.
        """
        try:
            if self.continuous_work_seconds <= 0:
                # -1 means infinite
                if self.continuous_work_seconds != -1:
                    return
            if self._continuous_until_ts is not None:
                return
            # If there's no prior user message, keep the "starts on your first prompt" behavior.
            if not any(m.get("role") == "user" for m in (self.conversation_history or [])):
                return

            started_ts = self._get_first_user_message_ts() or time.time()
            self._continuous_started_ts = float(started_ts)
            if self.continuous_work_seconds == -1:
                self._continuous_until_ts = None
            else:
                self._continuous_until_ts = float(started_ts) + float(self.continuous_work_seconds)
            self._continuous_anchor_date = datetime.fromtimestamp(float(started_ts)).strftime("%Y-%m-%d")
        except Exception:
            return

    def _is_pid_running(self, pid: Any) -> bool:
        try:
            import os
            p = int(pid)
            if p <= 0:
                return False
            # kill(pid, 0) checks existence without sending a signal
            os.kill(p, 0)
            return True
        except Exception:
            return False

    def _record_background_job(self, command: str, working_directory: str, pid: int, log_file: Optional[str], note: Optional[str]) -> str:
        self._bg_job_seq += 1
        job_id = f"bg{self._bg_job_seq}"
        self.background_jobs[job_id] = {
            "job_id": job_id,
            "pid": int(pid),
            "command": command,
            "working_directory": working_directory,
            "log_file": log_file,
            "note": note,
            "started_at": time.time(),
            "status": "running",
        }
        return job_id

    def _maybe_record_background_job(self, function_name: str, function_args: Dict[str, Any], tool_result: Dict[str, Any]) -> None:
        """If a run_command was detached, track it as a background job and annotate the tool result with job_id."""
        try:
            if function_name != "run_command":
                return
            if not isinstance(tool_result, dict):
                return
            pid = tool_result.get("pid")
            # Detached jobs return pid + returncode None
            if pid is None:
                return
            if tool_result.get("returncode", "x") is not None:
                return
            cmd = (function_args.get("command") or "").strip()
            wd = (function_args.get("working_directory") or self.session_cwd or os.getcwd())
            log_file = tool_result.get("log_file")
            note = tool_result.get("note")
            job_id = self._record_background_job(cmd, wd, int(pid), log_file, note)
            tool_result["job_id"] = job_id
            # Helpful UX hint in CLI
            try:
                console.print(f"[dim]🧪 Background job started: {job_id} (pid {pid}). Use /jobs to list, /kill {job_id} to stop.[/dim]")
                if log_file:
                    console.print(f"[dim]↳ log: {log_file}[/dim]")
            except Exception:
                pass
        except Exception:
            return

    def _run_subagent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run (or continue) a subagent conversation with full tool capabilities.

        This is invoked via the `run_subagent` tool. It maintains per-subagent conversation state
        in-memory so the parent agent can continue the same subagent thread by passing subagent_id.
        """
        import uuid
        # Back-compat: some prompts call this with {job_description,instructions} instead of {prompt}
        prompt = (args.get("prompt") or "").strip()
        if not prompt:
            jd = (args.get("job_description") or "").strip()
            ins = (args.get("instructions") or "").strip()
            prompt = (jd + ("\n\n" if jd and ins else "") + ins).strip()
        if not prompt:
            return {"success": False, "error": "prompt is required"}

        subagent_id = (args.get("subagent_id") or "").strip() or str(uuid.uuid4())
        parent_subagent_id = (args.get("parent_subagent_id") or "").strip() or None
        label = (args.get("label") or "").strip() or None
        max_turns = int(args.get("max_turns") or 50)
        max_turns = max(1, min(200, max_turns))
        max_tokens = args.get("max_tokens", None)
        raw_model_timeout = args.get("model_timeout_seconds", args.get("model_timeout", None))
        if raw_model_timeout is None:
            raw_model_timeout = os.environ.get("SWEET_SUBAGENT_MODEL_TIMEOUT", "90")
        model_timeout_s: Optional[float]
        try:
            model_timeout_s = float(raw_model_timeout)
            if model_timeout_s <= 0:
                model_timeout_s = None
            elif model_timeout_s < 5:
                model_timeout_s = 5.0
            elif model_timeout_s > 600:
                model_timeout_s = 600.0
        except Exception:
            model_timeout_s = 90.0

        # Optional role-specialization: if the parent passes a `system_prompt`,
        # the subagent gets a focused system message scoped to that discipline
        # instead of inheriting the full co-CEO orchestration prompt. This only
        # applies on FIRST run of a subagent; continuation calls keep whatever
        # system message is already at the top of the session history.
        custom_system_prompt = args.get("system_prompt")
        if isinstance(custom_system_prompt, str):
            custom_system_prompt = custom_system_prompt.strip() or None
        else:
            custom_system_prompt = None

        # Load/create session state
        sess = self.subagent_sessions.get(subagent_id)
        if not sess:
            initial_system_prompt = custom_system_prompt or self.system_prompt
            sess = {
                "conversation_history": [
                    {"role": "system", "content": initial_system_prompt},
                ],
                "conversation_summary": "",
                "session_cwd": self.session_cwd,
                "created_at": time.time(),
                "parent_subagent_id": parent_subagent_id,
                "label": label,
                # Track whether this subagent was specialized via a custom system prompt.
                "custom_system_prompt": bool(custom_system_prompt),
                # Subagent gets its own todos by default to avoid stomping parent todos
                "todo_manager": TodoManager(f".agent_todos.subagent.{subagent_id[:8]}.json"),
                # Async event stream: list of {type, role?, content?, ts, meta?}
                "events": [],
            }
            self.subagent_sessions[subagent_id] = sess
        else:
            # Allow parent/label metadata to be filled in on first continuation call
            if parent_subagent_id and not sess.get("parent_subagent_id"):
                sess["parent_subagent_id"] = parent_subagent_id
            if label and not sess.get("label"):
                sess["label"] = label

        hist: List[Dict[str, Any]] = sess["conversation_history"]
        todo_mgr: TodoManager = sess["todo_manager"]
        events: List[Dict[str, Any]] = sess["events"]

        progress_callback = args.get("_progress_callback")

        def emit(evt: Dict[str, Any]) -> None:
            evt = dict(evt)
            evt.setdefault("ts", time.time())
            events.append(evt)
            if callable(progress_callback):
                try:
                    progress_callback(evt)
                except Exception:
                    pass

        # Emit startup metadata for UI consumers instead of printing to stdout.
        emit({
            "type": "status",
            "status": "started",
            "subagent_id": subagent_id,
            "parent_subagent_id": parent_subagent_id,
            "label": label,
        })

        # Add user message
        hist.append({"role": "user", "content": prompt})
        emit({"type": "message", "role": "user", "content": prompt})

        # Run iterative tool-calling loop. Model calls are streamed (mirroring the
        # parent agent's loop) so:
        #   - long generations show live progress via periodic `model_streaming` events,
        #   - cancellation actually interrupts an in-flight call (we break the chunk loop),
        #   - and tool calls are assembled incrementally instead of blocking on a buffered response.
        turns = 0
        last_assistant_text = ""
        tool_call_count = 0
        cancel_event: Optional[Event] = args.get("_cancel_event")  # internal
        while turns < max_turns:
            turns += 1
            if cancel_event is not None and cancel_event.is_set():
                emit({"type": "status", "status": "cancelled"})
                return {"success": True, "status": "cancelled", "subagent_id": subagent_id, "events": events}

            try:
                sub_messages = self._sanitize_tool_calls_for_api(hist)
            except Exception:
                sub_messages = hist
            emit({
                "type": "status",
                "status": "model_request",
                "turn": turns,
                "message_count": len(sub_messages),
                "timeout_s": model_timeout_s,
                "stream": True,
            })

            accumulated_content = ""
            accumulated_reasoning = ""
            tool_calls_dict: Dict[int, Dict[str, Any]] = {}
            stream = None
            stream_failed: Optional[str] = None
            cancelled_during_stream = False
            last_progress_emit = time.time()
            content_chars_at_last_emit = 0
            reasoning_chars_at_last_emit = 0
            try:
                stream = self.client.chat(
                    messages=sub_messages,
                    tools=self.tool_registry.get_tool_definitions(),
                    stream=True,
                    max_tokens=max_tokens,
                    timeout=model_timeout_s,
                )
                for chunk in stream:
                    if cancel_event is not None and cancel_event.is_set():
                        cancelled_during_stream = True
                        break
                    if not chunk or not getattr(chunk, "choices", None):
                        continue
                    delta = chunk.choices[0].delta

                    # Reasoning stream (deepseek-reasoner / v4 thinking mode)
                    reasoning_delta = None
                    try:
                        if getattr(delta, "reasoning_content", None):
                            reasoning_delta = delta.reasoning_content
                        elif getattr(delta, "reasoning", None):
                            reasoning_delta = delta.reasoning
                        else:
                            extra = getattr(delta, "__pydantic_extra__", None) or getattr(delta, "model_extra", None)
                            if isinstance(extra, dict):
                                reasoning_delta = extra.get("reasoning_content") or extra.get("reasoning") or extra.get("thinking")
                    except Exception:
                        reasoning_delta = None
                    if reasoning_delta:
                        accumulated_reasoning += str(reasoning_delta)

                    # Content stream
                    if getattr(delta, "content", None):
                        accumulated_content += delta.content

                    # Tool-call stream: assemble dicts indexed by tc.index
                    if getattr(delta, "tool_calls", None):
                        for tc in delta.tool_calls:
                            try:
                                idx = tc.index
                            except Exception:
                                idx = 0
                            if idx not in tool_calls_dict:
                                tool_calls_dict[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}
                            if getattr(tc, "id", None):
                                tool_calls_dict[idx]["id"] = tc.id
                            fn = getattr(tc, "function", None)
                            if fn:
                                fname_chunk = getattr(fn, "name", None)
                                if fname_chunk:
                                    tool_calls_dict[idx]["function"]["name"] = fname_chunk
                                fargs_chunk = getattr(fn, "arguments", None)
                                if fargs_chunk:
                                    tool_calls_dict[idx]["function"]["arguments"] += fargs_chunk

                    # Periodic progress emit so polling reflects live work even
                    # when the model is generating large content/tool args.
                    now = time.time()
                    if now - last_progress_emit >= 1.5 and (
                        len(accumulated_content) > content_chars_at_last_emit
                        or len(accumulated_reasoning) > reasoning_chars_at_last_emit
                        or tool_calls_dict
                    ):
                        tc_preview: List[Dict[str, Any]] = []
                        for tidx in sorted(tool_calls_dict.keys()):
                            td = tool_calls_dict[tidx]
                            tc_preview.append({
                                "name": td["function"].get("name", ""),
                                "args_chars": len(td["function"].get("arguments", "") or ""),
                            })
                        emit({
                            "type": "status",
                            "status": "model_streaming",
                            "turn": turns,
                            "content_chars": len(accumulated_content),
                            "reasoning_chars": len(accumulated_reasoning),
                            "tool_calls_inflight": tc_preview,
                        })
                        last_progress_emit = now
                        content_chars_at_last_emit = len(accumulated_content)
                        reasoning_chars_at_last_emit = len(accumulated_reasoning)

                    # Honor model-signaled completion
                    try:
                        fr = getattr(chunk.choices[0], "finish_reason", None)
                        if fr:
                            break
                    except Exception:
                        pass
            except Exception as e:
                stream_failed = str(e)
            finally:
                try:
                    close_fn = getattr(stream, "close", None) if stream is not None else None
                    if callable(close_fn):
                        close_fn()
                except Exception:
                    pass

            if cancelled_during_stream:
                emit({"type": "status", "status": "cancelled"})
                return {"success": True, "status": "cancelled", "subagent_id": subagent_id, "events": events}

            if stream_failed:
                emit({"type": "status", "status": "model_error", "turn": turns, "error": stream_failed})
                return {"success": False, "error": f"Subagent model call failed: {stream_failed}", "subagent_id": subagent_id, "events": events}

            content = accumulated_content
            reasoning_content = accumulated_reasoning
            tool_calls = [tool_calls_dict[i] for i in sorted(tool_calls_dict.keys())]

            emit({
                "type": "status",
                "status": "model_response",
                "turn": turns,
                "content_chars": len(content),
                "reasoning_chars": len(reasoning_content),
                "tool_call_count": len(tool_calls),
            })

            if tool_calls:
                # Record assistant tool call request (dicts; matches parent agent shape).
                # In DeepSeek V4 thinking mode, `reasoning_content` must round-trip
                # on every tool-call assistant turn — even when the model chained
                # the call without emitting any reasoning text — or the API
                # rejects the next request. Always include the field; default "".
                assistant_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": content or "",
                    "tool_calls": tool_calls,
                    "reasoning_content": reasoning_content or "",
                }
                hist.append(assistant_msg)
                if content:
                    emit({"type": "message", "role": "assistant", "content": content})
                elif reasoning_content:
                    emit({"type": "message", "role": "assistant", "content": reasoning_content})

                # Execute tools
                for tc in tool_calls:
                    tool_call_count += 1
                    if cancel_event is not None and cancel_event.is_set():
                        emit({"type": "status", "status": "cancelled"})
                        return {"success": True, "status": "cancelled", "subagent_id": subagent_id, "events": events}
                    tool_call_id = tc.get("id", "") or ""
                    fn = tc.get("function") or {}
                    fname = fn.get("name", "") or ""
                    args_str = fn.get("arguments", "") or "{}"
                    try:
                        cleaned = args_str.strip()
                        if cleaned.startswith("```"):
                            fence_end = cleaned.find("\n")
                            if fence_end != -1:
                                cleaned = cleaned[fence_end + 1:]
                                if cleaned.endswith("```"):
                                    cleaned = cleaned[:-3]
                                cleaned = cleaned.strip()
                        fargs = json.loads(cleaned) if cleaned else {}
                    except Exception:
                        fargs = {}

                    # Ensure run_command runs from session cwd if not specified
                    if fname == "run_command" and not fargs.get("working_directory"):
                        fargs["working_directory"] = sess.get("session_cwd") or self.session_cwd
                    if fname == "run_command" and "timeout" not in fargs:
                        fargs["timeout"] = 30
                    if fname == "run_command" and "timeout_action" not in fargs:
                        fargs["timeout_action"] = "kill"

                    try:
                        emit({"type": "status", "status": "tool_start", "tool_name": fname, "turn": turns})
                        if fname == "manage_todos":
                            res = self.tool_registry.execute_tool(fname, fargs, todo_mgr)
                        elif fname == "run_subagent":
                            # Allow nested subagents via same runner, but keep it bounded by the model.
                            # Record hierarchy automatically: this subagent is the parent of the child subagent.
                            if "parent_subagent_id" not in fargs:
                                fargs["parent_subagent_id"] = subagent_id
                            res = self.tool_registry.execute_tool(fname, fargs, self._run_subagent)
                        elif fname == "run_subagent_async":
                            if "parent_subagent_id" not in fargs:
                                fargs["parent_subagent_id"] = subagent_id
                            res = self.tool_registry.execute_tool(fname, fargs, self._run_subagent_async)
                        elif fname == "poll_subagent":
                            res = self.tool_registry.execute_tool(fname, fargs, self._poll_subagent)
                        elif fname == "list_subagents":
                            res = self.tool_registry.execute_tool(fname, fargs, self._list_subagents)
                        elif fname == "cancel_subagent_job":
                            res = self.tool_registry.execute_tool(fname, fargs, self._cancel_subagent_job)
                        else:
                            res = self.tool_registry.execute_tool(fname, fargs)
                        # Track detached background processes
                        try:
                            self._maybe_record_background_job(fname, fargs, res)
                        except Exception:
                            pass
                        res_min = self._minimize_tool_result(fname, res)
                        res_str = json.dumps(res_min)
                        emit({"type": "status", "status": "tool_done", "tool_name": fname, "turn": turns})
                    except Exception as e:
                        res_str = json.dumps({"success": False, "error": str(e)})
                        emit({"type": "status", "status": "tool_error", "tool_name": fname, "turn": turns, "error": str(e)})

                    hist.append({"role": "tool", "tool_call_id": tool_call_id, "content": res_str, "ts": time.time()})
                    emit({"type": "tool", "tool_name": fname, "tool_call_id": tool_call_id, "result": json.loads(res_str) if res_str else {}})

                # Continue: model sees tool outputs next
                continue

            # No tool calls => final assistant message for this call. Always
            # include `reasoning_content` (default "") so DeepSeek V4 thinking
            # mode round-trips correctly on subsequent calls.
            if content:
                assistant_text_msg: Dict[str, Any] = {
                    "role": "assistant",
                    "content": content,
                    "reasoning_content": reasoning_content or "",
                    "ts": time.time(),
                }
                hist.append(assistant_text_msg)
                last_assistant_text = content
                emit({"type": "message", "role": "assistant", "content": content})
            else:
                # Tool-only turn: some models stop without emitting content after tool execution.
                # Synthesize a minimal user-visible message from recent tool results so polling
                # always yields something meaningful.
                def synthesize_from_tools() -> str:
                    try:
                        # Look back for the most recent tool message(s) until the last assistant boundary.
                        tool_msgs = []
                        for m in reversed(hist):
                            if m.get("role") == "tool":
                                tool_msgs.append(m)
                                if len(tool_msgs) >= 3:
                                    break
                            elif m.get("role") == "assistant":
                                break
                        tool_msgs = list(reversed(tool_msgs))
                        if not tool_msgs:
                            return ""
                        parts = []
                        for tm in tool_msgs:
                            raw = tm.get("content") or ""
                            try:
                                data = json.loads(raw)
                            except Exception:
                                data = {"raw": raw}
                            if isinstance(data, dict) and data.get("error"):
                                parts.append(f"Tool error: {data.get('error')}")
                            elif isinstance(data, dict) and data.get("success") is True and "todos" in data:
                                parts.append(f"Todos: {len(data.get('todos') or [])} item(s).")
                            elif isinstance(data, dict) and ("stdout" in data or "stderr" in data):
                                out = (data.get("stdout") or "").strip()
                                err = (data.get("stderr") or "").strip()
                                if out:
                                    parts.append(out)
                                if err:
                                    parts.append(f"[stderr]\n{err}")
                            else:
                                parts.append(json.dumps(data) if isinstance(data, (dict, list)) else str(data))
                        return "\n".join([p for p in parts if p]).strip()
                    except Exception:
                        return ""

                synthesized = synthesize_from_tools()
                last_assistant_text = synthesized
                if synthesized:
                    hist.append({"role": "assistant", "content": synthesized, "ts": time.time()})
                    emit({"type": "message", "role": "assistant", "content": synthesized})

            # Heuristic: if the subagent is asking questions, signal needs_user_input
            questions = []
            if last_assistant_text:
                for line in last_assistant_text.splitlines():
                    line = line.strip()
                    if line.endswith("?") and len(line) > 2:
                        questions.append(line)
                # Also catch a trailing question if it's not line-broken
                if not questions and last_assistant_text.strip().endswith("?"):
                    questions = [last_assistant_text.strip()]

            if questions:
                emit({"type": "status", "status": "needs_user_input", "questions": questions[:10]})
                return {
                    "success": True,
                    "status": "needs_user_input",
                    "subagent_id": subagent_id,
                    "questions": questions[:10],
                    "assistant_message": last_assistant_text,
                    "tool_call_count": tool_call_count,
                    "events": events,
                }

            final_status = "completed" if tool_call_count > 0 else "responded"
            emit({"type": "status", "status": final_status})
            return {
                "success": True,
                "status": final_status,
                "subagent_id": subagent_id,
                "assistant_message": last_assistant_text,
                "tool_call_count": tool_call_count,
                "events": events,
            }

        # Max turns reached without producing a final non-tool message
        return {
            "success": True,
            "status": "needs_user_input",
            "subagent_id": subagent_id,
            "questions": ["Subagent reached max_turns without finishing. Please provide guidance or ask it to summarize progress."],
            "assistant_message": last_assistant_text,
            "tool_call_count": tool_call_count,
            "events": events,
        }

    def _run_subagent_async(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # Back-compat: some prompts call this with {job_description,instructions} instead of {prompt}
        prompt = (args.get("prompt") or "").strip()
        if not prompt:
            jd = (args.get("job_description") or "").strip()
            ins = (args.get("instructions") or "").strip()
            prompt = (jd + ("\n\n" if jd and ins else "") + ins).strip()
            if prompt:
                args = dict(args)
                args["prompt"] = prompt
        if not prompt:
            return {"success": False, "error": "prompt is required"}

        # Always allocate a concrete subagent_id if one isn't provided,
        # so the caller can poll immediately without needing list_subagents.
        subagent_id = (args.get("subagent_id") or "").strip() or str(uuid.uuid4())
        parent_subagent_id = (args.get("parent_subagent_id") or "").strip() or None
        label = (args.get("label") or "").strip() or None
        job_id = str(uuid.uuid4())
        cancel_event = Event()

        # Copy args and inject cancel event (internal)
        job_args = dict(args)
        job_args["subagent_id"] = subagent_id
        job_args["_cancel_event"] = cancel_event

        def worker():
            with self._subagent_lock:
                self.subagent_jobs[job_id]["status"] = "running"
                self.subagent_jobs[job_id]["started_at"] = time.time()
            try:
                result = self._run_subagent(job_args)
                with self._subagent_lock:
                    prior_status = self.subagent_jobs[job_id].get("status")
                    self.subagent_jobs[job_id]["result"] = result
                    self.subagent_jobs[job_id]["completed_at"] = time.time()
                    result_status = result.get("status") if isinstance(result, dict) else None
                    if prior_status == "cancelling" or result_status == "cancelled":
                        self.subagent_jobs[job_id]["status"] = "cancelled"
                        self.subagent_jobs[job_id]["cancelled_at"] = time.time()
                        if isinstance(result, dict) and result_status not in (None, "cancelled"):
                            self.subagent_jobs[job_id]["note"] = f"Cancel requested; worker returned {result_status}"
                    elif isinstance(result, dict) and result.get("success") is False:
                        self.subagent_jobs[job_id]["status"] = "error"
                        self.subagent_jobs[job_id]["error"] = result.get("error") or "Subagent failed"
                    else:
                        self.subagent_jobs[job_id]["status"] = "done"
            except Exception as e:
                with self._subagent_lock:
                    self.subagent_jobs[job_id]["status"] = "error"
                    self.subagent_jobs[job_id]["error"] = str(e)
                    self.subagent_jobs[job_id]["completed_at"] = time.time()

        t = threading.Thread(target=worker, daemon=True)
        with self._subagent_lock:
            self.subagent_jobs[job_id] = {
                "job_id": job_id,
                "subagent_id": subagent_id,
                "parent_subagent_id": parent_subagent_id,
                "label": label,
                "status": "queued",
                "created_at": time.time(),
                "started_at": None,
                "completed_at": None,
                "cancelled_at": None,
                "cancel_event": cancel_event,
                "result": None,
                "error": None,
                "note": None,
            }
        t.start()

        return {"success": True, "job_id": job_id, "subagent_id": subagent_id}

    def _poll_subagent(self, args: Dict[str, Any]) -> Dict[str, Any]:
        subagent_id = (args.get("subagent_id") or "").strip() or None
        since = int(args.get("since_event_index") or 0)
        since = max(0, since)
        job_id = (args.get("job_id") or "").strip() or None

        # Allow polling by job_id alone
        if (not subagent_id) and job_id:
            with self._subagent_lock:
                j = self.subagent_jobs.get(job_id)
                if not j:
                    return {"success": False, "error": "job not found"}
                subagent_id = j.get("subagent_id")
        if not subagent_id:
            return {"success": False, "error": "Provide subagent_id or job_id"}

        sess = self.subagent_sessions.get(subagent_id)
        events = (sess or {}).get("events") or []
        new_events = events[since:]
        latest_event = events[-1] if events else None
        latest_event_age_s = None
        if isinstance(latest_event, dict) and latest_event.get("ts"):
            try:
                latest_event_age_s = max(0.0, time.time() - float(latest_event.get("ts")))
            except Exception:
                latest_event_age_s = None

        # Session-level status (useful when polling by subagent_id without a job_id)
        session_status = None
        try:
            for evt in reversed(events):
                if isinstance(evt, dict) and evt.get("type") == "status" and evt.get("status"):
                    session_status = evt.get("status")
                    break
        except Exception:
            session_status = None

        job_status = None
        job_error = None
        job_result = None
        interrupted_at = None
        job_created_at = None
        job_started_at = None
        job_completed_at = None
        job_cancelled_at = None
        job_note = None
        if job_id:
            with self._subagent_lock:
                j = self.subagent_jobs.get(job_id)
                if j:
                    job_status = j.get("status")
                    job_error = j.get("error")
                    job_result = j.get("result")
                    interrupted_at = j.get("interrupted_at")
                    job_created_at = j.get("created_at")
                    job_started_at = j.get("started_at")
                    job_completed_at = j.get("completed_at")
                    job_cancelled_at = j.get("cancelled_at")
                    job_note = j.get("note")
        else:
            # No explicit job_id; look up the most recent job for this subagent_id
            try:
                with self._subagent_lock:
                    for j in self.subagent_jobs.values():
                        if j.get("subagent_id") == subagent_id and j.get("status") == "interrupted":
                            job_status = job_status or "interrupted"
                            interrupted_at = interrupted_at or j.get("interrupted_at")
                            break
            except Exception:
                pass

        out: Dict[str, Any] = {
            "success": True,
            "subagent_id": subagent_id,
            "job_id": job_id,
            "job_status": job_status,
            "job_error": job_error,
            "job_result": job_result,
            "session_status": session_status,
            "events": new_events,
            "event_count": len(events),
            "latest_event": latest_event,
            "latest_event_age_s": latest_event_age_s,
            "job_age_s": (max(0.0, time.time() - float(job_created_at)) if job_created_at else None),
            "job_started_at": job_started_at,
            "job_completed_at": job_completed_at,
            "job_cancelled_at": job_cancelled_at,
            "job_note": job_note,
            "label": (sess or {}).get("label"),
            "custom_system_prompt": (sess or {}).get("custom_system_prompt"),
            "next_event_index": since + len(new_events),
        }
        if job_status == "interrupted":
            out["interrupted"] = True
            out["interrupted_at"] = interrupted_at
            out["note"] = (
                "This subagent was interrupted by a prior CLI exit/Ctrl+C and is no longer running. "
                "Its conversation, events, and partial outputs are preserved for review. "
                "If you still need the work, re-dispatch via run_subagent or run_subagent_async."
            )
        return out

    def _list_subagents(self, args: Dict[str, Any]) -> Dict[str, Any]:
        with self._subagent_lock:
            jobs = [
                {
                    "job_id": j.get("job_id"),
                    "subagent_id": j.get("subagent_id"),
                    "parent_subagent_id": j.get("parent_subagent_id"),
                    "label": j.get("label"),
                    "status": j.get("status"),
                    "created_at": j.get("created_at"),
                    "interrupted_at": j.get("interrupted_at"),
                    "cancelled_at": j.get("cancelled_at"),
                    "completed_at": j.get("completed_at"),
                    "error": j.get("error"),
                    "note": j.get("note"),
                }
                for j in self.subagent_jobs.values()
            ]

        # Build session list with hierarchy metadata
        subs = []
        for sid, sess in self.subagent_sessions.items():
            ev = sess.get("events") or []
            subs.append({
                "subagent_id": sid,
                "event_count": len(ev),
                "created_at": sess.get("created_at"),
                "parent_subagent_id": sess.get("parent_subagent_id"),
                "label": sess.get("label"),
            })

        # Build tree (forest) by parent_subagent_id (sessions are the nodes; jobs hang off sessions)
        nodes = {s["subagent_id"]: dict(s, jobs=[]) for s in subs}
        for j in jobs:
            sid = j.get("subagent_id")
            if sid in nodes:
                nodes[sid]["jobs"].append(j)

        children = {sid: [] for sid in nodes.keys()}
        roots = []
        for sid, n in nodes.items():
            pid = n.get("parent_subagent_id")
            if pid and pid in nodes and pid != sid:
                children[pid].append(sid)
            else:
                roots.append(sid)

        def _short(s: str) -> str:
            return (s or "")[:8]

        # Human-readable tree text for CLI display (kept small)
        lines: List[str] = []
        def walk(sid: str, prefix: str = "") -> None:
            n = nodes[sid]
            lbl = n.get("label")
            name = f"{lbl} " if lbl else ""
            job_bits = []
            for j in (n.get("jobs") or []):
                st = j.get("status") or "unknown"
                job_bits.append(f"{_short(j.get('job_id') or '')}:{st}")
            jobs_txt = f"  [jobs: {', '.join(job_bits)}]" if job_bits else ""
            lines.append(f"{prefix}- {name}{_short(sid)}{jobs_txt}")
            for cid in children.get(sid, []):
                walk(cid, prefix + "  ")

        for r in sorted(roots):
            walk(r, "")

        hierarchy = {
            "roots": sorted(roots),
            "children": children,
            "nodes": nodes,
            "tree_text": "\n".join(lines).strip(),
        }

        return {"success": True, "subagents": subs, "jobs": jobs, "hierarchy": hierarchy}

    def _cancel_subagent_job(self, args: Dict[str, Any]) -> Dict[str, Any]:
        job_id = (args.get("job_id") or "").strip()
        if not job_id:
            return {"success": False, "error": "job_id is required"}
        with self._subagent_lock:
            j = self.subagent_jobs.get(job_id)
            if not j:
                return {"success": False, "error": "job not found"}
            ev = j.get("cancel_event")
            if ev:
                ev.set()
            j["status"] = "cancelling"
        return {"success": True, "job_id": job_id, "status": "cancelling"}

    def _replay_pending_tool_calls(self) -> bool:
        """Detect and repair dangling tool calls from an interrupted turn.
        Returns True if any missing tool calls were closed out."""
        hist = self.conversation_history
        if not hist:
            return False
        # Find the last assistant with tool_calls
        last_idx = None
        for i in range(len(hist) - 1, -1, -1):
            m = hist[i]
            if m.get("role") == "assistant" and m.get("tool_calls"):
                last_idx = i
                break
        if last_idx is None:
            return False
        tool_calls = hist[last_idx]["tool_calls"]
        # Count following tool messages that reference those ids
        following = hist[last_idx + 1 :]
        responded_ids = set()
        for m in following:
            if m.get("role") == "tool" and m.get("tool_call_id"):
                responded_ids.add(m["tool_call_id"])
        missing = [tc for tc in tool_calls if tc.get("id") not in responded_ids]
        if not missing:
            return False

        # If a tool turn was interrupted, prefer preserving any COMPLETED tool calls (assistant tool_calls + tool results)
        # and discarding only the incomplete tail. This keeps the model context consistent while minimizing lost work.
        try:
            kept_tool_calls = [tc for tc in tool_calls if tc.get("id") in responded_ids]
            if not kept_tool_calls:
                # Nothing completed => discard the dangling tool-call block entirely.
                del hist[last_idx:]
                return True

            # Keep only tool messages that correspond to the kept tool_call ids, preserving order.
            kept_ids = {tc.get("id") for tc in kept_tool_calls if tc.get("id")}
            kept_tool_msgs: List[Dict[str, Any]] = []
            for m in following:
                if m.get("role") == "tool" and m.get("tool_call_id") in kept_ids:
                    kept_tool_msgs.append(m)

            # Rewrite the assistant tool_calls to only include completed calls.
            hist[last_idx]["tool_calls"] = kept_tool_calls

            # Truncate everything after the assistant tool_calls message, then re-append kept tool msgs.
            del hist[last_idx + 1 :]
            hist.extend(kept_tool_msgs)
            return True
        except Exception:
            # Conservative fallback: discard dangling tail.
            try:
                del hist[last_idx:]
            except Exception:
                pass
        return True

    @staticmethod
    def _is_live_stopped(live_ref: Optional[Live]) -> bool:
        """Return True if a Rich Live context is already stopped / not currently rendering.

        Calling .stop()/.update()/.refresh() a second time on a committed Live makes Rich
        emit cursor-up + erase-line escape sequences that can clip the bottom border of
        whatever was last committed to scrollback. Guarding with this check is critical
        for clean Ctrl+C behavior when multiple tiles have been rendered this turn.
        """
        if live_ref is None:
            return True
        try:
            started = getattr(live_ref, "_started", None)
        except Exception:
            started = None
        return started is False

    def _stop_live_context(self, live_ref: Optional[Live], clear: bool = True, pause: float = 0.02) -> None:
        """
        Safely stop and exit a Rich Live context without leaving stray UI artifacts.
        Optionally clears the content before stopping to avoid residual borders.
        No-op if the Live has already been stopped (prevents double-cleanup artifacts).
        """
        if not live_ref:
            return
        if self._is_live_stopped(live_ref):
            # Already committed to scrollback. Just detach it from the tracker; do NOT
            # call .stop()/.update() again or Rich will emit terminal escapes that
            # corrupt the already-rendered content.
            self._untrack_live_ref(live_ref)
            return
        try:
            if clear:
                try:
                    live_ref.update("")
                except Exception:
                    pass
            live_ref.stop()
            live_ref.__exit__(None, None, None)
            self._untrack_live_ref(live_ref)
            if pause and pause > 0:
                time.sleep(pause)
            sys.stdout.flush()
        except Exception:
            pass

    def _delete_live_tile(self, live_ref: Optional[Live], pause: float = 0.02) -> None:
        """Aggressively remove a Live-rendered tile (used on Ctrl+C/cancel to avoid leftover borders).
        No-op if the Live has already been stopped."""
        if not live_ref:
            return
        if self._is_live_stopped(live_ref):
            # The Live already committed its final render to scrollback. Further
            # update/stop calls would just re-emit cursor-up/erase-line sequences and
            # eat the bottom border of whatever is above.
            self._untrack_live_ref(live_ref)
            return
        try:
            # Prefer transient-style cleanup so Rich clears the previous render region.
            try:
                setattr(live_ref, "transient", True)
            except Exception:
                pass
            try:
                live_ref.update(Text(""), refresh=True)
            except Exception:
                try:
                    live_ref.update("", refresh=True)
                except Exception:
                    pass
            try:
                live_ref.refresh()
            except Exception:
                pass
            try:
                live_ref.stop()
            except Exception:
                pass
            try:
                live_ref.__exit__(None, None, None)
            except Exception:
                pass
            self._untrack_live_ref(live_ref)
            if pause and pause > 0:
                time.sleep(pause)
        except Exception:
            pass

    def _track_live_ref(self, live_ref: Optional[Live]) -> None:
        if not live_ref:
            return
        try:
            refs = getattr(self, "_tracked_live_refs", None)
            if not isinstance(refs, list):
                self._tracked_live_refs = []
                refs = self._tracked_live_refs
            if live_ref not in refs:
                refs.append(live_ref)
        except Exception:
            pass

    def _untrack_live_ref(self, live_ref: Optional[Live]) -> None:
        if not live_ref:
            return
        try:
            refs = getattr(self, "_tracked_live_refs", None)
            if isinstance(refs, list) and live_ref in refs:
                refs.remove(live_ref)
        except Exception:
            pass

    def _clear_tracked_live_refs(self) -> None:
        try:
            refs = list(getattr(self, "_tracked_live_refs", []) or [])
            # Only attempt to tear down Lives that are still actively rendering; stopped
            # Lives are simply dropped from the tracker. This prevents double-stop artifacts
            # (Rich cursor-up + erase-line sequences clipping previously-committed tiles).
            for lv in refs:
                try:
                    if self._is_live_stopped(lv):
                        continue
                    self._delete_live_tile(lv, pause=0.0)
                except Exception:
                    pass
            self._tracked_live_refs = []
        except Exception:
            pass

    def _print_interrupt_notice(self) -> None:
        """Print the Ctrl+C interruption notice at most once per short window.
        Multiple layers (stream loop, run_conversation, main) can all catch KeyboardInterrupt;
        this prevents duplicate banners."""
        try:
            now = time.time()
            if now - getattr(self, "_last_interrupt_notice_ts", 0.0) < 0.75:
                return
            self._last_interrupt_notice_ts = now
            try:
                self._clear_tracked_live_refs()
            except Exception:
                pass
            # Ensure no Live context is still active when printing the interrupt banner.
            # Printing into an active Live region is a common cause of "glitchy" leftover borders.
            try:
                self._cleanup_stray_live_contexts()
            except Exception:
                pass
            # Start from a fresh line boundary before printing the banner.
            try:
                sys.stdout.write("\n")
                sys.stdout.flush()
            except Exception:
                pass
            console.print("[yellow]⚠️  Generation interrupted by user[/yellow]")
        except Exception:
            pass

    def _suppress_ctrl_c_echo(self):
        """
        Context manager that disables ECHOCTL on the controlling TTY so a
        Ctrl+C keystroke does NOT paint a literal '^C' into the output buffer.
        Without this, when the user hits Ctrl+C while a Rich Live region is
        repainting, the kernel-echoed '^C' lands at the current cursor
        position and ends up *inside* the next rendered tile's top border.
        Restores the original termios attrs on exit. No-op on non-Unix or
        non-TTY stdin.
        """
        class _NullCtx:
            def __enter__(self_inner):
                return None

            def __exit__(self_inner, *exc):
                return False

        try:
            import termios  # noqa: F401
        except Exception:
            return _NullCtx()

        try:
            stdin = sys.stdin
            if not (stdin and hasattr(stdin, "fileno") and stdin.isatty()):
                return _NullCtx()
            fd = stdin.fileno()
        except Exception:
            return _NullCtx()

        class _SuppressCtx:
            def __init__(self_inner, fd_: int) -> None:
                self_inner.fd = fd_
                self_inner._old = None

            def __enter__(self_inner):
                try:
                    import termios as _tm
                    self_inner._old = _tm.tcgetattr(self_inner.fd)
                    new = list(self_inner._old)
                    # lflag is index 3; clear ECHOCTL so Ctrl+C / Ctrl+\ etc.
                    # are not echoed as visible '^C' / '^\\' glyphs.
                    new[3] = new[3] & ~_tm.ECHOCTL
                    _tm.tcsetattr(self_inner.fd, _tm.TCSANOW, new)
                except Exception:
                    self_inner._old = None
                return self_inner

            def __exit__(self_inner, *exc):
                if self_inner._old is None:
                    return False
                try:
                    import termios as _tm
                    _tm.tcsetattr(self_inner.fd, _tm.TCSANOW, self_inner._old)
                except Exception:
                    pass
                return False

        return _SuppressCtx(fd)

    def _scrub_ctrl_c_echo(self) -> None:
        """
        Best-effort fallback: wipe the current line in case a literal '^C'
        glyph already landed there (e.g. ECHOCTL was on, or we're on a
        platform where the suppression context didn't take effect).
        Safe to call between Live frames — only touches the current row.
        """
        try:
            sys.stdout.write("\r\033[2K")
            sys.stdout.flush()
        except Exception:
            pass

    def _finalize_live_in_place(self, live_ref: Optional[Live]) -> None:
        """
        Stop a Rich Live context while PRESERVING its currently rendered frame
        in scrollback. This is the safe Ctrl+C handler for in-flight tiles
        (reasoning panel, "Preparing ..." tile, etc): instead of trying to
        erase a partially rendered region — which Rich's transient cleanup
        often gets wrong, leaving an orphan top border — we just commit
        whatever the user already saw as a finished tile.

        No-op if the Live has already been stopped.
        """
        if not live_ref:
            return
        if self._is_live_stopped(live_ref):
            self._untrack_live_ref(live_ref)
            return
        try:
            # Force non-transient so .stop() doesn't try to repaint over the
            # rendered frame. The current frame stays committed to scrollback.
            try:
                setattr(live_ref, "transient", False)
            except Exception:
                pass
            # Final paint so any in-flight buffered content is visible.
            try:
                live_ref.refresh()
            except Exception:
                pass
            try:
                live_ref.stop()
            except Exception:
                pass
            try:
                live_ref.__exit__(None, None, None)
            except Exception:
                pass
        finally:
            try:
                self._untrack_live_ref(live_ref)
            except Exception:
                pass
            try:
                # Make sure the cursor is on a fresh line below the committed tile.
                sys.stdout.write("\n")
                sys.stdout.flush()
            except Exception:
                pass

    def _print_interrupt_panel(self, *, reason: str = "Cancelled by user (Ctrl+C)") -> None:
        """
        Render a small '⏸ Interrupted' panel that explicitly marks the cancel
        point in the transcript. Called once per interrupt so the user has a
        clear visual anchor showing the partial output above is not the
        agent's final answer.
        """
        try:
            now = time.time()
            if now - getattr(self, "_last_interrupt_panel_ts", 0.0) < 0.75:
                return
            self._last_interrupt_panel_ts = now
            console.print(Panel(
                Text(reason, style="yellow"),
                border_style="yellow",
                padding=(0, 1),
                title="[yellow]⏸ Interrupted[/yellow]",
            ))
        except Exception:
            try:
                console.print(f"[yellow]⏸ {reason}[/yellow]")
            except Exception:
                pass

    def _save_partial_assistant_on_interrupt(
        self,
        content: Optional[str],
        reasoning_content: Optional[str],
    ) -> bool:
        """
        Persist whatever the model streamed before the user pressed Ctrl+C
        into conversation_history, so the next turn has full context of what
        the user already saw. We deliberately drop any partial tool_calls —
        their JSON arguments are typically truncated and would cause the next
        request to 400. Returns True if a partial message was appended.
        """
        has_content = bool((content or "").strip())
        has_reasoning = bool((reasoning_content or "").strip())
        if not (has_content or has_reasoning):
            return False
        try:
            self.conversation_history.append({
                "role": "assistant",
                "content": content or "",
                "reasoning_content": reasoning_content or "",
                "interrupted": True,
            })
        except Exception:
            return False
        try:
            # Mark the new tail length so the outer turn handler knows not to
            # roll this entry back when it processes the KeyboardInterrupt.
            self._partial_commit_len = len(self.conversation_history)
        except Exception:
            pass
        try:
            self._checkpoint_session(force=True)
        except Exception:
            pass
        return True

    def stream_conversation(self, user_message: str, on_event: Callable[[Dict[str, Any]], None], cancel_event: Any = None) -> None:
        """
        Server-friendly conversation runner that emits structured events and does NOT use Rich Live/printing.

        Events are dictionaries like:
        - {"type": "thinking"}
        - {"type": "assistant_delta", "data": {"kind": "content"|"reasoning", "delta": "...", "full": "..."}}
        - {"type": "tool_call", "data": {"stage": "start"|"args_delta"|"ready", ...}}
        - {"type": "tool_result", "data": {"tool_call_id": "...", "name": "...", "result": {...}}}
        - {"type": "assistant", "data": {"content": "...", "reasoning": "...", "tool_calls": [...]}}
        - {"type": "done"}
        """
        # Basic guard: never let server mode crash due to callback errors
        def _emit(evt: Dict[str, Any]) -> None:
            try:
                on_event(evt)
            except Exception:
                pass

        # Ensure the system prompt is present and stable
        try:
            if not self.conversation_history or self.conversation_history[0].get("role") != "system":
                self.conversation_history.insert(0, {"role": "system", "content": self.system_prompt})
        except Exception:
            # Last resort
            self.conversation_history = [{"role": "system", "content": self.system_prompt}]

        # Repair interrupted tool-calls if any
        try:
            self._replay_pending_tool_calls()
        except Exception:
            pass

        # Append the user message
        self.conversation_history.append({"role": "user", "content": user_message})
        # Durable checkpoint after full message append (crash recovery).
        try:
            self._checkpoint_session(force=True)
        except Exception:
            pass

        # Run multi-step tool loop until we get a final assistant response without tool calls
        _post_compaction_retried = False
        while True:
            # Client cancelled / disconnected
            try:
                if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                    return
            except Exception:
                pass

            _emit({"type": "thinking", "data": {"status": "started"}})

            # Shrink context if needed (subagent path — no Live context, so
            # use the direct call without a progress tile).
            try:
                self._maybe_summarize_conversation()
            except Exception:
                pass

            # Stream model response
            accumulated_content = ""
            accumulated_reasoning = ""
            tool_calls_dict: Dict[int, Dict[str, Any]] = {}

            try:
                # Calculate safe max tokens
                max_tokens = self._calculate_safe_max_tokens(self.conversation_history)
                try:
                    stream_messages = self._sanitize_tool_calls_for_api(self.conversation_history)
                except Exception:
                    stream_messages = self.conversation_history
                stream = self.client.chat(
                    messages=stream_messages,
                    tools=self.tool_registry.get_tool_definitions(),
                    stream=True,
                    max_tokens=max_tokens,
                )

                for chunk in stream:
                    try:
                        if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                            return
                    except Exception:
                        pass
                    if not chunk or not hasattr(chunk, "choices") or len(chunk.choices) == 0:
                        continue
                    delta = chunk.choices[0].delta

                    # Reasoning stream (deepseek-reasoner and other OpenAI-compatible providers)
                    reasoning_delta = None
                    try:
                        if hasattr(delta, "reasoning_content") and getattr(delta, "reasoning_content", None):
                            reasoning_delta = getattr(delta, "reasoning_content", None)
                        elif hasattr(delta, "reasoning") and getattr(delta, "reasoning", None):
                            reasoning_delta = getattr(delta, "reasoning", None)
                        else:
                            extra = getattr(delta, "__pydantic_extra__", None) or getattr(delta, "model_extra", None)
                            if isinstance(extra, dict):
                                reasoning_delta = extra.get("reasoning_content") or extra.get("reasoning") or extra.get("thinking")
                    except Exception:
                        reasoning_delta = None

                    if reasoning_delta:
                        accumulated_reasoning += str(reasoning_delta)
                        _emit({
                            "type": "assistant_delta",
                            "data": {"kind": "reasoning", "delta": str(reasoning_delta), "full": accumulated_reasoning},
                        })

                    # Content stream
                    if getattr(delta, "content", None):
                        accumulated_content += delta.content
                        _emit({
                            "type": "assistant_delta",
                            "data": {"kind": "content", "delta": delta.content, "full": accumulated_content},
                        })

                    # Tool calls stream
                    if getattr(delta, "tool_calls", None):
                        for tc in delta.tool_calls:
                            try:
                                idx = tc.index
                            except Exception:
                                idx = 0
                            if idx not in tool_calls_dict:
                                tool_calls_dict[idx] = {"id": "", "type": "function", "function": {"name": "", "arguments": ""}}

                            # id
                            if getattr(tc, "id", None):
                                tool_calls_dict[idx]["id"] = tc.id

                            # function name / args
                            fn = getattr(tc, "function", None)
                            if fn:
                                fname = getattr(fn, "name", None)
                                if fname:
                                    first_name = tool_calls_dict[idx]["function"]["name"]
                                    tool_calls_dict[idx]["function"]["name"] = fname
                                    if not first_name:
                                        _emit({
                                            "type": "tool_call",
                                            "data": {"stage": "start", "index": idx, "tool_call_id": tool_calls_dict[idx].get("id", ""), "name": fname},
                                        })
                                fargs = getattr(fn, "arguments", None)
                                if fargs:
                                    tool_calls_dict[idx]["function"]["arguments"] += fargs
                                    # Don't spam enormous payloads; send a small preview
                                    preview = tool_calls_dict[idx]["function"]["arguments"]
                                    if isinstance(preview, str) and len(preview) > 800:
                                        preview = preview[:500] + "…"
                                    _emit({
                                        "type": "tool_call",
                                        "data": {
                                            "stage": "args_delta",
                                            "index": idx,
                                            "tool_call_id": tool_calls_dict[idx].get("id", ""),
                                            "name": tool_calls_dict[idx]["function"].get("name", ""),
                                            "arguments_preview": preview,
                                        },
                                    })

                    # If the model signaled completion, stop streaming
                    try:
                        fr = getattr(chunk.choices[0], "finish_reason", None)
                        if fr:
                            break
                    except Exception:
                        pass

            finally:
                try:
                    close_fn = getattr(stream, "close", None)
                    if callable(close_fn):
                        close_fn()
                except Exception:
                    pass

            # Build finalized tool_calls list
            tool_calls: List[Dict[str, Any]] = []
            if tool_calls_dict:
                for idx in sorted(tool_calls_dict.keys()):
                    tool_calls.append(tool_calls_dict[idx])

            # Record assistant message (even if tool calls)
            assistant_msg: Dict[str, Any] = {"role": "assistant", "content": accumulated_content or "", "ts": time.time()}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            if accumulated_reasoning:
                assistant_msg["reasoning_content"] = accumulated_reasoning
            self.conversation_history.append(assistant_msg)
            # Durable checkpoint after full message append (crash recovery).
            try:
                self._checkpoint_session(force=True)
            except Exception:
                pass

            _emit({
                "type": "assistant",
                "data": {
                    "content": accumulated_content or "",
                    "reasoning": accumulated_reasoning or None,
                    "tool_calls": tool_calls or None,
                },
            })

            # If there are no tool calls, this turn is complete
            if not tool_calls:
                # POST-COMPACTION STALL GUARD: if the conversation was just compacted
                # and the model replied with text but no tool_calls, retry once with a
                # stronger directive to force a tool call.
                if (self._is_post_compaction_turn()
                        and not _post_compaction_retried):
                    _post_compaction_retried = True
                    retry_msg = (
                        "[SYSTEM AUTO-INJECTED — the user did NOT type this]\n"
                        "You just responded with text but NO tool call. "
                        "The conversation was just compacted — you are mid-task. "
                        "Re-read the compacted context above and call the tool you need next. "
                        "Do NOT summarize. Call a tool NOW.\n"
                    )
                    self.conversation_history.append({
                        "role": "user",
                        "content": retry_msg,
                        "meta": {"auto_injected": True, "kind": "post_compaction_retry"},
                    })
                    _emit({"type": "status", "status": "post_compaction_retry", "message": "Stall detected — retrying with stronger directive"})
                    continue

                _emit({"type": "done", "data": {"conversation_length": len(self.conversation_history)}})
                return

            # Execute tools, append tool messages, and loop back to the model
            for tc in tool_calls:
                try:
                    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
                        return
                except Exception:
                    pass

                tool_call_id = tc.get("id", "")
                fn = (tc.get("function") or {})
                fname = fn.get("name", "")
                args_text = fn.get("arguments", "") or "{}"

                # Parse args
                fargs: Dict[str, Any] = {}
                try:
                    cleaned = args_text.strip()
                    if cleaned.startswith("```"):
                        fence_end = cleaned.find("\n")
                        if fence_end != -1:
                            cleaned = cleaned[fence_end + 1 :]
                            if cleaned.endswith("```"):
                                cleaned = cleaned[:-3]
                            cleaned = cleaned.strip()
                    fargs = json.loads(cleaned) if cleaned else {}
                except Exception as e:
                    result = {"success": False, "error": f"Failed to parse tool args for {fname}: {e}"}
                    self.conversation_history.append({"role": "tool", "tool_call_id": tool_call_id, "content": json.dumps(result)})
                    _emit({"type": "tool_result", "data": {"tool_call_id": tool_call_id, "name": fname, "result": result}})
                    continue

                # CRITICAL: normalize paths for execution in server streaming mode too.
                # Without this, run_command defaults to the process cwd (repo root) instead of session_cwd.
                try:
                    fargs = self._normalize_paths_for_execution(fargs, fname)
                except Exception:
                    pass

                # Execute tool
                try:
                    if fname == "manage_todos":
                        res = self.tool_registry.execute_tool(fname, fargs, self.todo_manager)
                    elif fname == "run_subagent":
                        res = self.tool_registry.execute_tool(fname, fargs, self._run_subagent)
                    elif fname == "run_subagent_async":
                        res = self.tool_registry.execute_tool(fname, fargs, self._run_subagent_async)
                    elif fname == "poll_subagent":
                        res = self.tool_registry.execute_tool(fname, fargs, self._poll_subagent)
                    elif fname == "list_subagents":
                        res = self.tool_registry.execute_tool(fname, fargs, self._list_subagents)
                    elif fname == "cancel_subagent_job":
                        res = self.tool_registry.execute_tool(fname, fargs, self._cancel_subagent_job)
                    else:
                        res = self.tool_registry.execute_tool(fname, fargs, cancel_event=cancel_event)

                    # Track detached background processes (CLI parity; safe in server mode too)
                    try:
                        self._maybe_record_background_job(fname, fargs, res)
                    except Exception:
                        pass

                    minimized = self._minimize_tool_result(fname, res)
                    result_str = json.dumps(minimized)
                except Exception as e:
                    minimized = {"success": False, "error": str(e)}
                    result_str = json.dumps(minimized)

                self.conversation_history.append({"role": "tool", "tool_call_id": tool_call_id, "content": result_str})
                _emit({"type": "tool_result", "data": {"tool_call_id": tool_call_id, "name": fname, "result": minimized}})

    def run_conversation(self, user_message: str, thinking_live: Optional[Live] = None, auto_injected: bool = False):
        """Run a conversation loop with function calling.

        auto_injected: True when this user_message came from the autopilot loop rather than
        the human. We mark the appended history entry with meta so later compaction can
        distinguish real user goals from autopilot heartbeats and preserve the human's intent.
        """
        
        # Show thinking spinner immediately, before any processing
        thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
        spinner_live = thinking_live
        if spinner_live is not None:
            try:
                spinner_live.update(thinking_panel)
            except Exception:
                # Provided Live may have been stopped/invalid; fall back to a fresh one
                spinner_live = None
        
        if spinner_live is None:
            console.print()  # Add spacing
            # Use screen=False to avoid switching to the alternate screen buffer (which clears the terminal / jumps to top).
            spinner_live = Live(thinking_panel, console=console, refresh_per_second=10, screen=False)
            spinner_live.__enter__()
            self._track_live_ref(spinner_live)
        
        # Normalize back to thinking_live for the rest of the method
        thinking_live = spinner_live
        
        # Ensure spinner is visible immediately (whether newly created or passed in)
        # Render a few frames and flush to overcome terminal buffering
        if thinking_live:
            for _ in range(3):
                try:
                    thinking_live.update(thinking_panel)
                except Exception:
                    break
                sys.stdout.flush()
                sys.stderr.flush()
                time.sleep(0.03)  # Give Live context enough time to render and ensure spinner is visible
            # Keep it on-screen briefly so it is visible even for fast responses
            time.sleep(0.12)
        else:
            sys.stdout.flush()
            sys.stderr.flush()
            time.sleep(0.03)
        
        # Repair conversation history if needed (e.g. from interrupted session)
        # MUST be done before adding new messages to ensure tool sequence is valid
        repaired_pending = self._replay_pending_tool_calls()
        if repaired_pending:
            console.print("[yellow]Resumed previous interrupted turn: pending tool calls were auto-closed. Please restate your request.[/yellow]")
        
        # Add system prompt if this is the first message or if we just cleared history
        if not self.conversation_history or len(self.conversation_history) == 0 or self.conversation_history[0].get("role") != "system":
            self.conversation_history.insert(0, {
                "role": "system",
                "content": self.system_prompt
            })
        
        # Add user message to history. Tag auto-injected autopilot prompts so compaction
        # can filter them out when building "last user messages" for the resume prompt,
        # preserving the real human goal even after many autopilot turns.
        user_entry: Dict[str, Any] = {
            "role": "user",
            "content": user_message,
            "ts": time.time(),
        }
        if auto_injected:
            user_entry["meta"] = {"auto_injected": True, "source": "autopilot"}
        self.conversation_history.append(user_entry)
        # Durable checkpoint after full message append (crash recovery).
        try:
            self._checkpoint_session(force=True)
        except Exception:
            pass
        
        # Ensure spinner is visible before potentially blocking operations
        if thinking_live:
            # Refresh the spinner to ensure it's visible
            thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
            thinking_live.update(thinking_panel)
            sys.stdout.flush()
        
        # Before sending to model, shrink history if needed
        self._maybe_summarize_with_tile(thinking_live=thinking_live)

        # If this turn is interrupted (during streaming or tool execution), we roll back to the LAST COMMITTED checkpoint.
        # We advance this checkpoint after each fully completed tool result (and at the end of the assistant response),
        # so Ctrl+C only discards the currently in-flight streaming/tool tile, not earlier completed steps.
        turn_start_checkpoint_len = len(self.conversation_history)
        commit_checkpoint_len = turn_start_checkpoint_len
        # Accumulate exact usage tokens if the billing relay provides them.
        actual_tokens_turn = 0
        
        try:
            # Store the initial thinking_live if provided (from main loop)
            initial_thinking_live = thinking_live
            
            _post_compaction_retried = False
            while True:
                # CRITICAL: Clean up any existing thinking_live from previous iteration before creating new one
                # This prevents multiple thinking tiles from being visible at once
                if 'current_thinking_live' in locals() and current_thinking_live:
                    try:
                        current_thinking_live.update("")
                        sys.stdout.flush()
                        time.sleep(0.02)
                        current_thinking_live.stop()
                        current_thinking_live.__exit__(None, None, None)
                        current_thinking_live = None
                    except Exception:
                        pass
                
                # Use provided thinking_live if available, otherwise create one
                # Show thinking spinner immediately, before API call
                # BUT: Only create thinking Live if we're actually about to make an API call
                # Don't create it immediately after tool execution - wait a moment for tool tiles to finish rendering
                if thinking_live is None:
                    # CRITICAL: Wait longer to ensure any tool tiles from previous iteration are fully rendered/stopped
                    # This prevents thinking spinner from appearing while tool tiles are still visible
                    # The delay here works with the delay after tool execution to ensure clean transition
                    time.sleep(0.15)  # Longer delay to ensure tool tiles are completely gone
                    sys.stdout.flush()
                    console.print()  # Add spacing
                    thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                    thinking_live = Live(thinking_panel, console=console, refresh_per_second=20, screen=False)  # Higher refresh rate
                    thinking_live.__enter__()
                    self._track_live_ref(thinking_live)
                    # Ensure spinner is visible immediately - flush multiple times for reliability
                    sys.stdout.flush()
                    time.sleep(0.1)  # Longer delay to ensure rendering
                    sys.stdout.flush()  # Flush again to ensure visibility
                    # Force an update to ensure spinner is rendered
                    thinking_live.update(thinking_panel)
                    sys.stdout.flush()
                    # CRITICAL: Brief loop to force multiple renders to overcome buffering
                    for _ in range(3):
                        time.sleep(0.02)
                        thinking_live.update(thinking_panel)
                        sys.stdout.flush()
                
                # Use thinking_live for this iteration, then clear for next iteration
                current_thinking_live = thinking_live
                thinking_live = None  # Clear for next iteration
                
                # Ensure thinking panel is visible before starting API call
                if current_thinking_live:
                    try:
                        target_renderable = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                        target_renderable_2 = target_renderable
                        if live_manager:
                            live_manager.update(target_renderable)
                            time.sleep(0.05)
                            live_manager.update(target_renderable_2)
                        else:
                            current_thinking_live.update(target_renderable)
                            sys.stdout.flush()
                            time.sleep(0.05)  # Brief pause to ensure render
                            current_thinking_live.update(target_renderable_2)
                        sys.stdout.flush()
                    except Exception:
                        pass  # Ignore errors if Live context is already closed
                
                # Initialize return variables before try block to avoid "referenced before assignment" errors
                content = None
                tool_calls = None
                prepare_tiles_info: Dict[int, Any] = {}
                streaming_live_map: Dict[str, Any] = {}
                thinking_stopped_early = False
                
                tool_call_live_map: Dict[str, Any] = {}  # Will be populated during streaming (for write_file) and after main Live exits (for others)
                streaming_interrupted = False
                try:
                    # Get streaming response from DeepSeek
                    # tool_call_live_map may already contain write_file Live contexts created during streaming
                    try:
                        content, tool_calls, prepare_tiles_info, streaming_live_map, thinking_stopped_early, reasoning_content, content_displayed_via_live, reasoning_displayed_via_live = self._handle_streaming_response(thinking_live=current_thinking_live)
                        try:
                            tt = getattr(self, "_last_stream_total_tokens", None)
                            if tt is not None:
                                actual_tokens_turn += int(tt)
                        except Exception:
                            pass
                    except KeyboardInterrupt:
                        # Handle interrupt during streaming setup or execution that
                        # wasn't caught inside _handle_streaming_response.
                        # FINALIZE the thinking tile in place instead of deleting it,
                        # so the user keeps whatever they already saw rendered as a
                        # finished tile (no orphan top borders).
                        streaming_interrupted = True
                        if current_thinking_live:
                            try:
                                self._finalize_live_in_place(current_thinking_live)
                            except Exception:
                                pass
                            current_thinking_live = None
                        # Re-raise to break the loop or be handled by outer loop
                        raise

                    # Merge streaming Live contexts (write_file) into main map
                    tool_call_live_map.update(streaming_live_map)
                finally:
                    # Ensure thinking Live context is cleaned up once before preparing any tiles
                    if current_thinking_live:
                        try:
                            if streaming_interrupted:
                                # Already finalized in place by the KeyboardInterrupt
                                # handler above — do nothing here so we don't repaint
                                # over the committed partial frame.
                                pass
                            elif reasoning_displayed_via_live or content_displayed_via_live:
                                try:
                                    setattr(current_thinking_live, "transient", False)
                                except Exception:
                                    pass
                            else:
                                # Avoid clearing the tile if it contains the reasoning panel we want to keep visible.
                                current_thinking_live.update("")
                                sys.stdout.flush()
                                time.sleep(0.02)
                        except Exception:
                            pass
                        if not streaming_interrupted:
                            try:
                                current_thinking_live.stop()
                            except Exception:
                                pass
                            try:
                                current_thinking_live.__exit__(None, None, None)
                            except Exception:
                                pass
                        thinking_stopped_early = True
                        # Brief pause to ensure spinner is fully gone before new tiles
                        time.sleep(0.05)
                    
                    # Immediately after main Live exits, create Live contexts for prepare tiles that don't have them yet
                    # write_file tiles are already created during streaming, so skip those
                    if tool_calls and prepare_tiles_info is not None:
                        # Match tool calls with prepare_tiles_info by function name
                        for tool_call in tool_calls:
                            tool_call_id = tool_call.get("id", "")
                            if tool_call_id and tool_call_id not in tool_call_live_map:
                                function_name = tool_call["function"]["name"]
                                # If we already created a tile during streaming (idx-based), reuse it.
                                existing_live_info = None
                                for live_info in tool_call_live_map.values():
                                    if live_info.get("function_name") == function_name and live_info.get("live"):
                                        existing_live_info = live_info
                                        break
                                if existing_live_info:
                                    tool_call_live_map[tool_call_id] = existing_live_info
                                    continue
                                prep_text = f"[dim]Preparing {function_name}...[/dim]"
                                # Check if we have more specific text from prepare_tiles_info
                                for prep_idx, prep_info in prepare_tiles_info.items():
                                    if prep_info.get("function_name") == function_name:
                                        prep_text = prep_info.get("text", prep_text)
                                        break
                                
                                # CRITICAL: Stop thinking spinner before creating new tile
                                if current_thinking_live:
                                    # If reasoning/content was shown in this Live, preserve it on screen.
                                    if reasoning_displayed_via_live or content_displayed_via_live:
                                        try:
                                            setattr(current_thinking_live, "transient", False)
                                        except Exception:
                                            pass
                                        self._stop_live_context(current_thinking_live, clear=False)
                                    else:
                                        # Here we want the spinner area cleared so it doesn't visually collide with tool tiles.
                                        self._stop_live_context(current_thinking_live, clear=True)
                                    current_thinking_live = None
                                
                                prep_panel = Panel(Spinner("dots", text=prep_text), title=f"[bold blue]🔧 {function_name}[/bold blue]", border_style="blue", padding=(0, 1))
                                prep_live = Live(prep_panel, console=console, refresh_per_second=10, screen=False)
                                prep_live.start()
                                self._track_live_ref(prep_live)
                                tool_call_live_map[tool_call_id] = {
                                    "live": prep_live,
                                    "text": prep_text,
                                    "function_name": function_name
                                }
                    
                    # For write_file and manage_todos tiles created during streaming, they're already visible and running
                    # No need to refresh them - they persist independently of the main Live context
                    # The main Live context exiting should not affect them since they're separate Live contexts
                    pass  # write_file and manage_todos Live contexts are independent and will persist seamlessly
                
                # Display reasoning when available (avoid duplicating Live-rendered reasoning).
                if reasoning_content and reasoning_content.strip() and (not reasoning_displayed_via_live) and (not getattr(self.config, "ui_reasoning_only", False)):
                    console.print()  # Add spacing
                    console.print("[dim]💭 Reasoning:[/dim]")
                    console.print(Panel(Markdown(reasoning_content), border_style="dim", padding=(1, 1)))
                
                # Always display the main agent response (text copy) so it remains visible even if Live was used.
                # If content is empty but reasoning streamed, fall back to reasoning; else "Done."
                display_content = content
                if (not display_content or not display_content.strip()):
                    if reasoning_content and reasoning_content.strip():
                        display_content = reasoning_content
                    elif not content_displayed_via_live and not reasoning_displayed_via_live:
                        display_content = "Done."
                # Reasoning-only UI mode: historically we suppressed printing the final assistant response when
                # reasoning was present to avoid redundancy. This caused "it stopped" moments where the model
                # announced a summary in reasoning, but the actual summary (final content) never printed.
                #
                # New behavior: only suppress if the model produced NO final content (content empty). If there
                # is final content, always print it.
                ui_ro = bool(getattr(self.config, "ui_reasoning_only", False))
                if ui_ro and reasoning_content and reasoning_content.strip():
                    if not (content and content.strip()):
                        display_content = None
                # Avoid duplicating the Agent label when content already streamed via Live.
                if content_displayed_via_live:
                    display_content = None
                if display_content and display_content.strip():
                    # Ensure spinner is stopped before printing the final copy
                    if current_thinking_live:
                        # Avoid a visible "blank flash" right before printing final content.
                        # Just stop Live without clearing; the subsequent console.print will advance naturally.
                        self._stop_live_context(current_thinking_live, clear=False)
                        current_thinking_live = None
                    console.print()  # Add spacing
                    console.print("[bold green]Agent:[/bold green]")
                    console.print(Markdown(display_content))
                
                # Check if model wants to call tools
                if tool_calls is not None and len(tool_calls) > 0:
                    # Add assistant message with tool calls to history. DeepSeek V4
                    # thinking mode requires `reasoning_content` to round-trip on
                    # every assistant turn that has tool_calls — even when the model
                    # emitted no reasoning text this turn (e.g. when chaining a tool
                    # call right after a tool result). Always include the field,
                    # defaulting to an empty string, so the next API call doesn't
                    # blow up with "reasoning_content must be passed back to the API".
                    assistant_msg = {
                        "role": "assistant",
                        "content": content or "",
                        "tool_calls": tool_calls,
                        "reasoning_content": reasoning_content or "",
                    }
                    self.conversation_history.append(assistant_msg)
                    # Durable checkpoint after full message append (crash recovery).
                    try:
                        self._checkpoint_session(force=True)
                    except Exception:
                        pass
                    
                    # Immediately start executing tool calls (no delay)
                    # Execute each tool call
                    for tool_call in tool_calls:
                        # Get function name immediately (fast)
                        function_name = tool_call["function"]["name"]
                        tool_call_id = tool_call.get("id", "")
                        
                        # Check if we have a Live context from the preparing tile
                        # For write_file and manage_todos, check both tool_call_id and any idx-based keys as fallback
                        existing_live_info = None
                        if tool_call_id:
                            existing_live_info = tool_call_live_map.get(tool_call_id)
                    # If not found and it's a tool that streams its tile, search by function name as fallback
                    if not existing_live_info and function_name in ("write_file", "modify_file", "manage_todos"):
                        for key, live_info in tool_call_live_map.items():
                            if live_info.get("function_name") == function_name and live_info.get("live"):
                                existing_live_info = live_info
                                # Update the map to use tool_call_id as key for future lookups
                                if tool_call_id:
                                    tool_call_live_map[tool_call_id] = live_info
                                    # Remove old key if different
                                    if key != tool_call_id:
                                        try:
                                            del tool_call_live_map[key]
                                        except Exception:
                                            pass
                                break
                    
                    # Create a single persistent tile; start as Preparing and update in place
                    args_text = tool_call["function"]["arguments"]
                    parsed: dict[str, Any] = {}
                    parse_error: dict[str, Exception] = {}

                    # Check if arguments string is empty or missing - this is a critical error
                    if not args_text or len(args_text.strip()) == 0:
                        parse_error["error"] = ValueError(f"Tool call arguments are empty or missing. This indicates the LLM did not provide arguments for {function_name}.")
                    # Parse args immediately (they're already complete at this point)
                    elif args_text.strip() == "{}":
                        # Empty JSON object - this is also an error for write_file
                        if function_name == "write_file":
                            parse_error["error"] = ValueError(f"write_file arguments are empty JSON object {{}}. File path and content are required.")
                        else:
                            # For other tools, empty {} might be valid, so parse it
                            parsed["value"] = {}
                    else:
                        try:
                            # Clean up JSON if needed (remove code fences)
                            cleaned_args = args_text
                            if cleaned_args.startswith("```"):
                                fence_end = cleaned_args.find("\n")
                                if fence_end != -1:
                                    cleaned_args = cleaned_args[fence_end+1:]
                                    if cleaned_args.endswith("```"):
                                        cleaned_args = cleaned_args[:-3]
                                    # Also remove trailing newlines after closing fence
                                    cleaned_args = cleaned_args.rstrip()
                            
                            # Check for incomplete JSON before parsing - detect unterminated strings
                            # This can happen if the stream was cut off mid-way (API limits, network issues, etc.)
                            # Check if we have an opening brace but potentially incomplete content
                            stripped = cleaned_args.strip()
                            if stripped.startswith('{') and not stripped.endswith('}'):
                                # Might be incomplete - check if we're mid-string
                                # Count unescaped quotes to see if we're in the middle of a string
                                in_string = False
                                escaped = False
                                quote_count = 0
                                for i, char in enumerate(stripped):
                                    if escaped:
                                        escaped = False
                                        continue
                                    if char == '\\':
                                        escaped = True
                                        continue
                                    if char == '"':
                                        in_string = not in_string
                                        quote_count += 1
                                
                                # If we're inside a string at the end, or have odd number of quotes, JSON is incomplete
                                if in_string or (quote_count % 2 != 0):
                                    parse_error["error"] = ValueError(f"Tool call arguments appear to be incomplete (stream was cut off). JSON string is unterminated. This usually happens with very large files (>15KB). Try splitting the file into smaller chunks or check if the API response was truncated. Args length: {len(args_text)} chars.")
                                else:
                                    # Try parsing anyway - might just be missing closing brace
                                    try:
                                        parsed["value"] = json.loads(cleaned_args)
                                    except json.JSONDecodeError as e:
                                        parse_error["error"] = ValueError(f"Failed to parse JSON - stream may have been cut off: {str(e)}. Args length: {len(args_text)} chars. For large files, consider splitting into smaller chunks.")
                            else:
                                # Normal case - try to parse
                                parsed["value"] = json.loads(cleaned_args)
                            
                            # For write_file, validate that content is present and properly set
                            # CORE FIX: Validate early during parsing to catch issues before execution
                            if function_name == "write_file" and "value" in parsed:
                                function_args_check = parsed["value"]
                                
                                # Check if content key exists
                                if "content" not in function_args_check:
                                    parse_error["error"] = ValueError(f"write_file requires 'content' parameter. Received keys: {list(function_args_check.keys())}. Arguments JSON length: {len(args_text)} chars.")
                                # Check if content is None
                                elif function_args_check.get("content") is None:
                                    parse_error["error"] = ValueError("write_file 'content' parameter cannot be None")
                                # Check if content is empty string - this is the CORE ISSUE
                                elif isinstance(function_args_check.get("content"), str) and len(function_args_check.get("content", "")) == 0:
                                    # Empty string content - reject it early with a clear error message
                                    parse_error["error"] = ValueError(f"write_file 'content' parameter is empty string. File path: {function_args_check.get('file_path', 'N/A')}. The content field must contain the actual file content.")
                                # Validate content is actually a string (shouldn't be needed but defensive)
                                elif not isinstance(function_args_check.get("content"), str):
                                    parse_error["error"] = ValueError(f"write_file 'content' parameter must be a string, got {type(function_args_check.get('content'))}")
                        except json.JSONDecodeError as e:
                            # JSON parsing failed - this might indicate malformed or incomplete JSON
                            # This could happen if content was truncated during streaming
                            # Include diagnostic info to help debug
                            args_preview = args_text[:500] if len(args_text) > 500 else args_text
                            args_suffix = args_text[-200:] if len(args_text) > 200 else ""
                            parse_error["error"] = ValueError(f"Failed to parse JSON arguments: {str(e)}\n  Args length: {len(args_text)} chars\n  Preview: {args_preview}...\n  Suffix: ...{args_suffix}")
                        except KeyError as e:
                            # KeyError accessing parsed value - provide better error message
                            parse_error["error"] = ValueError(f"Failed to access parsed arguments: missing key '{e.args[0] if e.args else 'unknown'}'. This may indicate incomplete JSON parsing.")
                        except Exception as e:
                            # Catch any other exceptions during parsing/validation
                            parse_error["error"] = ValueError(f"Unexpected error during argument parsing: {type(e).__name__}: {str(e)}")

                    # Reuse existing Live context if available, otherwise create new one
                    if existing_live_info and existing_live_info.get("live"):
                        # Reuse the Live context that was created during streaming
                        live = existing_live_info["live"]
                        
                        # Check for parse errors BEFORE using function_args
                        if parse_error.get("error") is not None:
                            prep_title = (
                                f"[bold blue]📝 Write File[/bold blue]"
                                if function_name == "write_file"
                                else f"[bold blue]🔧 {escape(str(function_name))}[/bold blue]"
                            )
                            error_panel = Panel(
                                f"[red]✗ Failed to parse tool arguments: {escape(str(parse_error['error']))}",
                                title=prep_title, border_style="red", padding=(0, 1),
                            )
                            live.update(error_panel)
                            result = {"success": False, "error": str(parse_error["error"])}
                            result_str = json.dumps(result)
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result_str
                            })
                            try:
                                existing_live_info["live"].stop()
                            except Exception:
                                pass
                            continue
                        
                        function_args = parsed.get("value", {})
                        exec_started_at = time.time()
                        
                        # Normalize paths before execution (handles duplicate prefixes, absolute paths, etc.)
                        function_args = self._normalize_paths_for_execution(function_args, function_name)
                        
                        # Create display version with relative paths for UI
                        display_args = self._normalize_paths_for_display(function_args, function_name)
                        
                        # For write_file and manage_todos, execute immediately and update directly to result - skip all intermediate states
                        # This ensures seamless transition: Preparing -> Result in one smooth update
                        # No prep_panel update needed - the tile is already showing "Preparing" from streaming
                        # manage_todos (especially create with many todos) benefits from immediate execution like write_file
                        # NOTE: run_subagent can take a while (nested model calls), so we do NOT keep it on the fast path;
                        # we want to show a "Delegating..." / loading state to avoid looking stuck.
                        if function_name in ("write_file", "modify_file", "manage_todos", "run_subagent_async", "poll_subagent", "list_subagents", "cancel_subagent_job"):
                            # For write_file, validate arguments before execution to prevent empty content issues
                            # This is the CORE FIX: reject empty/missing content immediately and return error to LLM
                            if function_name == "write_file":
                                # Check if content parameter exists
                                if "content" not in function_args:
                                    error_msg = f"write_file requires 'content' parameter but it was missing. Received parameters: {list(function_args.keys())}. Please retry with the actual file content."
                                    error_panel = Panel(
                                        f"[red]✗[/red] [cyan]Error:[/cyan] Missing 'content' parameter\n  [dim]Received: {escape(str(list(function_args.keys())))}[/dim]",
                                        title=f"[bold blue]📝 Write File[/bold blue]", border_style="red", padding=(0, 1),
                                    )
                                    live.update(error_panel)
                                    self.conversation_history.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call["id"],
                                        "content": json.dumps({"success": False, "error": error_msg})
                                    })
                                    try:
                                        existing_live_info["live"].stop()
                                    except Exception:
                                        pass
                                    continue
                                
                                content_value = function_args.get("content")
                                # Check if content is None
                                if content_value is None:
                                    error_msg = f"write_file 'content' parameter is None. File path: {function_args.get('file_path', 'N/A')}. Please provide the actual file content as a string."
                                    error_panel = Panel(
                                        f"[red]✗[/red] [cyan]Error:[/cyan] 'content' is None\n  [dim]file_path: {escape(str(function_args.get('file_path', 'N/A')))}[/dim]",
                                        title=f"[bold blue]📝 Write File[/bold blue]", border_style="red", padding=(0, 1),
                                    )
                                    live.update(error_panel)
                                    self.conversation_history.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call["id"],
                                        "content": json.dumps({"success": False, "error": error_msg})
                                    })
                                    try:
                                        existing_live_info["live"].stop()
                                    except Exception:
                                        pass
                                    continue
                                
                                # Check if content is empty string
                                if isinstance(content_value, str) and len(content_value) == 0:
                                    error_msg = f"write_file 'content' parameter is empty string. File path: {function_args.get('file_path', 'N/A')}. Please provide the actual file content. If you intended to create an empty file, use a single space or newline."
                                    error_panel = Panel(
                                        f"[red]✗[/red] [cyan]Error:[/cyan] 'content' is empty\n  [dim]file_path: {escape(str(function_args.get('file_path', 'N/A')))}[/dim]\n  [dim]Please provide actual file content[/dim]",
                                        title=f"[bold blue]📝 Write File[/bold blue]", border_style="red", padding=(0, 1),
                                    )
                                    live.update(error_panel)
                                    self.conversation_history.append({
                                        "role": "tool",
                                        "tool_call_id": tool_call["id"],
                                        "content": json.dumps({"success": False, "error": error_msg})
                                    })
                                    try:
                                        existing_live_info["live"].stop()
                                    except Exception:
                                        pass
                                    continue
                            
                            # Execute immediately - both are fast operations
                            # For manage_todos, use todo_manager if needed
                            try:
                                if function_name == "manage_todos":
                                    result = self.tool_registry.execute_tool(function_name, function_args, self.todo_manager)
                                elif function_name == "run_subagent":
                                    result = self.tool_registry.execute_tool(function_name, function_args, self._run_subagent)
                                elif function_name == "run_subagent_async":
                                    result = self.tool_registry.execute_tool(function_name, function_args, self._run_subagent_async)
                                elif function_name == "poll_subagent":
                                    result = self.tool_registry.execute_tool(function_name, function_args, self._poll_subagent)
                                elif function_name == "list_subagents":
                                    result = self.tool_registry.execute_tool(function_name, function_args, self._list_subagents)
                                elif function_name == "cancel_subagent_job":
                                    result = self.tool_registry.execute_tool(function_name, function_args, self._cancel_subagent_job)
                                else:
                                    result = self.tool_registry.execute_tool(function_name, function_args)
                                
                                # Create final panel with result
                                if function_name == "manage_todos":
                                    final_panel = self._create_todos_result_panel(function_args, result)
                                else:
                                    final_panel = self._create_result_panel(function_name, function_args, result)
                                
                                # Update immediately - same Live context, seamless transition from Preparing to Result
                                # No delays, no intermediate states - just smooth text update in the same tile
                                # The tile persists, only the content changes
                                live.update(final_panel)
                                # Minimize result for history
                                minimized = result
                                result_str = json.dumps(minimized)
                                # Add result to history
                                self.conversation_history.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": result_str
                                })
                                # Stop Live context - final panel is displayed
                                try:
                                    existing_live_info["live"].stop()
                                except Exception:
                                    pass
                            except Exception as e:
                                safe_fn = escape(str(function_name))
                                error_panel = Panel(
                                    f"[red]✗[/red] [cyan]Error executing {safe_fn}[/cyan]\n  {escape(str(e))}",
                                    title=f"[bold blue]🔧 {safe_fn}[/bold blue]", border_style="red", padding=(0, 1),
                                )
                                live.update(error_panel)
                                # Add error to history
                                self.conversation_history.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "content": json.dumps({"success": False, "error": str(e)})
                                })
                                try:
                                    existing_live_info["live"].stop()
                                except Exception:
                                    pass
                            # Skip the rest of the tool execution loop
                            continue
                        
                        # For other tools, update prep panel to maintain visibility
                        prep_text = existing_live_info.get("text", f"[dim]Preparing {escape(str(function_name))}...[/dim]")
                        safe_fn = escape(str(existing_live_info.get('function_name', function_name)))
                        prep_panel = Panel(Spinner("dots", text=prep_text), title=f"[bold blue]🔧 {safe_fn}[/bold blue]", border_style="blue", padding=(0, 1))
                        # Update immediately - no delay between prepare and loading states
                        live.update(prep_panel)
                        
                        # Determine loading message based on tool type (for non-write_file tools)
                        if function_name == "run_command":
                            # Ensure a sane default timeout if the model didn't provide one
                            if "timeout" not in function_args:
                                function_args["timeout"] = 30
                            if "timeout_action" not in function_args:
                                function_args["timeout_action"] = "kill"
                            cmd = function_args.get("command", "")
                            display_cmd = cmd if len(cmd) < 50 else cmd[:47] + "..."
                            # Escape: commands may contain `[...]` (grep regex,
                            # array literals, etc.) which Rich would otherwise
                            # parse as console markup.
                            loading_text = f"[cyan]Running:[/cyan] {escape(display_cmd)} [dim](timeout {function_args['timeout']}s)[/dim]"
                            panel_title = "[bold blue]⚙️  Run Command[/bold blue]"
                            panel_style = "blue"
                        elif function_name == "read_file":
                            loading_text = f"[cyan]Reading:[/cyan] {escape(str(display_args.get('file_path', '')))}"
                            panel_title = "[bold blue]📖 Read File[/bold blue]"
                            panel_style = "blue"
                        elif function_name == "list_directory":
                            loading_text = f"[cyan]Listing:[/cyan] {escape(str(display_args.get('directory_path', '')))}"
                            panel_title = "[bold blue]📁 List Directory[/bold blue]"
                            panel_style = "blue"
                        elif function_name == "write_file":
                            loading_text = f"[cyan]Writing:[/cyan] {escape(str(function_args.get('file_path', '')))}"
                            panel_title = "[bold blue]📝 Write File[/bold blue]"
                            panel_style = "blue"
                        elif function_name == "manage_todos":
                            action = function_args.get("action", "")
                            action_verb = {
                                "create": "Creating",
                                "update": "Updating",
                                "list": "Listing",
                                "clear": "Clearing"
                            }.get(action, action.capitalize())
                            loading_text = f"[cyan]{action_verb}:[/cyan] todos"
                            panel_title = "[bold cyan]📋 Manage Todos[/bold cyan]"
                            panel_style = "cyan"
                        elif function_name == "run_subagent":
                            loading_text = "[cyan]Delegating:[/cyan] run_subagent [dim](sync)[/dim]"
                            panel_title = "[bold magenta]🤖 Run Subagent[/bold magenta]"
                            panel_style = "magenta"
                        elif function_name == "web_search":
                            loading_text = f"[cyan]Searching:[/cyan] {escape(str(function_args.get('query', ''))[:50])}"
                            panel_title = f"[bold blue]🔍 web_search[/bold blue]"
                            panel_style = "blue"
                        else:
                            safe_fn = escape(str(function_name))
                            loading_text = f"[cyan]Executing:[/cyan] {safe_fn}"
                            panel_title = f"[bold blue]🔧 {safe_fn}[/bold blue]"
                            panel_style = "blue"
                        
                        # Update from prepare state to loading state immediately (no delay)
                        # This ensures smooth transition without the tile disappearing
                        # Update happens synchronously in the same Live context - no gap possible
                        # For write_file, skip loading state entirely since it's so fast - go straight to result
                        if function_name == "write_file":
                            # For write_file, skip "Writing" state - it's too fast and causes flicker
                            # We'll update directly to result after execution
                            pass  # Don't show loading state for write_file
                        else:
                            # For other tools, show loading state
                            loading_panel = Panel(Spinner("dots", text=loading_text), title=panel_title, border_style=panel_style, padding=(0, 1))
                            live.update(loading_panel)
                    else:
                        # Create new Live context for tools that didn't show preparing tile
                        # For write_file, this should never happen since we create it during streaming
                        # But if it does, use consistent title "📝 Write File"
                        if function_name == "write_file":
                            prep_title = f"[bold blue]📝 Write File[/bold blue]"
                        else:
                            prep_title = f"[bold blue]🔧 {escape(str(function_name))}[/bold blue]"
                        preparing_spinner = Spinner("dots", text=f"[dim]Preparing {escape(str(function_name))}...[/dim]")
                        tile = Panel(preparing_spinner, title=prep_title, border_style="blue", padding=(0, 1))
                        live_ctx = Live(tile, console=console, refresh_per_second=12, screen=False)
                        live_ctx.__enter__()
                        self._track_live_ref(live_ctx)
                        live = live_ctx
                        # Parse args in background so spinner stays animated
                        prepare_started_at = time.time()
                        def _parse_args():
                            try:
                                parsed["value"] = json.loads(args_text)
                            except json.JSONDecodeError as e:
                                parse_error["error"] = ValueError(f"Failed to parse JSON arguments: {str(e)}")
                            except Exception as e:
                                parse_error["error"] = ValueError(f"Unexpected error during argument parsing: {type(e).__name__}: {str(e)}")

                        parse_thread = threading.Thread(target=_parse_args, daemon=True)
                        parse_thread.start()
                        # Ensure preparing spinner is visible for a minimum time
                        MIN_PREPARE_VISIBLE_S = 0.25
                        while parse_thread.is_alive() or (time.time() - prepare_started_at) < MIN_PREPARE_VISIBLE_S:
                            time.sleep(0.05)
                        function_args = parsed.get("value", {})

                    try:
                        if parse_error.get("error") is not None:
                            prep_title = f"[bold blue]🔧 {escape(str(function_name))}[/bold blue]"
                            error_panel = Panel(
                                f"[red]✗ Failed to parse tool arguments: {escape(str(parse_error['error']))}",
                                title=prep_title, border_style="red", padding=(0, 1),
                            )
                            live.update(error_panel)
                            result = {"success": False, "error": str(parse_error["error"])}
                            result_str = json.dumps(result)
                            self.conversation_history.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "content": result_str
                            })
                            # Clean up Live context
                            try:
                                if existing_live_info and existing_live_info.get("live"):
                                    existing_live_info["live"].stop()
                                elif 'live_ctx' in locals():
                                    live_ctx.__exit__(None, None, None)
                            except Exception:
                                pass
                            continue

                        # Determine loading message based on tool type; update the same tile
                        # Set loading_text, panel_title, and panel_style for all tools
                        # Skip if we already set them in the existing_live_info branch
                        # For write_file, skip loading state entirely - it's too fast
                        if not existing_live_info and function_name not in ("write_file", "modify_file"):
                            exec_started_at = time.time()
                            if function_name == "run_command":
                                # Ensure a sane default timeout if the model didn't provide one
                                if "timeout" not in function_args:
                                    function_args["timeout"] = 30
                                if "timeout_action" not in function_args:
                                    function_args["timeout_action"] = "kill"
                                # Default working directory to the session cwd if not provided
                                if not function_args.get("working_directory"):
                                    function_args["working_directory"] = self.session_cwd

                                cmd = function_args.get("command", "")
                                display_cmd = cmd if len(cmd) < 50 else cmd[:47] + "..."
                                loading_text = f"[cyan]Running:[/cyan] {escape(display_cmd)} [dim](timeout {function_args['timeout']}s)[/dim]"
                                panel_title = "[bold blue]⚙️  Run Command[/bold blue]"
                                panel_style = "blue"
                            elif function_name == "read_file":
                                loading_text = f"[cyan]Reading:[/cyan] {escape(str(function_args.get('file_path', '')))}"
                                panel_title = "[bold blue]📖 Read File[/bold blue]"
                                panel_style = "blue"
                            elif function_name == "list_directory":
                                loading_text = f"[cyan]Listing:[/cyan] {escape(str(function_args.get('directory_path', '')))}"
                                panel_title = "[bold blue]📁 List Directory[/bold blue]"
                                panel_style = "blue"
                            elif function_name == "write_file":
                                loading_text = f"[cyan]Writing:[/cyan] {escape(str(function_args.get('file_path', '')))}"
                                panel_title = "[bold blue]📝 Write File[/bold blue]"
                                panel_style = "blue"
                            elif function_name == "manage_todos":
                                action = function_args.get("action", "")
                                action_verb = {
                                    "create": "Creating",
                                    "update": "Updating",
                                    "list": "Listing",
                                    "clear": "Clearing"
                                }.get(action, action.capitalize())
                                loading_text = f"[cyan]{action_verb}:[/cyan] todos"
                                panel_title = "[bold cyan]📋 Manage Todos[/bold cyan]"
                                panel_style = "cyan"
                            elif function_name == "web_search":
                                loading_text = f"[cyan]Searching:[/cyan] {escape(str(function_args.get('query', ''))[:50])}"
                                panel_title = f"[bold blue]🔍 web_search[/bold blue]"
                                panel_style = "blue"
                            else:
                                safe_fn2 = escape(str(function_name))
                                loading_text = f"[cyan]Executing:[/cyan] {safe_fn2}"
                                panel_title = f"[bold blue]🔧 {safe_fn2}[/bold blue]"
                                panel_style = "blue"

                            # Update the same tile to the loading state
                            if live:
                                live.update(Panel(Spinner("dots", text=loading_text), title=panel_title, border_style=panel_style, padding=(0, 1)))

                        # Execute the tool while keeping the same tile alive
                        if function_name == "run_command":
                            live_stdout_stderr = {"stdout": "", "stderr": ""}
                            last_displayed = {"stdout": "", "stderr": ""}
                            
                            def update_output(stdout: str, stderr: str):
                                """Update output state - called from background threads"""
                                live_stdout_stderr["stdout"] = stdout
                                live_stdout_stderr["stderr"] = stderr
                            
                            # Start command execution in background thread
                            result_container = {"result": None}
                            execution_done = threading.Event()
                            cancel_event = threading.Event()  # Event to signal cancellation
                            
                            # Get timeout from function_args to enforce it in polling loop
                            command_timeout = function_args.get("timeout", 30)
                            start_time = time.time()
                            
                            def run_command_thread():
                                try:
                                    result_container["result"] = self.tool_registry.execute_tool(
                                        function_name,
                                        function_args,
                                        live_callback=update_output,
                                        cancel_event=cancel_event
                                    )
                                finally:
                                    execution_done.set()
                            
                            cmd_thread = threading.Thread(target=run_command_thread, daemon=True)
                            cmd_thread.start()
                            
                            # Poll and update display while command runs
                            try:
                                while not execution_done.is_set():
                                    # Check for timeout - enforce it even if command doesn't
                                    elapsed = time.time() - start_time
                                    if elapsed > command_timeout:
                                        # Timeout exceeded - cancel the command
                                        cancel_event.set()
                                        result_container["result"] = {
                                            "success": False,
                                            "error": f"Command timed out after {command_timeout}s",
                                            "stdout": live_stdout_stderr.get("stdout", ""),
                                            "stderr": live_stdout_stderr.get("stderr", "")
                                        }
                                        execution_done.set()
                                        break
                                    
                                    stdout = live_stdout_stderr.get("stdout", "")
                                    stderr = live_stdout_stderr.get("stderr", "")
                                    
                                    if stdout != last_displayed["stdout"] or stderr != last_displayed["stderr"]:
                                        last_displayed["stdout"] = stdout
                                        last_displayed["stderr"] = stderr

                                        # Build the live output renderable as a
                                        # Group of Text nodes so Rich never
                                        # parses the actual stdout/stderr bytes
                                        # as console markup. The previous
                                        # f-string concat ('output_preview +=
                                        # f"\n[yellow][STDERR][/yellow]\n..."')
                                        # crashed whenever the program printed
                                        # regex literals containing `[/...]`.
                                        stdout_tail = stdout[-1500:] if len(stdout) > 1500 else stdout
                                        live_pieces: List[Any] = []
                                        if stdout_tail:
                                            live_pieces.append(Text(stdout_tail))
                                        if stderr:
                                            stderr_tail = stderr[-500:] if len(stderr) > 500 else stderr
                                            if live_pieces:
                                                live_pieces.append(Text(""))
                                            live_pieces.append(Text("[STDERR]", style="bold yellow"))
                                            live_pieces.append(Text(stderr_tail))

                                        if live_pieces:
                                            output_renderable: Any = Group(*live_pieces)
                                            content = Group(
                                                Spinner("dots", text=loading_text),
                                                Text(""),
                                                Panel(output_renderable, title="[dim]Live Output[/dim]", border_style="dim", padding=(0, 1)),
                                            )
                                            live.update(Panel(content, title=panel_title, border_style=panel_style, padding=(0, 1)))
                                        elif stdout or stderr:
                                            content = Group(
                                                Spinner("dots", text=loading_text),
                                                Text(""),
                                                Panel(Text.from_markup("[dim]Waiting for output...[/dim]"), title="[dim]Live Output[/dim]", border_style="dim", padding=(0, 1)),
                                            )
                                            live.update(Panel(content, title=panel_title, border_style=panel_style, padding=(0, 1)))
                                    
                                    # Check if thread is still alive, wait a bit
                                    if cmd_thread.is_alive():
                                        execution_done.wait(timeout=0.1)  # Check every 100ms
                                    else:
                                        break
                            except KeyboardInterrupt:
                                # Interrupt should cancel the tool and roll back the turn (no partial tool tiles/history).
                                cancel_event.set()
                                try:
                                    execution_done.set()
                                except Exception:
                                    pass
                                try:
                                    cmd_thread.join(timeout=0.5)
                                except Exception:
                                    pass
                                raise
                            
                            # Wait for thread to finish (with timeout to prevent hanging)
                            cmd_thread.join(timeout=max(1.0, command_timeout + 1))
                            result = result_container.get("result") or {
                                "success": False,
                                "error": "Command execution thread did not return result"
                            }
                        elif function_name == "manage_todos":
                            try:
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    function_args,
                                    self.todo_manager
                                )
                            except KeyboardInterrupt:
                                raise
                        elif function_name == "run_subagent":
                            try:
                                subagent_progress_lines: List[str] = []

                                def _format_subagent_progress(evt: Dict[str, Any]) -> str:
                                    # NOTE: every interpolated value is escaped — the subagent
                                    # message body in particular can contain `[/...]` (regex
                                    # literals, code snippets) that Rich would otherwise read
                                    # as an unbalanced closing tag.
                                    et = (evt or {}).get("type")
                                    if et == "tool":
                                        tool_name = escape(str((evt or {}).get("tool_name", "tool")))
                                        return f"[cyan]Tool:[/cyan] {tool_name}"
                                    if et == "status":
                                        st = escape(str((evt or {}).get("status", "")))
                                        if st:
                                            return f"[magenta]Status:[/magenta] {st}"
                                    if et == "message":
                                        role = escape(str((evt or {}).get("role", "assistant")))
                                        msg = str((evt or {}).get("content", "")).strip().replace("\n", " ")
                                        if len(msg) > 120:
                                            msg = msg[:117] + "..."
                                        if msg:
                                            return f"[dim]{role}:[/dim] {escape(msg)}"
                                    return ""

                                def _subagent_progress_callback(evt: Dict[str, Any]) -> None:
                                    try:
                                        line = _format_subagent_progress(evt)
                                        if not line:
                                            return
                                        subagent_progress_lines.append(line)
                                        preview = "\n".join(subagent_progress_lines[-6:])
                                        if live:
                                            content = Group(
                                                Spinner("dots", text=loading_text),
                                                Text(""),
                                                Panel(preview or "[dim]Waiting for subagent events...[/dim]", title="[dim]Subagent Progress[/dim]", border_style="dim", padding=(0, 1)),
                                            )
                                            live.update(Panel(content, title=panel_title, border_style=panel_style, padding=(0, 1)))
                                    except Exception:
                                        pass

                                exec_args = dict(function_args)
                                exec_args["_progress_callback"] = _subagent_progress_callback
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    exec_args,
                                    self._run_subagent
                                )
                            except KeyboardInterrupt:
                                raise
                        elif function_name == "run_subagent_async":
                            try:
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    function_args,
                                    self._run_subagent_async
                                )
                            except KeyboardInterrupt:
                                raise
                        elif function_name == "poll_subagent":
                            try:
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    function_args,
                                    self._poll_subagent
                                )
                            except KeyboardInterrupt:
                                raise
                        elif function_name == "list_subagents":
                            try:
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    function_args,
                                    self._list_subagents
                                )
                            except KeyboardInterrupt:
                                raise
                        elif function_name == "cancel_subagent_job":
                            try:
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    function_args,
                                    self._cancel_subagent_job
                                )
                            except KeyboardInterrupt:
                                raise
                        elif function_name == "write_file":
                            # Validate write_file arguments before execution to prevent empty content issues
                            if "content" not in function_args:
                                result = {
                                    "success": False,
                                    "error": f"write_file requires 'content' parameter. Received keys: {list(function_args.keys())}"
                                }
                            elif function_args.get("content") is None:
                                result = {
                                    "success": False,
                                    "error": "write_file 'content' parameter cannot be None"
                                }
                            elif isinstance(function_args.get("content"), str) and len(function_args.get("content", "")) == 0:
                                result = {
                                    "success": False,
                                    "error": "write_file 'content' parameter is empty. Please provide the actual file content."
                                }
                            else:
                                # Content is present and non-empty, proceed with execution
                                try:
                                    result = self.tool_registry.execute_tool(
                                        function_name,
                                        function_args
                                    )
                                except KeyboardInterrupt:
                                    raise
                        else:
                            try:
                                result = self.tool_registry.execute_tool(
                                    function_name,
                                    function_args
                                )
                            except KeyboardInterrupt:
                                raise

                        # Update the same tile to final state - keep it persistent
                        # Note: write_file is handled earlier and skipped with continue, so this is for other tools
                        # For other tools, ensure loading state is visible briefly
                        MIN_LOADING_VISIBLE_S = 0.15
                        elapsed_loading = time.time() - exec_started_at
                        if elapsed_loading < MIN_LOADING_VISIBLE_S:
                            time.sleep(MIN_LOADING_VISIBLE_S - elapsed_loading)
                        
                        # Create final panel BEFORE updating Live context
                        if function_name == "manage_todos":
                            final_panel = self._create_todos_result_panel(function_args, result)
                        else:
                            final_panel = self._create_result_panel(function_name, function_args, result)
                        
                        # Update Live context with result immediately - same tile persists, just text changes
                        live.update(final_panel)
                        
                        # Ensure update is rendered
                        sys.stdout.flush()
                        
                        # Stop the Live context
                        try:
                            if existing_live_info and existing_live_info.get("live"):
                                existing_live_info["live"].stop()
                            elif 'live_ctx' in locals():
                                live_ctx.__exit__(None, None, None)
                        except Exception:
                            pass

                        # Prepare any additional panels to render AFTER the tile finishes
                        extra_stdout = result.get("stdout") if function_name == "run_command" else None
                        extra_stderr = result.get("stderr") if function_name == "run_command" else None

                        # If this was a run_command that changed directory (leading 'cd <dir> &&'), persist new cwd
                        if function_name == "run_command":
                            try:
                                import re
                                cmd = function_args.get("command", "")
                                cd_match = re.match(r"^\s*cd\s+([^&;]+)\s*&&", cmd)
                                if cd_match:
                                    target = cd_match.group(1).strip()
                                    # Resolve against prior session_cwd
                                    if not os.path.isabs(target):
                                        new_dir = os.path.normpath(os.path.join(self.session_cwd, target))
                                    else:
                                        new_dir = os.path.normpath(target)
                                    # Ensure it's a valid directory
                                    if os.path.isdir(new_dir):
                                        self.session_cwd = new_dir
                            except Exception:
                                pass

                        # Minimize payload stored in conversation to avoid context bloat.
                        # Uses a token-budget fraction of the overall context window (see _minimize_tool_result).
                        minimized = self._minimize_tool_result(function_name, result)
                        result_str = json.dumps(minimized)
                    except KeyboardInterrupt:
                        # User interrupted - clean up ALL Live contexts immediately
                        try:
                            # Clean up the current tool's Live context
                            if existing_live_info and existing_live_info.get("live"):
                                self._delete_live_tile(existing_live_info.get("live"), pause=0.02)
                            elif 'live_ctx' in locals():
                                self._delete_live_tile(live_ctx, pause=0.02)
                            elif 'live' in locals() and live:
                                self._delete_live_tile(live, pause=0.02)
                        except Exception:
                            pass
                        
                        # CRITICAL: Clean up ALL remaining tool call Live contexts
                        try:
                            for tool_call_id, live_info in tool_call_live_map.items():
                                if live_info and live_info.get("live"):
                                    try:
                                        self._delete_live_tile(live_info.get("live"), pause=0.01)
                                    except Exception:
                                        pass
                        except Exception:
                            pass

                        # Global safety-net cleanup for any Live contexts that escaped local refs.
                        try:
                            self._hard_cleanup_live_interrupt()
                        except Exception:
                            pass
                        
                        # Clean up thinking Live context if still active
                        try:
                            if 'current_thinking_live' in locals() and current_thinking_live:
                                try:
                                    self._delete_live_tile(current_thinking_live, pause=0.02)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        
                        # Roll back to the last committed checkpoint so we only drop the in-flight tool tile.
                        try:
                            if isinstance(commit_checkpoint_len, int) and commit_checkpoint_len >= 0:
                                self.conversation_history = (self.conversation_history or [])[:commit_checkpoint_len]
                        except Exception:
                            pass
                        try:
                            sys.stdout.write("\n⚠️  Tool execution cancelled. You can enter a new message.\n")
                            sys.stdout.flush()
                        except Exception:
                            pass
                        # Tell the outer Ctrl-C handler to skip its own "Response cancelled"
                        # banner — we've already shown the more specific one here.
                        try:
                            self._cancel_notice_shown = True
                        except Exception:
                            pass
                        # Flush and pause to ensure all Live contexts are cleared
                        try:
                            sys.stdout.flush()
                            sys.stderr.flush()
                            time.sleep(0.1)  # Pause to ensure cleanup completes
                        except Exception:
                            pass
                        # Re-raise so outer handlers return to the input prompt cleanly.
                        raise
                    except Exception as e:
                        result_str = json.dumps({"error": str(e)})
                        console.print(f"[red]✗ Error executing {function_name}: {escape(str(e))}[/red]")
                        # Stop Live context on error too
                        try:
                            if existing_live_info and existing_live_info.get("live"):
                                existing_live_info["live"].stop()
                            elif 'live_ctx' in locals():
                                live_ctx.__exit__(None, None, None)
                        except Exception:
                            pass
                    
                    # Add tool result to history
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "content": result_str
                    })
                    # Record per-tool stats so /wrap has something to show.
                    try:
                        self._record_tool_use(function_name, function_args, result)
                    except Exception:
                        pass
                    # Commit: this tool result is complete and should survive future Ctrl+C interruptions.
                    try:
                        commit_checkpoint_len = len(self.conversation_history)
                    except Exception:
                        pass
                    # Durable checkpoint (crash recovery).
                    try:
                        self._checkpoint_session(force=True)
                    except Exception:
                        pass

                    # Display additional result info for specific tools (AFTER the tile)
                    if function_name == "manage_todos":
                        self.display_todos()
                    elif function_name == "run_command":
                        # IMPORTANT: stdout/stderr is untrusted text. Wrap it in a
                        # plain Text node so Rich does NOT try to parse `[...]`
                        # sequences (regex literals, JSON-with-square-brackets, log
                        # tokens, etc.) as console markup. A previous bug surfaced
                        # as `closing tag '[/...]' doesn't match any open tag`.
                        if extra_stdout is not None and extra_stdout != "":
                            console.print(Panel(
                                Text(str(extra_stdout)),
                                title="[green]Output[/green]",
                                border_style="green", padding=(0, 1),
                            ))

                        if extra_stderr is not None and extra_stderr != "":
                            was_success = result.get("success", False)
                            label = "[dim]stderr[/dim]" if was_success else "[red]Error[/red]"
                            style = "dim" if was_success else "red"
                            console.print(Panel(
                                Text(str(extra_stderr)),
                                title=label,
                                border_style=style, padding=(0, 1),
                            ))

                        error_msg = result.get("error")
                        if error_msg and (not extra_stderr or extra_stderr == ""):
                            console.print(Panel(
                                Text(str(error_msg)),
                                title="[red]Error[/red]",
                                border_style="red", padding=(0, 1),
                            ))

                        note_msg = result.get("note")
                        pid = result.get("pid")
                        if note_msg:
                            # `note` comes from our own tool, but be defensive: pass
                            # the prose as Text and only the small PID suffix as
                            # markup so a future tool tweak can't reintroduce the bug.
                            note_renderable: Any = Text(str(note_msg), style="cyan")
                            if pid:
                                note_renderable = Group(
                                    note_renderable,
                                    Text(f"PID: {pid}", style="dim"),
                                )
                            console.print(Panel(
                                note_renderable,
                                title="[blue]Info[/blue]",
                                border_style="blue", padding=(0, 1),
                            ))
                    
                    # Show thinking animation before next iteration
                    console.print()
                    
                    # Ensure all Live contexts are stopped before continuing
                    # This prevents terminal state issues that can freeze input
                    # Clean up all tool call Live contexts first
                    try:
                        for tool_call_id, live_info in tool_call_live_map.items():
                            if live_info and live_info.get("live"):
                                try:
                                    live_info["live"].stop()
                                    live_info["live"].__exit__(None, None, None)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    
                    # Explicitly clean up any remaining thinking spinners
                    try:
                        if 'current_thinking_live' in locals() and current_thinking_live:
                            try:
                                # Clear the display by updating to empty content first
                                current_thinking_live.update("")
                                sys.stdout.flush()
                                time.sleep(0.02)  # Brief pause to ensure update is rendered
                                current_thinking_live.stop()
                                current_thinking_live.__exit__(None, None, None)
                                current_thinking_live = None  # Clear reference to prevent reuse
                            except Exception:
                                pass
                    except Exception:
                        pass
                    
                    try:
                        sys.stdout.flush()
                        sys.stderr.flush()
                        # CRITICAL: Longer pause to ensure all Live contexts are fully stopped and cleared
                        # This prevents thinking spinner from appearing while tool tiles are still visible
                        time.sleep(0.25)  # Longer pause to let terminal settle and ensure tiles are gone
                    except Exception:
                        pass
                    
                    # Continue loop to get next response
                    # CRITICAL: Additional delay before creating new thinking spinner
                    # This ensures tool tiles are completely gone before showing thinking spinner
                    sys.stdout.flush()
                    time.sleep(0.05)  # Brief pause to ensure tool tiles are fully cleared
                    # Start the next thinking spinner *now* so the user sees activity while we prepare the next model call
                    # (otherwise there can be a "dead air" gap between tool output and the next streamed response).
                    try:
                        console.print()
                        thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                        thinking_live = Live(thinking_panel, console=console, refresh_per_second=20, screen=False)
                        thinking_live.__enter__()
                        self._track_live_ref(thinking_live)
                        thinking_live.update(thinking_panel)
                        sys.stdout.flush()
                    except Exception:
                        thinking_live = None
                        try:
                            console.print("[dim]Thinking...[/dim]")
                        except Exception:
                            pass
                    continue
                else:
                    # No more tool calls, response already displayed during streaming
                    # CRITICAL: Ensure thinking spinner is stopped for text-only responses
                    if current_thinking_live:
                        try:
                            # Clear the display by updating to empty content first
                            current_thinking_live.update("")
                            sys.stdout.flush()
                            time.sleep(0.02)  # Brief pause to ensure update is rendered
                            current_thinking_live.stop()
                            current_thinking_live.__exit__(None, None, None)
                            current_thinking_live = None  # Clear reference
                            sys.stdout.flush()
                        except Exception:
                            pass
                    
                    # Add to history. In DeepSeek V4 thinking mode, the API
                    # expects `reasoning_content` to round-trip on every assistant
                    # turn — even text-only ones where the model produced no
                    # reasoning text. Always include the field (default ""); the
                    # API ignores empty values and we avoid the
                    # "reasoning_content must be passed back" rejection.
                    assistant_final_msg: Dict[str, Any] = {
                        "role": "assistant",
                        "content": display_content or "",
                        "reasoning_content": reasoning_content or "",
                    }
                    self.conversation_history.append(assistant_final_msg)
                    # Commit: final assistant message for this turn is complete.
                    try:
                        commit_checkpoint_len = len(self.conversation_history)
                    except Exception:
                        pass
                    # Durable checkpoint (crash recovery).
                    try:
                        self._checkpoint_session(force=True)
                    except Exception:
                        pass
                    
                    # Log this complete turn for fine-tuning
                    self._save_conversation_turn(user_message)

                    # POST-COMPACTION STALL GUARD: if the conversation was just compacted
                    # and the model replied with text but no tool_calls, retry once with a
                    # stronger directive to force a tool call.
                    if (self._is_post_compaction_turn()
                            and not _post_compaction_retried):
                        _post_compaction_retried = True
                        retry_msg = (
                            "[SYSTEM AUTO-INJECTED — the user did NOT type this]\n"
                            "You just responded with text but NO tool call. "
                            "The conversation was just compacted — you are mid-task. "
                            "Re-read the compacted context above and call the tool you need next. "
                            "Do NOT summarize. Call a tool NOW.\n"
                        )
                        self.conversation_history.append({
                            "role": "user",
                            "content": retry_msg,
                            "meta": {"auto_injected": True, "kind": "post_compaction_retry"},
                        })
                        console.print("[dim]🔄 Post-compaction stall detected — retrying with stronger directive[/dim]")
                        continue

                    # Ensure all Live contexts are stopped before returning to input loop
                    # This prevents terminal state issues that can freeze input
                    try:
                        sys.stdout.flush()
                        sys.stderr.flush()
                        time.sleep(0.05)  # Brief pause to let terminal settle
                    except Exception:
                        pass
                    
                    break

            # Record token usage for this completed turn (best-effort; used for /stats heatmap).
            # We use an estimate based on the tokens in the user message plus the new messages produced in this turn.
            try:
                # Use the turn-start checkpoint (immediately after the user message) so the estimate covers
                # everything produced during this turn (assistant + tools), even if we advanced commit checkpoints.
                new_messages = (self.conversation_history or [])[turn_start_checkpoint_len:]
                estimated_prompt_tokens = int(self._estimate_tokens(user_message))
                estimated_total_tokens = int(estimated_prompt_tokens + self._estimate_messages_tokens(new_messages))
                actual = int(actual_tokens_turn) if int(actual_tokens_turn) > 0 else None
                self._record_token_usage_for_today(estimated_tokens=estimated_total_tokens, actual_tokens=actual)

                # Keep billing dashboard usage aligned with the same turn-level source stream used by /stats.
                # If exact usage is available from relay chunks, send it; otherwise fall back to estimate.
                if self.billing_client:
                    total_tokens_for_billing = int(actual if actual is not None else estimated_total_tokens)
                    prompt_tokens_for_billing = min(max(0, estimated_prompt_tokens), max(0, total_tokens_for_billing))
                    completion_tokens_for_billing = max(0, total_tokens_for_billing - prompt_tokens_for_billing)
                    self.billing_client.report_usage({
                        "type": "turn_end",
                        "seconds": 0,
                        "tokens_prompt": prompt_tokens_for_billing,
                        "tokens_completion": completion_tokens_for_billing,
                    })
            except Exception:
                pass
        except KeyboardInterrupt:
            # On Ctrl+C: finalize in-flight tiles in place (preserving what the
            # user already saw), persist the partial assistant message into
            # history, and let interactive_mode handle the prompt return.
            try:
                # Finalize tool call tiles in place — they show the user what was
                # about to happen when they cancelled, which is useful context.
                if 'tool_call_live_map' in locals() and tool_call_live_map:
                    for tool_call_id, live_info in tool_call_live_map.items():
                        if live_info and live_info.get("live"):
                            try:
                                self._finalize_live_in_place(live_info["live"])
                            except Exception:
                                pass

                # Finalize the thinking/reasoning tile in place rather than
                # trying to delete it. Erasing a partially scrolled multi-line
                # Rich panel is what produced the orphan top border.
                if 'current_thinking_live' in locals() and current_thinking_live:
                    try:
                        self._finalize_live_in_place(current_thinking_live)
                    except Exception:
                        pass

                # Same for any local fallback thinking Live created between turns.
                if 'thinking_live' in locals() and thinking_live:
                    try:
                        self._finalize_live_in_place(thinking_live)
                    except Exception:
                        pass

                # Drop the global Live tracker WITHOUT calling stop on entries
                # we just finalized (they're already in scrollback).
                try:
                    self._tracked_live_refs = []
                except Exception:
                    pass

                # Roll back ONLY the in-flight tool-call/result entries (if any)
                # while keeping any partial assistant message saved by
                # _save_partial_assistant_on_interrupt. _partial_commit_len is
                # set there and points to one past the saved partial entry.
                try:
                    target_len = None
                    if 'commit_checkpoint_len' in locals() and isinstance(commit_checkpoint_len, int) and commit_checkpoint_len >= 0:
                        target_len = commit_checkpoint_len
                    partial_len = getattr(self, "_partial_commit_len", None)
                    if isinstance(partial_len, int) and partial_len > (target_len or 0):
                        target_len = partial_len
                    if target_len is not None and target_len < len(self.conversation_history or []):
                        self.conversation_history = (self.conversation_history or [])[:target_len]
                except Exception:
                    pass
                finally:
                    try:
                        # One-shot flag — clear so a future turn doesn't accidentally inherit it.
                        if hasattr(self, "_partial_commit_len"):
                            delattr(self, "_partial_commit_len")
                    except Exception:
                        pass

                # Print the explicit "Interrupted" panel below the partial
                # output so the user has a clear visual marker.
                try:
                    self._print_interrupt_panel()
                except Exception:
                    pass

                # Ensure terminal is in clean state
                sys.stdout.flush()
                sys.stderr.flush()
                time.sleep(0.05)
            except Exception:
                pass
            # Re-raise to let interactive_mode handle it
            raise
    
    def _cleanup_stray_live_contexts(self):
        """Clean up any stray Live contexts that may interfere with new spinners."""
        # Try to stop any Live contexts that might still be active
        # This is a safety net for cases where normal cleanup missed something
        try:
            import sys
            import time

            try:
                self._clear_tracked_live_refs()
            except Exception:
                pass

            # Rich Console keeps track of the currently active Live; if one is still attached,
            # starting a new spinner often won't render. Proactively stop anything attached.
            try:
                active_live = getattr(console, "_live", None)
                if active_live:
                    try:
                        # Prefer aggressive cleanup to avoid leaving border fragments.
                        self._delete_live_tile(active_live, pause=0.01)
                    except Exception:
                        pass
                    try:
                        active_live.__exit__(None, None, None)
                    except Exception:
                        pass
            except Exception:
                pass

            # Some Rich versions keep a stack for nested Live contexts; stop them too.
            try:
                live_stack = getattr(console, "_live_stack", None)
                if live_stack and isinstance(live_stack, list):
                    for lv in list(live_stack):
                        try:
                            self._delete_live_tile(lv, pause=0.01)
                        except Exception:
                            pass
                        try:
                            lv.__exit__(None, None, None)
                        except Exception:
                            pass
                    try:
                        live_stack.clear()
                    except Exception:
                        pass
            except Exception:
                pass

            # Ensure terminal is in a good state
            try:
                console.show_cursor(True)
            except Exception:
                pass
            sys.stdout.flush()
            sys.stderr.flush()
            time.sleep(0.05)
        except Exception:
            pass

    def _hard_cleanup_live_interrupt(self) -> None:
        """Best-effort global Live cleanup used by Ctrl+C handlers."""
        had_live = False
        try:
            if getattr(self, "_tracked_live_refs", None):
                had_live = True
        except Exception:
            pass
        try:
            if getattr(console, "_live", None):
                had_live = True
            live_stack = getattr(console, "_live_stack", None)
            if isinstance(live_stack, list) and len(live_stack) > 0:
                had_live = True
        except Exception:
            pass

        try:
            self._clear_tracked_live_refs()
        except Exception:
            pass
        try:
            self._cleanup_stray_live_contexts()
        except Exception:
            pass
        try:
            sys.stdout.flush()
            sys.stderr.flush()
        except Exception:
            pass
        # Final scrub for stubborn top-border remnants from interrupted Live tiles.
        if had_live:
            try:
                # Minimal scrub: clear current row and at most one row above.
                # More aggressive upward clears can clip the bottom of the last completed tile.
                sys.stdout.write("\r\033[2K")
                sys.stdout.write("\033[1A\r\033[2K")
                sys.stdout.write("\033[1B\r\033[2K")
                sys.stdout.write("\n")
                sys.stdout.flush()
            except Exception:
                pass
    
    def _ensure_live_clean_before_spinner(self):
        """Ensure terminal is clean before creating a new spinner."""
        import sys
        import time
        # Additional terminal reset
        console.line()
        console.show_cursor(True)
        sys.stdout.flush()
        sys.stderr.flush()
        time.sleep(0.1)
        self._cleanup_stray_live_contexts()
    
    def interactive_mode(self):
        """Run in interactive mode"""
        # Disable kernel echo of control characters (^C, ^\, etc.) for the
        # entire interactive session. Without this, a Ctrl+C pressed while a
        # Rich Live tile is mid-paint leaves a literal '^C' in the output
        # buffer that gets painted into the next tile's top border.
        with self._suppress_ctrl_c_echo():
            self._interactive_mode_inner()

    def _interactive_mode_inner(self):
        # Startup banner (keep it clean + static like a TUI splash screen)
        # NOTE: we keep the existing block-letter exclamation mark (the rightmost 3 chars on each line)
        # so it can be animated safely without changing the ASCII art layout.
        ascii_lines = [
            "  ███████╗██╗    ██╗███████╗███████╗████████╗██╗",
            "  ██╔════╝██║    ██║██╔════╝██╔════╝╚══██╔══╝██║",
            "  ███████╗██║ █╗ ██║█████╗  █████╗     ██║   ██║",
            "  ╚════██║██║███╗██║██╔══╝  ██╔══╝     ██║   ╚═╝",
            "  ███████║╚███╔███╔╝███████╗███████╗   ██║   ██╗",
            "  ╚══════╝ ╚══╝╚══╝ ╚══════╝╚══════╝   ╚═╝   ╚═╝",
        ]
        banner_quick = (
            "\n"
            "[dim]Quick commands[/dim]\n"
            "[cyan]•[/cyan] [bold white]/help[/bold white]  all commands\n"
            "[cyan]•[/cyan] [bold white]/stats[/bold white]  usage stats\n"
            "[cyan]•[/cyan] [bold white]/wrap[/bold white]  shareable daily wrap\n"
            "[cyan]•[/cyan] [bold white]/todos[/bold white]  view todos\n"
            "\n"
            "[dim]Sessions[/dim]\n"
            "[cyan]•[/cyan] [bold white]sweet resume[/bold white]\n"
            "[cyan]•[/cyan] [bold white]sweet start --session {sessionid}[/bold white]\n"
            "[cyan]•[/cyan] [bold white]/workfor 45m[/bold white]  autopilot for 45m\n"
            "[cyan]•[/cyan] [bold white]/workoff[/bold white]  stop autopilot\n"
            "[cyan]•[/cyan] [bold white]/jobs[/bold white]  list background jobs\n"
        )
        def _build_header_text(*, phase: int = 0, animate_all: bool = False) -> Text:
            """
            Build the header as a Rich Text object so we can animate the ASCII logo.
            Gradient motion: a rainbow gradient shifts horizontally over time (phase).
            """
            t = Text()
            # Higher-resolution gradient: compute per-character RGB from HSV.
            # This avoids chunky color bands from a small named-color palette.
            def _hsv_hex(h_deg: float, s: float = 0.78, v: float = 1.0) -> str:
                r, g, b = colorsys.hsv_to_rgb((h_deg % 360.0) / 360.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
                return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

            def _rainbow_line(line: str, phase_i: int, row_i: int) -> Text:
                lt = Text()
                for col, ch in enumerate(line):
                    if ch == " ":
                        lt.append(ch)
                    else:
                        # Diagonal, higher-res gradient:
                        # - include both row/col offsets for diagonal look
                        # - use degrees to create many "micro-steps" (higher resolution)
                        hue = (col * 9.0) + (row_i * 18.0) + (phase_i * 24.0)
                        lt.append(ch, style=f"bold {_hsv_hex(hue)}")
                return lt

            for i, line in enumerate(ascii_lines):
                if animate_all:
                    # Animate every non-space character in the logo.
                    line_text = _rainbow_line(line, phase, i)
                else:
                    line_text = Text(line, style="bold white")
                t.append_text(line_text)
                t.append("\n")
            t.append("\n")
            t.append_text(Text("Sweet! CLI Coding Agent\n", style="bold"))
            t.append_text(Text(f"v{self.version}\n", style="dim"))
            t.justify = "center"
            return t

        def _make_panel(*, phase: int = 0, animate_all: bool = False) -> Panel:
            header_text = _build_header_text(phase=phase, animate_all=animate_all)
            quick_text = Text.from_markup(banner_quick)
            return Panel(
                Group(
                    Align.center(header_text),
                    quick_text,
                ),
                border_style="cyan",
                padding=(1, 2),
                expand=True,
            )

        # Optional startup animation (short + delightful). Disable with SWEET_NO_ANIM=1.
        anim_enabled = os.environ.get("SWEET_NO_ANIM", "").strip().lower() not in ("1", "true", "yes", "on")
        try:
            anim_enabled = bool(anim_enabled and sys.stdout and sys.stdout.isatty())
        except Exception:
            pass

        if anim_enabled:
            try:
                live = Live(_make_panel(phase=0, animate_all=True), console=console, refresh_per_second=30, screen=False, transient=True)
                live.__enter__()
                self._track_live_ref(live)
                start = time.time()
                phase = 0
                duration_s = 1.0
                while (time.time() - start) < duration_s:
                    live.update(_make_panel(phase=phase, animate_all=True), refresh=True)
                    time.sleep(0.05)
                    phase += 1
                live.__exit__(None, None, None)
            except Exception:
                pass

        # Print final static banner
        console.print(_make_panel(phase=0, animate_all=False))
        
        # If resuming, show the last three messages under the banner.
        try:
            if self._resume_tail_messages:
                for msg in self._resume_tail_messages:
                    role = msg.get("role", "")
                    if role == "tool":
                        tc_id = msg.get("tool_call_id") or msg.get("id") or ""
                        tc = self._resume_tool_call_map.get(tc_id, {})
                        fname = tc.get("name") or "tool"
                        fargs = tc.get("args") or {}
                        result = {}
                        content = msg.get("content")
                        if isinstance(content, str) and content.strip():
                            try:
                                result = json.loads(content)
                            except Exception:
                                result = {"success": True, "content": content}
                        elif isinstance(content, dict):
                            result = content
                        panel = self._create_result_panel(fname, fargs, result)
                        console.print(panel)
                        console.print()
                    else:
                        label = "User" if role == "user" else "Assistant"
                        content = msg.get("content") or msg.get("reasoning_content") or ""
                        if not isinstance(content, str):
                            content = str(content)
                        content = content.strip()
                        if not content:
                            continue
                        if len(content) > 1600:
                            content = content[:900] + "\n… [truncated] …\n" + content[-300:]
                        panel = Panel(
                            content,
                            title=f"[bold cyan]🧾 {label}[/bold cyan]",
                            title_align="left",
                            border_style="dim",
                            padding=(1, 2),
                            width=80
                        )
                        console.print(panel)
                        console.print()
        except Exception:
            pass
        finally:
            # Only show once per resume.
            self._resume_tail_messages = None
            self._resume_tool_call_map = {}
        
        consecutive_error_count = 0
        max_consecutive_errors = 5
        last_interrupt_time = 0
        interrupt_threshold = 2.0  # seconds
        suppress_eof_until = 0.0  # Ignore EOFs until this timestamp after first Ctrl-C
        flush_input_once = False  # Drop any buffered keystrokes after response cancellation

        # If we resumed with history and --work-for is set, start autopilot immediately (no need for a new prompt).
        try:
            self._arm_autopilot_if_possible()
        except Exception:
            pass
        
        while True:
            try:
                # If autopilot is active (continuous work), inject a follow-up prompt instead of waiting for input.
                auto_injected = False
                now_ts = time.time()
                user_input = None
                try:
                    # Autopilot is "armed" until the first real user prompt arrives.
                    # The only exception is resume: _arm_autopilot_if_possible() will set _continuous_started_ts
                    # when there is prior user history, allowing immediate continuation after resume.
                    if (
                        (self._continuous_started_ts is not None)
                        and (
                        (self.continuous_work_seconds == -1)
                        or (
                            self.continuous_work_seconds > 0
                            and self._continuous_until_ts is not None
                            and now_ts < float(self._continuous_until_ts)
                            )
                        )
                    ):
                        # Guardrail 1: don't let autopilot re-inject faster than once every
                        # _autopilot_min_interval_s seconds. A misbehaving provider (empty
                        # responses, 4xx/5xx, cached failures) could otherwise spam the
                        # conversation with one "Timebox..." user message per second.
                        last_inj = self._autopilot_last_inject_ts
                        if last_inj is not None:
                            elapsed = now_ts - float(last_inj)
                            min_interval = float(self._autopilot_min_interval_s or 0.0)
                            if elapsed < min_interval:
                                try:
                                    time.sleep(min(min_interval - elapsed, 30.0))
                                except Exception:
                                    pass
                                now_ts = time.time()

                        # Guardrail 2: if previous autopilot turns produced nothing useful
                        # (no assistant text, no tool calls), stop re-injecting so we don't
                        # bloat history with increasingly-stale Timebox prompts.
                        if self._autopilot_empty_turns >= int(self._autopilot_empty_turn_limit or 0):
                            console.print(
                                f"[yellow]⚠️  Autopilot paused: {self._autopilot_empty_turns} consecutive empty turns. "
                                f"Type a new prompt to resume, or /workoff to disable.[/yellow]"
                            )
                            self._continuous_started_ts = None
                            self._continuous_until_ts = None
                            self._continuous_anchor_date = None
                            self._autopilot_empty_turns = 0
                        else:
                            anchor = self._continuous_anchor_date or datetime.now().strftime("%Y-%m-%d")
                            remaining_s = -1 if self.continuous_work_seconds == -1 else max(0, int(float(self._continuous_until_ts) - now_ts))
                            user_input = self.config.get_autopilot_prompt(anchor, int(remaining_s))
                            auto_injected = True
                            self._autopilot_last_inject_ts = now_ts
                            if remaining_s == -1:
                                console.print("[dim]⏱ Autopilot: continuing (no time limit)[/dim]")
                            else:
                                console.print(f"[dim]⏱ Autopilot: continuing (~{(remaining_s + 30)//60}m remaining)[/dim]")
                except Exception:
                    user_input = None
                    auto_injected = False

                # Ensure terminal is in a clean state before reading input
                # This prevents freezing when Live contexts or background processes leave terminal in bad state
                try:
                    # Flush all output streams to ensure nothing is blocking
                    sys.stdout.flush()
                    sys.stderr.flush()
                    # Give terminal a moment to settle after any Live context cleanup
                    # This allows any subprocess stdin handles to be fully released
                    time.sleep(0.05)
                except Exception:
                    pass
                
                # Use Rich's console.input() for proper terminal state management
                # Rich handles ANSI codes correctly and works well with Live contexts
                try:
                    if user_input is None:
                        # After an interrupt, terminal input can still contain a buffered keystroke
                        # that would render before the next prompt box (e.g. "t╭─────╮").
                        if flush_input_once:
                            try:
                                import termios
                                termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
                            except Exception:
                                pass
                            flush_input_once = False

                        # Ensure we start prompt rendering from a fresh line boundary.
                        try:
                            sys.stdout.write("\n")
                            sys.stdout.flush()
                        except Exception:
                            pass

                        # Match tool/reasoning tile styling: put the "You" label inside a bordered Panel,
                        # and keep the panel only as wide as the text.
                        console.print(
                            Panel(
                                Text("You", style="bold yellow"),
                                border_style="yellow",
                                padding=(0, 1),
                                expand=False,
                            )
                        )
                        user_input = console.input("[bold yellow]›[/bold yellow] ")
                except KeyboardInterrupt:
                    # Ctrl-C at input prompt - check if this is a second Ctrl-C
                    current_time = time.time()
                    if last_interrupt_time > 0 and (current_time - last_interrupt_time) < interrupt_threshold:
                        # Second Ctrl-C - exit immediately
                        self.save_session()
                        try:
                            sys.stdout.write("\nGoodbye! 👋\n")
                            sys.stdout.flush()
                        except Exception:
                            pass
                        try:
                            sys.exit(0)
                        except SystemExit:
                            raise
                        except:
                            os._exit(0)
                    # First Ctrl-C at input prompt - show warning and continue
                    try:
                        sys.stdout.write("\n⚠️  Press Ctrl-C again to exit the agent\n")
                        sys.stdout.flush()
                    except Exception:
                        pass
                    last_interrupt_time = current_time
                    suppress_eof_until = current_time + 1.0
                    continue
                except EOFError:
                    # Re-raise to let the exception handlers below deal with it
                    raise
                
                # Reset error count on successful input
                consecutive_error_count = 0
                # A real (not auto-injected) user turn means the user is actively guiding the agent;
                # clear the autopilot empty-turn counter so guardrails don't trip after past stalls.
                if not auto_injected:
                    self._autopilot_empty_turns = 0
                    self._autopilot_last_inject_ts = None
                # Any clean input should clear EOF suppression
                if suppress_eof_until > 0:
                    suppress_eof_until = 0.0
                
                if not user_input.strip():
                    continue
                # Normalize for command matching (fixes cases like "/stats " with trailing spaces)
                user_input = user_input.strip()

                # Clipboard paste helpers — inline: use /paste or /pasteclip anywhere in your message
                lower = user_input.lower()
                PASTE_TOKENS = ["/paste", "/pasteclip"]
                needs_paste = any(tok in lower for tok in PASTE_TOKENS)
                if needs_paste:
                    try:
                        import subprocess
                        cb = subprocess.check_output(["pbpaste"], text=True)
                        cb = cb if isinstance(cb, str) else str(cb)
                        cb = cb.strip("\n")
                        if not cb.strip():
                            console.print("[yellow]⚠️  Clipboard is empty — stripping /paste token(s)[/yellow]")
                            # Strip paste tokens but keep the rest of the message
                            for tok in PASTE_TOKENS:
                                user_input = user_input.replace(tok, "")
                            user_input = user_input.strip()
                            if not user_input:
                                continue
                        else:
                            console.print(f"[dim]↳ Pasted {len(cb)} chars from clipboard[/dim]")
                            # Replace every occurrence of /paste or /pasteclip with clipboard content
                            for tok in PASTE_TOKENS:
                                idx = lower.find(tok)
                                while idx != -1:
                                    user_input = user_input[:idx] + cb + user_input[idx + len(tok):]
                                    lower = user_input.lower()
                                    idx = lower.find(tok, idx + len(cb))
                    except Exception as e:
                        console.print(f"[red]✗ Clipboard paste failed:[/red] {e}")
                        # Strip paste tokens so the rest of the message still goes through
                        for tok in PASTE_TOKENS:
                            user_input = user_input.replace(tok, "")
                        user_input = user_input.strip()
                        if not user_input:
                            continue
                # Inline /pastefile <path> — can appear anywhere in the message
                PF_TOKEN = "/pastefile"
                if PF_TOKEN in lower:
                    import re as _re
                    pf_match = _re.search(r'/pastefile\s+(\S+)', user_input, _re.IGNORECASE)
                    if pf_match:
                        path = pf_match.group(1)
                        try:
                            p = Path(path).expanduser()
                            txt = p.read_text("utf-8", errors="replace").strip("\n")
                            if not txt.strip():
                                console.print("[yellow]⚠️  File is empty — stripping /pastefile token[/yellow]")
                                user_input = user_input[:pf_match.start()] + user_input[pf_match.end():]
                            else:
                                console.print(f"[dim]↳ Pasted {len(txt)} chars from {p}[/dim]")
                                # Replace the /pastefile <path> token with the file content
                                user_input = user_input[:pf_match.start()] + txt + user_input[pf_match.end():]
                        except Exception as e:
                            console.print(f"[red]✗ pastefile failed:[/red] {e}")
                            # Strip the token so the rest of the message still goes through
                            user_input = user_input[:pf_match.start()] + user_input[pf_match.end():]
                # Re-normalize after paste replacements
                user_input = user_input.strip()
                lower = user_input.lower()

                # Autopilot commands
                if lower.startswith("/workfor "):
                    spec = user_input[len("/workfor "):].strip()
                    secs = _parse_duration_seconds(spec)
                    if secs == 0 or secs < -1:
                        console.print("[red]✗ Invalid duration. Examples: /workfor 45m, /workfor 2h, /workfor 1h30m[/red]")
                    else:
                        self.continuous_work_seconds = secs
                        self._continuous_started_ts = None
                        self._continuous_until_ts = None
                        self._continuous_anchor_date = None
                        if secs == -1:
                            console.print("[green]✓[/green] Autopilot enabled (no time limit). Starts after your next prompt.")
                        else:
                            console.print(f"[green]✓[/green] Autopilot enabled for {secs//60} minutes (will start after your next prompt)")
                    continue
                if lower == "/workoff":
                    self.continuous_work_seconds = 0
                    self._continuous_started_ts = None
                    self._continuous_until_ts = None
                    self._continuous_anchor_date = None
                    console.print("[green]✓[/green] Autopilot disabled")
                    continue
                if lower == "/workstatus":
                    if self.continuous_work_seconds <= 0:
                        console.print("[dim]Autopilot: off[/dim]")
                    elif self.continuous_work_seconds == -1:
                        if self._continuous_started_ts is None:
                            console.print("[dim]Autopilot: armed (no time limit; starts after next prompt)[/dim]")
                        else:
                            console.print("[dim]Autopilot: on (no time limit)[/dim]")
                    elif self._continuous_until_ts:
                        rem = max(0, int(self._continuous_until_ts - time.time()))
                        console.print(f"[dim]Autopilot: on, {rem//60}m {rem%60}s remaining[/dim]")
                    else:
                        if self.continuous_work_seconds == -1:
                            console.print("[dim]Autopilot: armed (no time limit; starts after next prompt)[/dim]")
                        else:
                            console.print(f"[dim]Autopilot: armed for {self.continuous_work_seconds//60}m (starts after next prompt)[/dim]")
                    continue
                
                # Support simple 'cd' to update session working directory
                if user_input.startswith("cd "):
                    target = user_input[3:].strip() or os.path.expanduser("~")
                    try:
                        os.chdir(target)
                        self.session_cwd = os.getcwd()
                        console.print(f"[green]✓[/green] Working directory: [bold]{self.session_cwd}[/bold]")
                    except Exception as e:
                        console.print(f"[red]✗ cd failed:[/red] {e}")
                    continue
                
                if lower in ["exit", "quit"]:
                    self.save_session()
                    console.print("[cyan]Goodbye! 👋[/cyan]")
                    break
                
                if lower == "/todos":
                    self.display_todos()
                    continue

                if lower in ("/help", "/h", "/?"):
                    self.display_help()
                    continue
                
                if lower == "/stats":
                    self.display_stats()
                    continue

                if lower == "/stats share" or lower == "/stats wrap":
                    self.display_share_card("today")
                    continue

                if lower == "/wrap" or lower == "/wrap today":
                    self.display_share_card("today")
                    continue
                if lower == "/wrap week":
                    self.display_share_card("week")
                    continue
                if lower == "/wrap all" or lower == "/wrap alltime" or lower == "/wrap all-time":
                    self.display_share_card("all")
                    continue

                if lower in ("/whoami", "/account"):
                    self.display_billing_identity()
                    continue

                if lower == "/jobs":
                    if not self.background_jobs:
                        console.print("[dim]No background jobs[/dim]")
                        continue
                    console.print("[bold]Background jobs:[/bold]")
                    for jid, j in list(self.background_jobs.items()):
                        pid = j.get("pid")
                        running = self._is_pid_running(pid)
                        if not running and j.get("status") == "running":
                            j["status"] = "exited"
                        st = j.get("status") or ("running" if running else "exited")
                        cmd = (j.get("command") or "").strip()
                        wd = j.get("working_directory") or ""
                        logf = j.get("log_file") or ""
                        console.print(f"- [cyan]{jid}[/cyan] pid={pid} status={st}")
                        if cmd:
                            console.print(f"  [dim]cmd:[/dim] {cmd}")
                        if wd:
                            console.print(f"  [dim]cwd:[/dim] {wd}")
                        if logf:
                            console.print(f"  [dim]log:[/dim] {logf}")
                    continue

                if lower.startswith("/kill "):
                    target = user_input[len("/kill "):].strip()
                    if not target:
                        console.print("[red]Usage: /kill <job_id>[/red]")
                        continue
                    job = self.background_jobs.get(target)
                    if not job:
                        console.print(f"[red]Unknown job id:[/red] {target}")
                        continue
                    pid = job.get("pid")
                    try:
                        import os as _os, signal as _signal
                        if pid is None:
                            raise ValueError("job has no pid")
                        _os.kill(int(pid), _signal.SIGTERM)
                        job["status"] = "stopped"
                        console.print(f"[green]✓[/green] Stopped {target} (pid {pid})")
                    except Exception as e:
                        console.print(f"[red]✗ Failed to stop {target}:[/red] {e}")
                    continue
                
                if lower == "/clear":
                    self.conversation_history = []
                    self.conversation_summary = ""
                    console.print("[green]✓ Conversation history cleared[/green]")
                    continue
                
                # Track whether we are inside an active model/tool turn.
                # This helps Ctrl+C handling distinguish "cancel response" from "exit agent".
                agent_turn_in_progress = False

                # Show thinking spinner immediately when user hits enter
                console.print()  # Add spacing
                # Ensure terminal is clean before creating new spinner
                self._ensure_live_clean_before_spinner()
                live_manager = LiveManager(
                    console,
                    refresh_per_second=self.config.live_refresh_per_second,
                    min_update_interval=self.config.live_min_update_interval,
                    debug=False,
                    track_live=self._track_live_ref,
                    untrack_live=self._untrack_live_ref,
                )
                thinking_panel = Panel(Spinner("dots", text="[dim]Thinking...[/dim]"), border_style="dim", padding=(0, 1))
                # Keep the spinner in the normal buffer (no screen clear / top-jump)
                ui_ro = bool(getattr(self.config, "ui_reasoning_only", False))
                thinking_live = live_manager.start(thinking_panel, screen=False, transient=(not ui_ro))
                # Fallback: if LiveManager failed to start (rare), create a direct Live so user still sees spinner
                if not thinking_live:
                    thinking_live = Live(thinking_panel, console=console, refresh_per_second=self.config.live_refresh_per_second, screen=False)
                    thinking_live.__enter__()
                    self._track_live_ref(thinking_live)
                # Absolute fallback: if Live still failed, print a dim placeholder so user sees activity
                if not thinking_live:
                    console.print("[dim]Thinking...[/dim]")
                # Ensure the spinner is visible immediately before any blocking operations
                sys.stdout.flush()
                # CRITICAL: Force multiple renders to overcome buffering
                min_visible_start = time.time()
                for _ in range(3):
                    time.sleep(0.02)
                    if thinking_live:
                        thinking_live.update(thinking_panel)
                    sys.stdout.flush()
                # Guarantee a minimum on-screen time so the user sees the spinner
                elapsed = time.time() - min_visible_start
                if elapsed < 0.2:
                    time.sleep(0.2 - elapsed)
                
                try:
                    # Track duration of this agent turn (from user submit until the agent returns control)
                    turn_started_at = time.time()
                    # Start continuous window on first manual user prompt.
                    if (self.continuous_work_seconds == -1 or self.continuous_work_seconds > 0) and (not self._continuous_until_ts) and (not auto_injected):
                        self._continuous_started_ts = turn_started_at
                        if self.continuous_work_seconds == -1:
                            self._continuous_until_ts = None
                        else:
                            self._continuous_until_ts = float(turn_started_at) + float(self.continuous_work_seconds)
                        self._continuous_anchor_date = datetime.fromtimestamp(turn_started_at).strftime("%Y-%m-%d")
                    agent_turn_in_progress = True
                    # Snapshot history length so we can tell afterwards whether the turn actually
                    # produced anything beyond the auto-injected user message itself (for autopilot
                    # empty-turn detection).
                    history_len_before_turn = len(self.conversation_history)
                    self.run_conversation(user_input, thinking_live=thinking_live, auto_injected=auto_injected)
                    agent_turn_in_progress = False
                    # Update autopilot empty-turn counter: a healthy turn appends at least a user
                    # message + an assistant message (and often tool/tool_result pairs). If only the
                    # user message was added, the LLM produced nothing useful.
                    try:
                        if auto_injected:
                            added = max(0, len(self.conversation_history) - history_len_before_turn)
                            produced_something = False
                            if added > 1:
                                # Anything appended after the injected user message counts as progress.
                                for m in self.conversation_history[history_len_before_turn + 1:]:
                                    if not isinstance(m, dict):
                                        continue
                                    role = m.get("role")
                                    if role == "assistant" and ((m.get("content") or "").strip() or m.get("tool_calls")):
                                        produced_something = True
                                        break
                                    if role == "tool":
                                        produced_something = True
                                        break
                            if produced_something:
                                self._autopilot_empty_turns = 0
                            else:
                                self._autopilot_empty_turns = int(self._autopilot_empty_turns) + 1
                    except Exception:
                        pass
                    # If compaction happened during this turn, print a stable notice line (like autopilot status).
                    try:
                        line = getattr(self, "_last_compaction_notice_line", None)
                        if isinstance(line, str) and line.strip():
                            console.print(f"[dim]{line}[/dim]")
                        self._last_compaction_notice_line = None
                    except Exception:
                        pass
                except KeyboardInterrupt:
                    # Ctrl+C should always interrupt generation, including during autopilot.
                    # IMPORTANT UX: if autopilot is enabled and the user interrupts *any* generation (manual or auto-injected),
                    # pause autopilot (do not disable) and return to the input prompt. This prevents the agent from immediately
                    # starting another autopilot turn right after the interrupt.
                    if self.continuous_work_seconds != 0:
                        # Preserve remaining time when possible so a timed autopilot run doesn't restart
                        # from the full duration after an interrupt.
                        try:
                            if self.continuous_work_seconds != -1 and self._continuous_until_ts is not None:
                                remaining_s = max(0, int(float(self._continuous_until_ts) - time.time()))
                                self.continuous_work_seconds = remaining_s
                        except Exception:
                            pass

                        # "Armed" state: require the next real user prompt to resume autopilot.
                        self._continuous_started_ts = None
                        self._continuous_until_ts = None
                        self._continuous_anchor_date = None

                        if self.continuous_work_seconds == -1:
                            msg = "Autopilot paused (no time limit). It will resume after your next prompt."
                        elif self.continuous_work_seconds <= 0:
                            msg = "Autopilot interrupted (Ctrl+C). No time remaining; back to input."
                            self.continuous_work_seconds = 0
                        else:
                            msg = f"Autopilot paused with ~{int(self.continuous_work_seconds)//60}m remaining. It will resume after your next prompt."
                        console.print(f"\n[yellow]⚠️  {msg} Use /workoff to disable.[/yellow]")
                        agent_turn_in_progress = False
                        continue

                    # Autopilot is off: keep existing behavior (cancel current response / double Ctrl+C to exit)
                    raise
                except Exception as e:
                    console.print(f"[red]Error in run_conversation: {escape(str(e))}[/red]")
                    agent_turn_in_progress = False
                finally:
                    # CRITICAL: Always ensure thinking spinner is stopped and reset
                    # This prevents terminal from being left in bad state.
                    # Note: sometimes we fall back to a direct Live(...) spinner; in that case,
                    # stopping only the LiveManager is not enough (it may never have started).
                    try:
                        if live_manager:
                            # Check if thinking_live is the same as live_manager.live
                            if thinking_live is not None and live_manager.live is thinking_live:
                                # Managed by live_manager, stop via manager only
                                live_manager.stop(clear=True)
                                thinking_live = None
                            else:
                                # thinking_live is separate or None, stop both safely
                                live_manager.stop(clear=True)
                    except Exception:
                        pass
                    # Use the safe method to stop thinking_live if it exists
                    self._stop_live_context(thinking_live, clear=True, pause=0.02)
                    # Always reset thinking_live to None after use
                    thinking_live = None
                    # Ensure terminal is ready for next input
                    sys.stdout.flush()
                    sys.stderr.flush()
                    time.sleep(0.05)  # Brief pause to ensure terminal is ready
                    

                    # Print turn duration summary once we're back to user input
                    try:
                        if 'turn_started_at' in locals() and turn_started_at:
                            duration_s = max(0.0, time.time() - float(turn_started_at))
                            total_minutes = int(duration_s // 60)
                            hours = total_minutes // 60
                            minutes = total_minutes % 60
                            seconds = int(duration_s % 60)
                            parts = []
                            if hours > 0:
                                parts.append(f"{hours} hr")
                            if minutes > 0 or hours > 0:
                                parts.append(f"{minutes} min")
                            # show seconds only for short turns (< 2 min) to avoid noise
                            if hours == 0 and minutes < 2:
                                parts.append(f"{seconds} sec")
                            worked_for = " ".join(parts) if parts else "0 sec"
                            console.print(f"[dim]Worked for {worked_for}[/dim]")
                    except Exception:
                        pass
                
            except KeyboardInterrupt:
                current_time = time.time()
                
                # CRITICAL: Clean up ALL Live contexts to restore terminal state
                # This prevents terminal from being left in bad state that blocks input
                agent_responding = bool(locals().get("agent_turn_in_progress", False))
                try:
                    self._hard_cleanup_live_interrupt()

                    # Clean up thinking Live context
                    if 'thinking_live' in locals() and thinking_live:
                        agent_responding = True
                        try:
                            # Clear the display by updating to empty content first
                            thinking_live.update("")
                            sys.stdout.flush()
                            time.sleep(0.02)  # Brief pause to ensure update is rendered
                            thinking_live.stop()
                            thinking_live.__exit__(None, None, None)
                        except Exception:
                            pass
                        thinking_live = None
                    
                    # If any Rich Live context is still active, we were still in an agent-rendered turn.
                    try:
                        active_live = getattr(console, "_live", None)
                        live_stack = getattr(console, "_live_stack", None)
                        if active_live or (isinstance(live_stack, list) and len(live_stack) > 0):
                            agent_responding = True
                    except Exception:
                        pass

                    self._hard_cleanup_live_interrupt()

                    # CRITICAL: Ensure terminal is fully restored
                    # Flush all streams and wait to ensure cleanup completes
                    sys.stdout.flush()
                    sys.stderr.flush()
                    time.sleep(0.1)  # Brief pause to ensure cleanup completes and terminal is ready
                except Exception:
                    # Ensure thinking_live is reset even if cleanup fails
                    if 'thinking_live' in locals():
                        thinking_live = None
                
                # If agent was responding, cancel it and return to input prompt
                if agent_responding:
                    # If an inner handler (e.g. tool-execution cancel) already
                    # showed its own, more specific banner, don't double up.
                    suppress_banner = False
                    try:
                        if getattr(self, "_cancel_notice_shown", False):
                            suppress_banner = True
                            self._cancel_notice_shown = False
                    except Exception:
                        suppress_banner = False
                    if not suppress_banner:
                        try:
                            sys.stdout.write("\n⚠️  Response cancelled. Press Ctrl-C again to exit.\n")
                            sys.stdout.flush()
                        except Exception:
                            pass
                    # Reset interrupt time since we're cancelling the response, not quitting
                    last_interrupt_time = 0
                    agent_turn_in_progress = False
                    flush_input_once = True
                    # Ensure thinking_live is None for next iteration
                    thinking_live = None
                    # Additional cleanup to ensure terminal is ready for input
                    try:
                        sys.stdout.flush()
                        sys.stderr.flush()
                        time.sleep(0.05)  # Brief pause to ensure terminal is ready
                    except Exception:
                        pass
                    continue
                
                # Agent is not responding - we're at the input prompt
                # Check if this is a double Ctrl-C (within threshold)
                if last_interrupt_time > 0 and (current_time - last_interrupt_time) < interrupt_threshold:
                    # Second Ctrl-C - exit immediately
                    self.save_session()
                    try:
                        sys.stdout.write("\nGoodbye! 👋\n")
                        sys.stdout.flush()
                    except Exception:
                        pass
                    # Exit cleanly with code 0
                    try:
                        sys.exit(0)
                    except SystemExit:
                        raise
                    except:
                        os._exit(0)
                
                # First Ctrl-C at input prompt - show warning
                try:
                    sys.stdout.write("\n⚠️  Press Ctrl-C again to exit the agent\n")
                    sys.stdout.flush()
                except Exception:
                    pass

                last_interrupt_time = current_time
                # The input stream may emit an immediate EOF after SIGINT; ignore EOFs briefly
                suppress_eof_until = current_time + 1.0
                continue
            except EOFError:
                # Some wrappers emit EOFs immediately after SIGINT; ignore EOFs for a brief window
                now = time.time()
                if suppress_eof_until and now <= suppress_eof_until:
                    continue
                # Treat EOF like a first Ctrl-C (do not exit immediately)
                try:
                    sys.stdout.write("\n⚠️  Press Ctrl-C again to exit the agent\n")
                    sys.stdout.flush()
                except Exception:
                    pass
                last_interrupt_time = now
                suppress_eof_until = now + 1.0
                continue
                    
            except Exception as e:
                consecutive_error_count += 1
                console.print(f"[red]Error: {escape(str(e))}[/red]")
                if consecutive_error_count >= max_consecutive_errors:
                    self.save_session()
                    console.print("\n[red]Too many errors. Exiting safely.[/red]")
                    # Re-raise to let main() handle consistent exit
                    raise KeyboardInterrupt
                # Reset error count on successful input
                if consecutive_error_count > 0:
                    consecutive_error_count = 0


def find_latest_session(sessions_dir: str = "sessions") -> Optional[str]:
    """
    Find the most recent session file in the sessions directory (by mtime).
    In normal exits the newest file is a session_end snapshot; for crashes, a checkpoint may be newest.
    
    Args:
        sessions_dir: Directory containing session files
        
    Returns:
        Path to the latest session file, or None if no sessions found
    """
    def _is_session_end_filename(name: str) -> bool:
        if name.endswith("-session_end.json"):
            return True
        # Legacy format: session-YYYYMMDD-HHMMSS.json
        return bool(re.match(r"^session-\d{8}-\d{6}\.json$", name))

    # First check the sessions directory for new format
    if os.path.exists(sessions_dir):
        session_paths: List[str] = []
        for filename in os.listdir(sessions_dir):
            if not (filename.startswith("session-") and filename.endswith(".json")):
                continue
            path = os.path.join(sessions_dir, filename)
            if os.path.isfile(path):
                session_paths.append(path)
        
        if session_paths:
            try:
                session_paths.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            except Exception:
                # Fallback: lexicographic sort if mtime fails
                session_paths.sort(reverse=True)
            for path in session_paths:
                try:
                    with open(path, "r") as f:
                        json.load(f)
                    return path
                except Exception:
                    continue
    
    # Fallback: check for conversation_logs_session.json in current directory (old format)
    if os.path.exists("conversation_logs_session.json"):
        return "conversation_logs_session.json"
    
    return None


def load_session_data(session_file: str) -> Dict[str, Any]:
    """
    Load session data from a session file.
    
    Args:
        session_file: Path to the session file
        
    Returns:
        Session data dictionary
    """
    with open(session_file, 'r') as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="CLI LLM Agent with function calling and todo management"
    )
    
    # Add arguments that work both with and without subcommands
    parser.add_argument(
        'message',
        nargs='*',
        help='Optional initial message/prompt'
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="DeepSeek API key (or set DEEPSEEK_API_KEY env var) - only needed if not using billing"
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=['deepseek', 'nebius', 'fireworks', 'local'],
        default='deepseek',
        help="Model provider (default: deepseek)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name override"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Single prompt to execute (non-interactive mode)"
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Log conversations to JSONL for fine-tuning"
    )
    parser.add_argument(
        "--snapshot-compactions",
        action="store_true",
        help="Save pre-compaction conversation windows to training_snapshots/ (without enabling full JSONL logging)"
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default="conversation_logs.jsonl",
        help="Path to log file (default: conversation_logs.jsonl)"
    )
    parser.add_argument(
        "--no-billing",
        action="store_true",
        help="Use direct DeepSeek API instead of billing relay"
    )
    parser.add_argument(
        '--api-base',
        type=str,
        help='Billing API base URL (for login)'
    )
    parser.add_argument(
        "--list-sessions",
        action="store_true",
        help="List saved sessions in the current directory and exit"
    )
    parser.add_argument(
        "--list-sessions-json",
        action="store_true",
        help="List saved sessions as JSON for CLI consumption and exit"
    )
    parser.add_argument(
        "--resume-last",
        action="store_true",
        help="Resume the most recent session in the current directory"
    )
    parser.add_argument(
        "--session",
        type=str,
        help="Resume a specific session by ID (YYYYMMDD-HHMMSS) or path"
    )
    parser.add_argument(
        "--work-for",
        type=str,
        help="Keep working continuously without further user input for this long (e.g. '45m', '2h', '1h30m', or 'forever'). Timer starts on your first prompt."
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Run system health check and exit"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version information and exit"
    )
    
    # Check if first arg is 'resume' (before parsing)
    if len(sys.argv) > 1 and sys.argv[1] == 'resume':
        # Remove 'resume' from args and continue with normal flow
        sys.argv.pop(1)
        # Set a flag to load the latest session
        os.environ['SWEET_RESUME'] = 'true'
        # Also set --resume-last flag for argparse compatibility
        if '--resume-last' not in sys.argv:
            sys.argv.insert(1, '--resume-last')
    
    # Check if first arg is 'login' (before parsing)
    if len(sys.argv) > 1 and sys.argv[1] == 'login':
        # Parse login-specific args
        login_parser = argparse.ArgumentParser()
        login_parser.add_argument('login_cmd')
        login_parser.add_argument('--api-base', type=str, help='Billing API URL')
        login_args = login_parser.parse_args()
        
        # Handle login command
        billing_client = get_billing_client()
        api_base = login_args.api_base or billing_client.get_api_base()
        
        console.print("[cyan]🔐 Sweet Agent Login[/cyan]\n")
        console.print(f"[dim]Connecting to {api_base}[/dim]\n")
        
        if billing_client.login(api_base):
            console.print("\n[green]✅ You're all set! Run 'sweet' to start.[/green]")
        else:
            console.print("\n[red]❌ Login failed. Please try again.[/red]")
            sys.exit(1)
        return
    
    # Parse regular arguments
    args = parser.parse_args()

    # Utility: list sessions
    def _collect_sessions(sessions_dir: str = "sessions") -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        try:
            if os.path.exists(sessions_dir):
                for filename in os.listdir(sessions_dir):
                    if not (filename.startswith("session-") and filename.endswith(".json")):
                        continue
                    path = os.path.join(sessions_dir, filename)
                    try:
                        data = load_session_data(path)
                    except Exception:
                        data = {}
                    started = data.get("session_start")
                    ended = data.get("session_end")
                    messages = data.get("messages", [])
                    last_assistant = ""
                    for m in reversed(messages):
                        if m.get("role") == "assistant" and isinstance(m.get("content"), str):
                            last_assistant = (m.get("content") or "").strip()
                            break
                    preview = (last_assistant[:120] + ("…" if len(last_assistant) > 120 else "")) if last_assistant else ""
                    # id is the timestamp portion of the filename
                    base = os.path.basename(path)
                    sid = base.replace("session-", "").replace(".json", "")
                    results.append({
                        "id": sid,
                        "path": path,
                        "started_at": started,
                        "ended_at": ended,
                        "duration_seconds": (ended - started) if (isinstance(ended, (int, float)) and isinstance(started, (int, float))) else None,
                        "last_preview": preview,
                    })
            # Sort newest first by id (filename timestamp sorts lexicographically)
            results.sort(key=lambda r: r.get("id", ""), reverse=True)
        except Exception:
            pass
        return results

    if args.list_sessions or args.list_sessions_json:
        sessions = _collect_sessions()
        if args.list_sessions_json:
            try:
                sys.stdout.write(json.dumps({"sessions": sessions}, indent=2) + "\n")
                sys.stdout.flush()
            except Exception:
                pass
        else:
            if not sessions:
                console.print("[dim]No sessions found in ./sessions[/dim]")
            else:
                console.print("[bold]Saved sessions (newest first):[/bold]")
                for s in sessions:
                    ts = s.get("id", "")
                    dur = s.get("duration_seconds")
                    dur_s = f" ({int(dur)}s)" if isinstance(dur, (int, float)) else ""
                    preview = s.get("last_preview") or ""
                    console.print(f"- [cyan]{ts}[/cyan]{dur_s} — [dim]{preview}[/dim]")
        return
    
    if args.health_check:
        console.print("[bold]Sweet! CLI Health Check[/bold]")
        console.print("[dim]Running system diagnostics...[/dim]")
        import platform
        python_version = platform.python_version()
        console.print(f"✅ Python {python_version}")
        try:
            import rich
            console.print("✅ Rich library installed")
        except ImportError:
            console.print("❌ Rich library missing")
        billing_client = get_billing_client()
        api_base = billing_client.get_api_base()
        console.print(f"[dim]Billing server: {api_base}[/dim]")
        if billing_client.is_authenticated():
            console.print("✅ Authenticated with billing server")
        else:
            console.print("⚠️ Not authenticated (run 'sweet login')")
        console.print("[green]Health check completed.[/green]")
        return
    
    if args.version:
        console.print("[bold]Sweet! CLI[/bold]")
        console.print("Version: 0.2.7")
        console.print("Build: 2026-02-01")
        return
    
    # Also check if message contains 'login' (legacy support)
    if args.message and args.message[0] == 'login':
        # Handle login command
        billing_client = get_billing_client()
        api_base = args.api_base or billing_client.get_api_base()
        
        console.print("[cyan]🔐 Sweet Agent Login[/cyan]\n")
        console.print(f"[dim]Connecting to {api_base}[/dim]\n")
        
        if billing_client.login(api_base):
            console.print("\n[green]✅ You're all set! Run 'sweet' to start.[/green]")
        else:
            console.print("\n[red]❌ Login failed. Please try again.[/red]")
            sys.exit(1)
        return
    
    # Handle start/run command
    billing_client = None
    api_key = None
    
    # Check if we should use billing
    if not args.no_billing:
        billing_client = get_billing_client()
        
        if billing_client.is_authenticated():
            # Skip billing check if called by npm package (it already checked)
            from_npm = os.environ.get('SWEET_BILLING_TOKEN') or os.environ.get('SWEET_RELAY_API')
            
            if not from_npm:
                # Check subscription and reserve session (standalone mode)
                console.print("[dim]🔒 Checking billing...[/dim]")
                reserve_result = billing_client.check_and_reserve(estimated_minutes=5)
                
                if not reserve_result['ok']:
                    console.print(f"\n[red]❌ {reserve_result.get('message', 'Billing check failed')}[/red]")
                    api_base = reserve_result.get('apiBase', billing_client.get_api_base())
                    console.print(f"[dim]Manage subscription at: {api_base}/billing.html[/dim]\n")
                    sys.exit(1)
                
                console.print("[green]✓ Billing OK[/green]\n")
        else:
            # Not authenticated, fall back to API key
            console.print("[yellow]⚠️  Not signed in to billing server[/yellow]")
            console.print("[dim]Run 'python main.py login' to use the billing relay[/dim]")
            console.print("[dim]Or provide --api-key to use DeepSeek API directly[/dim]\n")
            billing_client = None
    
    # If not using billing, require API key
    if billing_client is None:
        provider = getattr(args, "provider", "deepseek")
        if provider == "fireworks":
            api_key = args.api_key or os.environ.get("FIREWORKS_API_KEY")
        else:
            api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
        
        if not api_key:
            console.print("[red]Error: No authentication method available.[/red]")
            console.print("Either:")
            console.print("  1. Run 'python main.py login' to sign in")
            if provider == "fireworks":
                console.print("  2. Provide --api-key or set FIREWORKS_API_KEY env var")
            else:
                console.print("  2. Provide --api-key or set DEEPSEEK_API_KEY env var")
            sys.exit(1)
    
    # Create agent
    agent = CLIAgent(
        api_key=api_key,
        billing_client=billing_client,
        provider=getattr(args, "provider", "deepseek"),
        model=getattr(args, "model", None),
        log_conversations=args.log, 
        log_file=args.log_file,
        snapshot_compactions=args.snapshot_compactions,
    )

    # Configure CLI continuous work mode
    try:
        if getattr(args, "work_for", None):
            secs = _parse_duration_seconds(args.work_for)
            if secs == -1:
                agent.continuous_work_seconds = -1
                console.print("[dim]⏱ Autopilot armed (no time limit; starts on your first prompt)[/dim]")
            elif secs > 0:
                agent.continuous_work_seconds = secs
                console.print(f"[dim]⏱ Autopilot armed for {secs//60} minutes (starts on your first prompt)[/dim]")
            else:
                console.print("[yellow]⚠️  Ignoring invalid --work-for duration. Examples: 45m, 2h, 1h30m, forever[/yellow]")
    except Exception:
        pass
    
    # Helper to restore a session file
    def _restore_session(session_path: str):
        try:
            session_data = load_session_data(session_path)
            console.print(f"[green]✓  Loaded session from {session_path}[/green]")
            messages = session_data.get("messages", [])
            agent.conversation_history = messages
            tool_call_map: Dict[str, Dict[str, Any]] = {}
            for m in messages:
                if m.get("role") == "assistant" and m.get("tool_calls"):
                    for tc in (m.get("tool_calls") or []):
                        tc_id = tc.get("id") or tc.get("tool_call_id") or ""
                        fn = (tc.get("function") or {})
                        name = fn.get("name") or ""
                        args_raw = fn.get("arguments") or ""
                        args_obj: Dict[str, Any] = {}
                        if isinstance(args_raw, str) and args_raw.strip():
                            try:
                                args_obj = json.loads(args_raw)
                            except Exception:
                                args_obj = {"_raw": args_raw}
                        tool_call_map[tc_id] = {"name": name, "args": args_obj}
            if "cwd" in session_data:
                agent.session_cwd = session_data["cwd"]
                console.print(f"[dim]Restored working directory: {session_data['cwd']}[/dim]")
            # Rehydrate subagent sessions/jobs so the user can see what was in-flight
            # and so poll/list tools still resolve by subagent_id after a restart.
            try:
                sub_snap = session_data.get("subagents")
                if isinstance(sub_snap, dict):
                    interrupted = agent._restore_subagents_from_state(sub_snap)
                    n_jobs = len(sub_snap.get("jobs") or {})
                    n_sessions = len(sub_snap.get("sessions") or {})
                    if n_sessions or n_jobs:
                        suffix = f", {interrupted} marked interrupted" if interrupted else ""
                        console.print(
                            f"[dim]🧵 Restored {n_sessions} subagent session(s), {n_jobs} job(s){suffix}[/dim]"
                        )
            except Exception as e:
                console.print(f"[dim]⚠  Failed to restore subagent state: {escape(str(e))}[/dim]")
            console.print("[green]✅  Session restored! Continuing conversation...[/green]")
            console.print()
            try:
                valid_messages = agent._filter_valid_messages(messages)
            except Exception:
                valid_messages = list(messages)
            non_system = [m for m in valid_messages if m.get("role") in ("user", "assistant", "tool")]
            # If the session ended right after a user prompt (Ctrl+C at input),
            # drop trailing user-only entries so we show the last completed turn.
            while non_system and non_system[-1].get("role") == "user":
                non_system.pop()
            tail = non_system[-3:] if len(non_system) > 3 else non_system
            agent._resume_tail_messages = tail or None
            agent._resume_tool_call_map = tool_call_map
        except Exception as e:
            console.print(f"[red]❌  Failed to load session: {escape(str(e))}[/red]")

    # Handle resume flags
    if os.environ.get('SWEET_RESUME') == 'true' or args.resume_last or args.session:
        target_path: Optional[str] = None
        if args.session:
            # Map ID to path if needed
            cand = args.session
            if os.path.isfile(cand):
                target_path = cand
            else:
                # Try sessions/session-<id>.json
                guess = os.path.join("sessions", f"session-{cand}.json")
                if os.path.isfile(guess):
                    target_path = guess
        if not target_path:
            # Default to latest
            target_path = find_latest_session()
        if target_path:
            _restore_session(target_path)
            # If autopilot is enabled, arm it immediately on resume and start working right away.
            try:
                agent._arm_autopilot_if_possible()
                until = getattr(agent, "_continuous_until_ts", None)
                anchor = getattr(agent, "_continuous_anchor_date", None) or datetime.now().strftime("%Y-%m-%d")
                if agent.continuous_work_seconds == -1:
                    console.print("[dim]⏱ Autopilot: resuming work (no time limit)[/dim]")
                    agent.run_conversation(agent.config.get_autopilot_prompt(anchor, -1), auto_injected=True)
                elif until and time.time() < float(until):
                    remaining_s = int(float(until) - time.time())
                    console.print(f"[dim]⏱ Autopilot: resuming work (~{(remaining_s + 30)//60}m remaining)[/dim]")
                    agent.run_conversation(agent.config.get_autopilot_prompt(anchor, remaining_s), auto_injected=True)
            except Exception:
                pass
        # Clear env resume flag
        os.environ.pop('SWEET_RESUME', None)
    
    # Show status
    if billing_client:
        console.print("[dim]🌐 Using Sweet billing relay[/dim]")
        cached_email = billing_client.get_cached_email()
        if cached_email:
            console.print(f"[dim]👤 Signed in as {cached_email}[/dim]")
    else:
        console.print("[dim]🔑 Using direct DeepSeek API[/dim]")
    
    if args.log:
        console.print(f"[dim]💾 Logging conversations to {args.log_file}[/dim]")
    
    console.print()
    
    # Run in appropriate mode
    try:
        # Check for prompt from either --prompt flag or positional message args
        prompt = args.prompt or (hasattr(args, 'message') and args.message and ' '.join(args.message))
        
        if prompt:
            agent.run_conversation(prompt)
            agent.save_session()
            return
        else:
            agent.interactive_mode()
    except KeyboardInterrupt:
        # Ctrl+C can occur during streaming network reads; avoid dumping a stack trace.
        try:
            agent._print_interrupt_notice()
        except Exception:
            pass
        try:
            agent.save_session()
        except Exception:
            pass
        try:
            sys.exit(0)
        except SystemExit:
            raise
    except Exception as e:
        safe_error = escape(str(e))
        console.print(f"\n[red]Unexpected error: {safe_error}[/red]")
        try:
            agent.save_session()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Absolute last-resort guard to prevent raw traceback on Ctrl+C
        try:
            sys.stdout.write("\n⚠️  Interrupted. Goodbye!\n")
            sys.stdout.flush()
        except Exception:
            pass
        raise SystemExit(0)


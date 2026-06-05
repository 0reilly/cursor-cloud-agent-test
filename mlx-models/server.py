#!/usr/bin/env python3
"""
Qwen3.5-9B-MLX Local Server with Streaming

A FastAPI server that provides streaming inference for the Qwen3.5-9B-MLX model.
Supports both streaming and non-streaming responses.

Usage:
    python3 server.py
"""

import asyncio
import json
import time
from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any

import mlx_lm
from mlx_lm.models import cache
from mlx_lm.generate import generate_step
import mlx.core as mx
import hashlib, os, re, uuid
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Configuration
MODEL_PATH = os.environ.get('MODEL_PATH', "/Users/adamoreilly/.cache/huggingface/hub/models--prism-ml--Ternary-Bonsai-8B-mlx-2bit/snapshots/9260b24298e4211e804663e9f519962cf59f34be")
MODEL_NAME = os.environ.get('MODEL_NAME', 'Ternary-Bonsai-8B-mlx-2bit')
HOST = "0.0.0.0"
PORT = int(os.environ.get('PORT', 8000))
MAX_CACHEABLE_TOKENS = 4096  # Cache up to 4096 tokens (fits sweet CLI system prompt ~1339 tokens + tools)
PREFILL_STEP_SIZE = 8192  # Default mlx_lm value (faster prefill)
_kv_bits_raw = os.environ.get('KV_BITS', None)
try:
    KV_BITS = int(_kv_bits_raw) if _kv_bits_raw and str(_kv_bits_raw).lower() not in ('none', 'null', '') else None  # KV cache quantization (8=good speed/quality, 4=aggressive, None=off); off by default (required for Ternary-Bonsai rotating KV cache)
except (ValueError, TypeError):
    KV_BITS = None
MAX_KV_SIZE = 4096  # Allow full conversation context (was 512, too small for CLI agent)
ENABLE_PREFILL = True  # Can be disabled if memory issues persist
MAX_CACHES = 3  # Maximum number of system prompt caches to keep (prevent OOM)
DRAFT_MODEL_PATH = os.environ.get('DRAFT_MODEL')  # Disabled by default (regresses 10-18% on 9B with 0.8B draft)
NUM_DRAFT_TOKENS = int(os.environ.get('NUM_DRAFT_TOKENS', '3'))

# Global model and tokenizer
model = None
tokenizer = None
draft_model = None

# System prompt KV cache
system_prompt_caches = {}  # hash -> (cache, prefix_len)
cache_lock = threading.Lock()

import re
_THINK_PATTERN = re.compile(r'<think>.*?</think>\s*', re.DOTALL)
_THINK_OPEN_PATTERN = re.compile(r'<think>.*$', re.DOTALL)

def strip_thinking(text: str) -> str:
    """Remove <think>...</think> blocks from Qwen responses.
    
    Qwen3.5 models may output reasoning in <think> tags. This function
    strips those blocks, returning only the final assistant response.
    Handles complete blocks, unclosed blocks, and nested blocks.
    
    Strategy:
    - Complete <think>...</think> blocks: removed entirely
    - Unclosed <think> (no matching </think>): strip the opening tag, keep content
      (happens when token budget is too small for thinking + response)
    """
    # First remove all complete <think>...</think> blocks (non-greedy, including trailing whitespace)
    text = _THINK_PATTERN.sub('', text)
    # For any remaining unclosed <think> tags, just remove the <think> opening tag
    text = text.replace('<think>', '')
    return text.strip()

class ThinkingFilter:
    """Stateful filter to suppress <think> blocks during token streaming.
    
    Since <think>...</think> spans multiple tokens, we need to track whether
    we're currently inside a thinking block to suppress the enclosed tokens.
    If the think block is never closed (token budget exhausted), flush() will
    strip the opening <think> tag and release any remaining buffered content.
    """
    def __init__(self):
        self.buffer = ""
        self.in_think = False
        self.think_depth = 0
    
    def feed(self, token_text: str) -> str:
        """Feed a new token, return any non-thinking text to emit."""
        self.buffer += token_text
        output = ""
        i = 0
        while i < len(self.buffer):
            if not self.in_think:
                # Look for <think> opening tag
                tag_start = self.buffer.find('<think>', i)
                if tag_start == -1:
                    # No more think tags — emit everything safe
                    output += self.buffer[i:]
                    self.buffer = ""
                    break
                else:
                    # Emit text before the tag
                    output += self.buffer[i:tag_start]
                    self.in_think = True
                    self.think_depth = 1
                    i = tag_start + len('<think>')
            else:
                # We're inside a think block — look for </think> or nested <think>
                close_tag = self.buffer.find('</think>', i)
                open_tag = self.buffer.find('<think>', i)
                if close_tag == -1 and open_tag == -1:
                    # No tags at all — buffer the rest, emit nothing
                    self.buffer = self.buffer[i:] if i > 0 else self.buffer
                    break
                # Pick the nearest tag
                if open_tag != -1 and (close_tag == -1 or open_tag < close_tag):
                    # Nested <think>
                    self.think_depth += 1
                    i = open_tag + len('<think>')
                elif close_tag != -1:
                    self.think_depth -= 1
                    i = close_tag + len('</think>')
                    if self.think_depth == 0:
                        self.in_think = False
        return output
    
    def flush(self) -> str:
        """Flush any remaining buffer, stripping unclosed <think> tags."""
        if self.in_think:
            # Unclosed think block — just strip the <think> tag, keep content
            self.buffer = self.buffer.replace('<think>', '')
            self.in_think = False
            self.think_depth = 0
        result = self.buffer
        self.buffer = ""
        return result

def get_prefix_tokens(system_prompt, messages=None, tools=None):
    """Return token IDs for the invariant prefix: everything up to and including 
    <|im_start|>user\n. This prefix is identical across all requests with the same
    system prompt and tools, regardless of user message content.
    
    Args:
        system_prompt: The system prompt string
        messages: Optional full messages list (used when building cache, so we 
                  can match the same template structure)
        tools: Optional tools list to include in the template
    """
    if messages is None:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": ""}
        ]
    kwargs = {"tokenize": False, "add_generation_prompt": True}
    if tools:
        kwargs["tools"] = tools
    template = tokenizer.apply_chat_template(messages, **kwargs)
    tokens = tokenizer.encode(template)
    print(f"[DEBUG] Total tokens in template: {len(tokens)}")
    # Qwen: find <|im_start|>user\n marker — this is the invariant split point
    # Everything up to and including this marker is identical for all requests 
    # with the same system prompt (only user content varies after it)
    user_marker = tokenizer.encode("<|im_start|>user\n")
    try:
        for i in range(len(tokens) - len(user_marker) + 1):
            if tokens[i:i+len(user_marker)] == user_marker:
                return tokens[:i+len(user_marker)]
        # Fallback: return all tokens for safety
        print("[WARN] Could not find <|im_start|>user\\n marker in template")
        return tokens
    except Exception:
        return tokens

def find_user_marker_pos(tokens):
    """Find the position of <|im_start|>user\n in tokenized template.
    Returns the starting index, or -1 if not found."""
    user_marker = tokenizer.encode("<|im_start|>user\n")
    for i in range(len(tokens) - len(user_marker) + 1):
        if tokens[i:i+len(user_marker)] == user_marker:
            return i
    return -1

def get_system_prompt_cache(system_prompt, tools=None):
    """Get or create KV cache for system prompt prefix.
    
    NOTE: Caller must hold cache_lock!
    """
    # Compute hash of system prompt + tools (tools change the prefix in the template)
    cache_key = system_prompt + json.dumps(tools or [], sort_keys=True)
    hash_key = hashlib.sha256(cache_key.encode()).hexdigest()
    
    if hash_key in system_prompt_caches:
        print("Cache hit for system prompt (hash: {}...)".format(hash_key[:16]))
        return system_prompt_caches[hash_key]
    
    # Create new cache
    print("Creating new cache for system prompt (hash: {}...)".format(hash_key[:16]))
    if model is None:
        print("Warning: Model not loaded, cannot create cache")
        return None, 0
        
    # If caching is disabled, return None
    if MAX_CACHEABLE_TOKENS <= 0:
        return None, 0

    # Create cache
    prompt_cache = cache.make_prompt_cache(model)
    if draft_model is not None:
        prompt_cache += cache.make_prompt_cache(draft_model)
    
    # Get prefix tokens length (system prompt + tools up to <|user|> token)
    prefix_tokens = get_prefix_tokens(system_prompt, tools=tools)
    prefix_len = len(prefix_tokens) if prefix_tokens else 0
    print("Prefix length: {} tokens".format(prefix_len))
    
    # Check if prefix is too long to cache
    if prefix_len > MAX_CACHEABLE_TOKENS:
        print("Warning: Prefix too long ({} > {} tokens), caching only first {} tokens".format(prefix_len, MAX_CACHEABLE_TOKENS, MAX_CACHEABLE_TOKENS))
        prefix_len = MAX_CACHEABLE_TOKENS
    
    # Prefill cache with prefix tokens if we have any
    if prefix_len > 0 and prefix_tokens:
        # Use only the tokens we're going to cache (might be truncated to MAX_CACHEABLE_TOKENS)
        tokens_to_cache = prefix_tokens[:prefix_len]
        print(f"Prefilling cache with {len(tokens_to_cache)} tokens...")
        try:
            with mx.stream(mx.default_stream(mx.default_device())):
                # Convert to mx.array with batch dimension
                mx_tokens = mx.array([tokens_to_cache])
                # Run model to fill cache
                _ = model(mx_tokens, cache=prompt_cache)
            print(f"Cache prefilled successfully")
        except Exception as e:
            print(f"Warning: Failed to prefill cache: {e}")
            # Continue with empty cache - it will be filled during generation
    
    # Enforce cache limit
    if len(system_prompt_caches) >= MAX_CACHES:
        # Remove the oldest cache (first key)
        oldest_key = next(iter(system_prompt_caches))
        del system_prompt_caches[oldest_key]
        print(f"Evicted oldest cache (hash: {oldest_key[:16]}...) to maintain limit of {MAX_CACHES}")
    
    # Store cache (now prefilled)
    system_prompt_caches[hash_key] = (prompt_cache, prefix_len)
    print(f"Cache stored: hash={hash_key[:16]}..., prefix_len={prefix_len}, cache_dict_size={len(system_prompt_caches)}")
    return prompt_cache, prefix_len

def format_qwen_prompt(user_message: str, system_message: Optional[str] = None) -> str:
    """Format prompt for Qwen3.5 model using the Qwen chat template."""
    if tokenizer is None:
        raise ValueError("Tokenizer not loaded")
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": user_message})
    
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

def format_messages(messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> str:
    """Format messages using the Qwen chat template. Passes tools if provided."""
    if tokenizer is None:
        raise ValueError("Tokenizer not loaded")
    
    kwargs: Dict[str, Any] = {"tokenize": False, "add_generation_prompt": True}
    if tools:
        kwargs["tools"] = tools
    
    return tokenizer.apply_chat_template(messages, **kwargs)

def parse_tool_calls(text: str):
    """Parse <tool_call> blocks from model output.
    Returns (clean_content, tool_calls_list or None).
    
    Supports two formats:
    1. Qwen3.5 XML format:
       <tool_call>
       <function=function_name>
       <parameter=param1>value1</parameter>
       <parameter=param2>multi\nline\nvalue</parameter>
       </function>
       </tool_call>
    
    2. Legacy JSON format (Qwen3-8B):
       <tool_call>
       {"name": "...", "arguments": {...}}
       </tool_call>
    """
    tool_call_pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
    matches = list(re.finditer(tool_call_pattern, text, re.DOTALL))
    
    if not matches:
        return text, None
    
    tool_calls = []
    for match in matches:
        block = match.group(1).strip()
        
        # Try Qwen3.5 XML format first: <function=NAME>...</function>
        func_pattern = r'<function=([^>]+)>\s*(.*?)\s*</function>'
        func_matches = list(re.finditer(func_pattern, block, re.DOTALL))
        
        if func_matches:
            for func_match in func_matches:
                func_name = func_match.group(1).strip()
                func_body = func_match.group(2)
                
                param_pattern = r'<parameter=([^>]+)>\s*(.*?)\s*</parameter>'
                param_matches = list(re.finditer(param_pattern, func_body, re.DOTALL))
                
                arguments = {}
                for param_match in param_matches:
                    param_name = param_match.group(1).strip()
                    param_value = param_match.group(2).strip()
                    arguments[param_name] = param_value
                
                tool_call = {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(arguments)
                    }
                }
                tool_calls.append(tool_call)
        else:
            # Fall back to legacy JSON format
            try:
                tool_data = json.loads(block)
                tool_call = {
                    "id": f"call_{uuid.uuid4().hex[:8]}",
                    "type": "function",
                    "function": {
                        "name": tool_data.get("name", ""),
                        "arguments": json.dumps(tool_data.get("arguments", {}))
                    }
                }
                tool_calls.append(tool_call)
            except (json.JSONDecodeError, Exception):
                pass
    
    if not tool_calls:
        return text, None
    
    # Remove tool call blocks from text
    clean_text = re.sub(tool_call_pattern, '', text, flags=re.DOTALL).strip()
    
    return clean_text if clean_text else None, tool_calls

def can_use_system_cache(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Check if we can use system prompt caching.
    Returns the system prompt if cacheable, None otherwise.
    
    Conditions for caching:
    1. First message is a system message
    2. No other system messages
    3. At least one user message after system
    
    (Assistant messages are fine — the cached prefix is just system+user-header,
    which is identical across all turns.)
    """
    if not messages:
        return None
    
    # Check if first message is system
    if messages[0]["role"] != "system":
        return None
    
    system_prompt = messages[0]["content"]
    print(f"[DEBUG] System prompt length: {len(system_prompt)} chars, hash: {hashlib.sha256(system_prompt.encode()).hexdigest()[:16]}")
    
    # Check for other system messages
    for msg in messages[1:]:
        if msg["role"] == "system":
            return None
    
    # Must have at least one user message
    has_user = any(msg["role"] == "user" for msg in messages[1:])
    if not has_user:
        return None
    
    return system_prompt

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup and clean up on shutdown."""
    global model, tokenizer, draft_model
    
    # Load model on startup
    print(f"Loading {MODEL_NAME} model from {MODEL_PATH}...")
    start_time = time.time()
    
    try:
        model, tokenizer = mlx_lm.load(MODEL_PATH, lazy=True)
        load_time = time.time() - start_time
        print(f"✓ Model loaded successfully in {load_time:.2f} seconds")
        
        # Load draft model for speculative decoding
        if DRAFT_MODEL_PATH:
            print(f"Loading draft model: {DRAFT_MODEL_PATH}...")
            draft_start = time.time()
            try:
                draft_model, draft_tokenizer = mlx_lm.load(DRAFT_MODEL_PATH)
                draft_load_time = time.time() - draft_start
                # Verify tokenizer compatibility
                if draft_tokenizer.vocab_size != tokenizer.vocab_size:
                    print(f"⚠ Draft model tokenizer vocab mismatch (draft={draft_tokenizer.vocab_size}, main={tokenizer.vocab_size}) — disabling speculative decoding")
                    draft_model = None
                else:
                    print(f"✓ Draft model loaded in {draft_load_time:.2f}s (num_draft_tokens={NUM_DRAFT_TOKENS})")
            except Exception as e:
                print(f"⚠ Could not load draft model ({e}) — continuing without speculative decoding")
                draft_model = None
        
        # Set metal wired memory limit to 2GB — reduces OS paging latency
        # Benchmark-verified: consistent 1.003-1.010x speedup across prompt lengths
        # Only config that never regresses (wired_2gb wins on medium+long, competitive on short)
        try:
            mx.set_wired_limit(2 * 1024**3)
            print("✓ Metal wired memory limit set to 2GB (benchmark-verified optimization)")
        except Exception as e:
            print(f"⚠ Could not set wired memory limit: {e}")
        
        # Warm-up: Trigger JIT compilation for both prefill AND decode paths
        # Using a realistic ~300 token prompt ensures prefill path is compiled too
        print("Warming up model (JIT compilation for prefill + decode)...")
        warmup_start = time.time()
        try:
            # Build a realistic-sized warmup prompt (~300 tokens) to compile prefill
            warmup_text = "You are a helpful assistant. Be concise.\n\n" + (
                "This is a warmup prompt designed to exercise the prefill path. " * 20
            )
            warmup_result = mlx_lm.generate(
                model, tokenizer, 
                warmup_text,
                max_tokens=5,  # Also compile the decode path
                verbose=False,
                prefill_step_size=PREFILL_STEP_SIZE,
                kv_bits=KV_BITS,
                max_kv_size=MAX_KV_SIZE
            )
            warmup_time = time.time() - warmup_start
            print(f"✓ Warm-up completed in {warmup_time:.2f}s (prefill + decode JIT-compiled)")
            
            # Prefill system prompt cache for faster CLI requests
            print("Prefilling system prompt cache for CLI agent...")
            try:
                # Load condensed system prompt from file
                condensed_prompt_path = "cli_system_prompt.txt"
                import os
                if os.path.exists(condensed_prompt_path):
                    with open(condensed_prompt_path, "r", encoding="utf-8") as f:
                        raw_prompt = f.read().strip()
                    # Format with current date (same as client does)
                    from datetime import datetime
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    current_year = datetime.now().strftime("%Y")
                    system_prompt = raw_prompt.format(current_date=current_date, current_year=current_year)
                    # Use the same cache creation path as runtime requests (no tools for this pre-warm)
                    with cache_lock:
                        prompt_cache, prefix_len = get_system_prompt_cache(system_prompt, tools=None)
                    print(f"System prompt cache ready (prefix_len={prefix_len})")
                    
                    # Warm-up: compile the exact code path real requests use
                    # (full prompt string + cache, same as the /chat/completions endpoint)
                    print("Warming up cache-aware request path (same as live requests)...")
                    try:
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": "OK"}
                        ]
                        full_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                        _ = mlx_lm.generate(
                            model, tokenizer, full_prompt,  # Full string prompt — exactly like live requests
                            max_tokens=3, verbose=False,
                            prefill_step_size=PREFILL_STEP_SIZE,
                            prompt_cache=prompt_cache,
                            kv_bits=KV_BITS,
                            max_kv_size=MAX_KV_SIZE
                        )
                        # Trim cache back to original prefix
                        full_tokens = tokenizer.encode(full_prompt)
                        total_tokens = len(full_tokens) + 3
                        added_tokens = max(0, total_tokens - prefix_len)
                        if added_tokens > 0:
                            from mlx_lm.models import cache as cache_module
                            cache_module.trim_prompt_cache(prompt_cache, added_tokens)
                        print("✓ Cache-aware request path compiled (full-prompt + cache pattern)")
                    except Exception as e:
                        print(f"⚠ Cache-aware warm-up skipped (non-critical): {e}")
                else:
                    print("⚠ Condensed prompt file not found, skipping cache prefill")
            except Exception as e:
                print(f"⚠ System prompt cache prefill failed (non-critical): {e}")
        except Exception as warmup_error:
            print(f"⚠ Warm-up failed (non-critical): {warmup_error}")
            print(f"  (First request may be slower)")
        
        print(f"Model ready on http://{HOST}:{PORT}")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
        raise
    
    yield
    
    # Cleanup on shutdown
    print("Shutting down server...")
    # Note: MLX models don't typically need explicit cleanup

# Request/Response models
class GenerationRequest(BaseModel):
    """Request model for generation."""
    prompt: str = Field(..., description="User prompt/message")
    system_prompt: Optional[str] = Field(None, description="Optional system instruction")
    max_tokens: int = Field(200, ge=1, le=2048, description="Maximum tokens to generate")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature for sampling")
    stream: bool = Field(False, description="Whether to stream the response")

class ChatMessage(BaseModel):
    """Chat message for conversation."""
    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: Optional[str] = Field(None, description="Message content (optional if tool_calls present)")
    tool_calls: Optional[List[Dict[str, Any]]] = Field(None, description="Tool calls from assistant")
    tool_call_id: Optional[str] = Field(None, description="Tool call ID for tool responses")

class ChatRequest(BaseModel):
    """Request model for chat completion."""
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    max_tokens: int = Field(200, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    stream: bool = Field(False)
    tools: Optional[List[Dict[str, Any]]] = Field(None, description="Available tools for function calling")
    tool_choice: Optional[Any] = Field(None, description="Tool choice: 'auto', 'none', or specific tool")

class GenerationResponse(BaseModel):
    """Response model for generation."""
    text: str = Field(..., description="Generated text")
    created_at: str = Field(..., description="ISO timestamp")
    model: str = Field(MODEL_NAME, description="Model name")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")

# Create FastAPI app
app = FastAPI(
    title=f"{MODEL_NAME} Server",
    description=f"Local server for {MODEL_NAME} model with streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "message": f"{MODEL_NAME} Server",
        "status": "running",
        "endpoints": {
            "GET /": "This info page",
            "GET /health": "Health check",
            "GET /model": "Model info",
            "POST /generate": "Generate text (non-streaming)",
            "POST /generate/stream": "Generate text (streaming)",
            "POST /chat/completions": "Chat completions (OpenAI-compatible)",
        },
        "docs": f"http://{HOST}:{PORT}/docs"
    }

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@app.get("/model")
async def model_info():
    """Get model information."""
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "model": MODEL_NAME,
        "format": "MLX 4-bit quantized",
        "path": MODEL_PATH,
        "status": "loaded",
        "parameters": "4B",
        "context_window": "128K tokens",
        "loaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@app.get("/cache_stats")
async def cache_stats():
    """Get cache statistics."""
    with cache_lock:
        cache_size = len(system_prompt_caches)
        cache_keys = list(system_prompt_caches.keys())
    
    return {
        "cache_enabled": True,
        "cache_size": cache_size,
        "cache_keys": [k[:16] + "..." for k in cache_keys],  # Truncate hashes
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

@app.post("/generate")
async def generate(request: GenerationRequest):
    """Generate text (non-streaming)."""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Format prompt
    if request.system_prompt:
        formatted_prompt = format_qwen_prompt(request.prompt, request.system_prompt)
    else:
        formatted_prompt = format_qwen_prompt(request.prompt)
    
    # Generate response
    start_time = time.time()
    
    # Use KV cache if system prompt is provided
    prompt_cache = None
    prefix_len = 0
    if request.system_prompt:
        with cache_lock:
            prompt_cache, prefix_len = get_system_prompt_cache(request.system_prompt)
    
    # Note: mlx_lm.generate doesn't accept temperature in current version
    # We'll use default parameters for now
    response_text = mlx_lm.generate(
        model,
        tokenizer,
        formatted_prompt,
        max_tokens=request.max_tokens,
        verbose=False,
        prefill_step_size=PREFILL_STEP_SIZE,
        prompt_cache=prompt_cache if prompt_cache else None,
        kv_bits=KV_BITS,
        max_kv_size=MAX_KV_SIZE,
        draft_model=draft_model,
        num_draft_tokens=NUM_DRAFT_TOKENS
    )
    
    # Remove prompt from response
    if response_text.startswith(formatted_prompt):
        response_text = response_text[len(formatted_prompt):]
    
    generation_time = time.time() - start_time
    
    # Trim cache back to prefix length if used
    if prompt_cache:
        # Determine how many tokens were added after prefix
        # Approximate: total input tokens + output tokens
        total_tokens = len(tokenizer.encode(formatted_prompt)) + len(tokenizer.encode(response_text))
        added_tokens = total_tokens - prefix_len
        print(f"Cache trimming (generate): prefix_len={prefix_len}, total_tokens={total_tokens}, added_tokens={added_tokens}")
        if added_tokens > 0:
            cache.trim_prompt_cache(prompt_cache, added_tokens)
            print(f"Cache trimmed (generate), remaining cache size approx {prefix_len} tokens")
    
    # Calculate token counts (mlx_lm.generate returns only generated tokens, not prompt)
    input_tokens = len(tokenizer.encode(formatted_prompt))
    output_tokens = len(tokenizer.encode(response_text))
    
    return GenerationResponse(
        text=strip_thinking(response_text.strip()),
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        model="Qwen3.5-9B-MLX",
        usage={
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "generation_time_ms": int(generation_time * 1000)
        }
    )

async def generate_stream_generator(prompt: str, max_tokens: int):
    """Generator function for streaming responses using mlx_lm.stream_generate."""
    if model is None or tokenizer is None:
        yield "data: {\"error\": \"Model not loaded\"}\n\n"
        return
    
    start_time = time.time()
    accumulated_text = ""
    last_response = None
    think_filter = ThinkingFilter()
    
    try:
        # Get streaming generator
        stream = mlx_lm.stream_generate(
            model,
            tokenizer,
            prompt,
            max_tokens=max_tokens,
            prefill_step_size=PREFILL_STEP_SIZE,
            kv_bits=KV_BITS,
            max_kv_size=MAX_KV_SIZE,
            draft_model=draft_model,
            num_draft_tokens=NUM_DRAFT_TOKENS
        )
        
        # Process streaming responses
        for response in stream:
            # response.text contains the new text for this token
            raw_text = response.text
            # Filter out thinking blocks from the token stream
            clean_text = think_filter.feed(raw_text)
            accumulated_text += clean_text
            last_response = response
            
            # Send SSE event with the filtered text
            data = {
                "text": clean_text,
                "accumulated": accumulated_text,
                "finished": False,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            yield f"data: {json.dumps(data)}\n\n"
            
            # Check if generation is complete
            if response.finish_reason is not None:
                break
        
        # Final completion event — flush any remaining buffered text
        flush_text = think_filter.flush()
        if flush_text:
            accumulated_text += flush_text
        total_time = time.time() - start_time
        finish_reason = "completed"
        if last_response and hasattr(last_response, 'finish_reason') and last_response.finish_reason:
            finish_reason = last_response.finish_reason
        
        final_data = {
            "text": flush_text,
            "accumulated": accumulated_text,
            "finished": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total_time": round(total_time, 3),
            "finish_reason": finish_reason
        }
        yield f"data: {json.dumps(final_data)}\n\n"
        
    except Exception as e:
        # Error event
        error_data = {
            "error": str(e),
            "finished": True,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        yield f"data: {json.dumps(error_data)}\n\n"

async def generate_openai_stream_generator(prompt: str, max_tokens: int, request_id: str = None, model_name: str = "Qwen3.5-9B-MLX", prompt_cache=None, prefix_len=0):
    """Generator function for OpenAI-compatible streaming responses.
    
    When prompt_cache is provided with prefix_len > 0, the cached KV states
    cover the first prefix_len tokens (system prompt + user tag). We slice the
    prompt to only pass the UNCACHED suffix to mlx_lm.stream_generate, avoiding
    redundant prefill of the system prompt on every request.
    """
    if model is None or tokenizer is None:
        # Return OpenAI-style error
        error_chunk = {
            "id": request_id or f"chatcmpl-{int(time.time())}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {"content": ""},
                "finish_reason": "error"
            }],
            "error": "Model not loaded"
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        return
    
    start_time = time.time()
    accumulated_text = ""
    last_response = None
    think_filter = ThinkingFilter()
    
    # Generate request ID if not provided
    if not request_id:
        request_id = f"chatcmpl-{int(time.time())}"
    
    # Determine the actual prompt to pass to the model
    # If we have a valid cache, slice to only uncached tokens
    model_prompt = prompt  # default: full string prompt
    try:
        if prompt_cache is not None and prefix_len > 0:
            # Tokenize the full prompt and slice off the cached prefix
            full_tokens = tokenizer.encode(prompt)
            user_pos = find_user_marker_pos(full_tokens)
            if user_pos >= 0:
                user_marker = tokenizer.encode("<|im_start|>user\n")
                suffix_start = user_pos + len(user_marker)
                suffix_tokens = full_tokens[suffix_start:]
                model_prompt = mx.array(suffix_tokens)
                print(f"[DEBUG] Cache active: prefix_len={prefix_len}, full={len(full_tokens)} tokens, "
                      f"user_marker at pos={user_pos}, suffix={len(suffix_tokens)} tokens -> skipping prefill")
            else:
                print(f"[DEBUG] Cache present but user marker not found in prompt — falling back to full prefill")
    except Exception as e:
        print(f"[DEBUG] Cache slicing failed ({e}), falling back to full prefill")
    
    try:
        print(f"[DEBUG] generate_openai_stream_generator: prompt_cache={'present' if prompt_cache else None}, prefix_len={prefix_len}")
        # Get streaming generator — pass sliced tokens when cache is active
        stream = mlx_lm.stream_generate(
            model,
            tokenizer,
            model_prompt,
            max_tokens=max_tokens,
            prefill_step_size=PREFILL_STEP_SIZE,
            kv_bits=KV_BITS,
            max_kv_size=MAX_KV_SIZE,
            prompt_cache=prompt_cache if prompt_cache else None,
            draft_model=draft_model,
            num_draft_tokens=NUM_DRAFT_TOKENS
        )
        
        # Process streaming responses
        first_token_time = None
        for response in stream:
            raw_text = response.text
            # Filter out thinking blocks from the token stream
            clean_text = think_filter.feed(raw_text)
            if first_token_time is None:
                first_token_time = time.time() - start_time
                print(f"[DEBUG] First token after {first_token_time:.3f}s, prefix_len={prefix_len}, cache={'present' if prompt_cache else 'None'}")
            accumulated_text += clean_text
            last_response = response
            
            # Create OpenAI-compatible chunk (skip empty deltas from filtered thinking)
            if clean_text:
                chunk = {
                    "id": request_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model_name,
                    "choices": [{
                        "index": 0,
                        "delta": {
                            "content": clean_text
                        },
                        "finish_reason": None
                    }]
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            
            # Check if generation is complete
            if response.finish_reason is not None:
                break
        
        # Final completion chunk — flush any remaining buffered text first
        flush_text = think_filter.flush()
        if flush_text:
            accumulated_text += flush_text
        total_time = time.time() - start_time
        finish_reason = "stop"
        if last_response and hasattr(last_response, 'finish_reason') and last_response.finish_reason:
            # Map finish reasons
            if last_response.finish_reason == "length":
                finish_reason = "length"
            elif last_response.finish_reason == "stop":
                finish_reason = "stop"
            else:
                finish_reason = last_response.finish_reason
        
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": finish_reason
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        # Trim cache back to prefix length if used
        if prompt_cache and prefix_len > 0:
            # Determine how many tokens were added after prefix
            total_tokens = len(tokenizer.encode(prompt)) + len(tokenizer.encode(accumulated_text))
            added_tokens = total_tokens - prefix_len
            if added_tokens > 0:
                cache.trim_prompt_cache(prompt_cache, added_tokens)
        
    except Exception as e:
        # Error chunk
        error_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model_name,
            "choices": [{
                "index": 0,
                "delta": {"content": ""},
                "finish_reason": "error"
            }],
            "error": str(e)
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
@app.post("/generate/stream")
async def generate_stream(request: GenerationRequest):
    """Generate text with streaming response (Server-Sent Events)."""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Format prompt
    if request.system_prompt:
        formatted_prompt = format_qwen_prompt(request.prompt, request.system_prompt)
    else:
        formatted_prompt = format_qwen_prompt(request.prompt)
    
    return StreamingResponse(
        generate_stream_generator(formatted_prompt, request.max_tokens),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )

@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Convert messages to list of dicts for tokenizer (include tool_calls and tool_call_id if present)
    messages = []
    for m in request.messages:
        msg_dict = {"role": m.role}
        if m.content is not None:
            msg_dict["content"] = m.content
        if m.tool_calls:
            # Qwen3.5 chat template expects arguments as a dict (not JSON string).
            # Convert OpenAI-format JSON-string arguments to dict for Jinja |items filter.
            tc_list = []
            for tc in m.tool_calls:
                tc_copy = dict(tc)
                fn = tc_copy.get("function", {})
                if isinstance(fn.get("arguments"), str):
                    try:
                        fn["arguments"] = json.loads(fn["arguments"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                tc_copy["function"] = fn
                tc_list.append(tc_copy)
            msg_dict["tool_calls"] = tc_list
        if m.tool_call_id:
            msg_dict["tool_call_id"] = m.tool_call_id
        messages.append(msg_dict)
    
    # Extract tools
    tools = request.tools
    
    # Ensure there's at least one user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user messages found")
    
    # Format prompt using Qwen chat template (pass tools if provided)
    formatted_prompt = format_messages(messages, tools=tools)
    
    # Handle streaming vs non-streaming
    if request.stream:
        # Check if we can use system prompt caching
        system_prompt = can_use_system_cache(messages)
        print(f"Cache check: system_prompt={'present' if system_prompt else 'None'}, messages count={len(messages)}, tools={'present' if tools else 'none'}")
        prompt_cache = None
        prefix_len = 0
        
        if system_prompt:
            try:
                with cache_lock:
                    prompt_cache, prefix_len = get_system_prompt_cache(system_prompt, tools)
            except Exception as e:
                print(f"Warning: Failed to get system prompt cache: {e}")
                prompt_cache = None
        
        # Generate request ID consistent with non-streaming format
        request_id = f"chatcmpl-{int(time.time())}"
        return StreamingResponse(
            generate_openai_stream_generator(
                formatted_prompt, 
                request.max_tokens,
                request_id=request_id,
                model_name=MODEL_NAME,
                prompt_cache=prompt_cache,
                prefix_len=prefix_len
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-transform",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",  # Disable nginx buffering
                "Content-Encoding": "identity"  # Prevent gzip buffering
            }
        )
    else:
        # Check if we can use system prompt caching
        system_prompt = can_use_system_cache(messages)
        print(f"Cache check: system_prompt={'present' if system_prompt else 'None'}, messages count={len(messages)}, tools={'present' if tools else 'none'}")
        prompt_cache = None
        prefix_len = 0
        
        if system_prompt:
            try:
                with cache_lock:
                    prompt_cache, prefix_len = get_system_prompt_cache(system_prompt, tools)
            except Exception as e:
                print(f"Warning: Failed to get system prompt cache: {e}")
                prompt_cache = None
        
        # Generate response — slice prompt to only uncached tokens when cache is active
        print(f"Generation: cache={'present' if prompt_cache else 'None'}, prefix_len={prefix_len}")
        start_gen_time = time.time()
        
        # Determine model prompt (slice if cache is active)
        model_prompt = formatted_prompt
        if prompt_cache is not None and prefix_len > 0:
            try:
                full_tokens = tokenizer.encode(formatted_prompt)
                user_pos = find_user_marker_pos(full_tokens)
                if user_pos >= 0:
                    user_marker = tokenizer.encode("<|im_start|>user\n")
                    suffix_start = user_pos + len(user_marker)
                    suffix_tokens = full_tokens[suffix_start:]
                    model_prompt = mx.array(suffix_tokens)
                    print(f"[DEBUG] Non-streaming cache active: prefix_len={prefix_len}, full={len(full_tokens)}, "
                          f"suffix={len(suffix_tokens)} tokens -> skipping prefill")
            except Exception as e:
                print(f"[DEBUG] Non-streaming cache slicing failed ({e}), falling back to full prefill")
        
        response_text = mlx_lm.generate(
            model,
            tokenizer,
            model_prompt,
            max_tokens=request.max_tokens,
            verbose=False,
            prefill_step_size=PREFILL_STEP_SIZE,
            prompt_cache=prompt_cache if prompt_cache else None,
            kv_bits=KV_BITS,
            max_kv_size=MAX_KV_SIZE,
            draft_model=draft_model,
            num_draft_tokens=NUM_DRAFT_TOKENS
        )
        gen_time = time.time() - start_gen_time
        print(f"Generation time: {gen_time:.2f}s")
        
        # Remove prompt from response
        if response_text.startswith(formatted_prompt):
            response_text = response_text[len(formatted_prompt):]
        
        response_text = strip_thinking(response_text.strip())
        
        # Parse tool calls from model output
        clean_content, tool_calls = parse_tool_calls(response_text)
        
        # Build assistant message (with tool_calls if parsed)
        assistant_message: Dict[str, Any] = {"role": "assistant"}
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
            assistant_message["content"] = clean_content  # may be None
            finish_reason = "tool_calls"
        else:
            assistant_message["content"] = response_text if response_text else ""
            finish_reason = "stop"
        
        # Trim cache back to prefix length if used
        display_text = response_text  # use full text for token counting
        if prompt_cache:
            total_tokens = len(tokenizer.encode(formatted_prompt)) + len(tokenizer.encode(display_text))
            added_tokens = total_tokens - prefix_len
            print(f"Cache trimming: prefix_len={prefix_len}, total_tokens={total_tokens}, added_tokens={added_tokens}")
            if added_tokens > 0:
                cache.trim_prompt_cache(prompt_cache, added_tokens)
                print(f"Cache trimmed, remaining cache size approx {prefix_len} tokens")
        
        # Calculate token counts
        input_tokens = len(tokenizer.encode(formatted_prompt))
        output_tokens = len(tokenizer.encode(display_text))
        
        # Override finish_reason if max_tokens reached
        if output_tokens >= request.max_tokens:
            finish_reason = "length"
        
        # Return OpenAI-compatible response
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": MODEL_NAME,
            "choices": [{
                "index": 0,
                "message": assistant_message,
                "finish_reason": finish_reason
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "generation_time_ms": int(gen_time * 1000)
            }
        }

@app.get("/v1/models")
async def v1_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen3.5-9b-mlx",
                "object": "model",
                "created": 0,
                "owned_by": "local"
            }
        ]
    }
if __name__ == "__main__":
    import uvicorn
    import argparse
    
    parser = argparse.ArgumentParser(description=f"{MODEL_NAME} Local Server")
    parser.add_argument("--model-path", type=str, default=MODEL_PATH,
                        help=f"Model path (default: {MODEL_PATH})")
    parser.add_argument("--host", type=str, default=HOST, help=f"Host to bind (default: {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Port to bind (default: {PORT})")
    parser.add_argument("--draft-model", type=str, default=DRAFT_MODEL_PATH,
                        help="Draft model for speculative decoding (default: disabled)")
    parser.add_argument("--num-draft-tokens", type=int, default=NUM_DRAFT_TOKENS,
                        help="Number of draft tokens (default: 3)")
    parser.add_argument("--no-draft", action="store_true",
                        help="Disable speculative decoding entirely")
    parser.add_argument("--kv-bits", type=int, default=KV_BITS,
                        help="KV cache quantization bits (8=good speed/quality, 4=aggressive, None=off)")
    args = parser.parse_args()
    
    MODEL_PATH = args.model_path
    HOST = args.host
    PORT = args.port
    KV_BITS = args.kv_bits if args.kv_bits else None
    if args.no_draft:
        DRAFT_MODEL_PATH = None
        NUM_DRAFT_TOKENS = 3
    else:
        DRAFT_MODEL_PATH = args.draft_model
        NUM_DRAFT_TOKENS = args.num_draft_tokens
    
    print(f"Starting {MODEL_NAME} server on http://{HOST}:{PORT}")
    print(f"KV cache quantization: {KV_BITS}-bit" if KV_BITS else "KV cache quantization: off")
    if DRAFT_MODEL_PATH:
        print(f"Speculative decoding: draft_model={DRAFT_MODEL_PATH}, num_draft_tokens={NUM_DRAFT_TOKENS}")
    else:
        print(f"Speculative decoding: disabled")
    print(f"API documentation: http://{HOST}:{PORT}/docs")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
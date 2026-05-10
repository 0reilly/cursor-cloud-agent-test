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
import hashlib, os
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Configuration
MODEL_PATH = "/Users/adamoreilly/model/models/qwen3.5-9b-mlx"
HOST = "0.0.0.0"
PORT = int(os.environ.get('PORT', 8000))
MAX_CACHEABLE_TOKENS = 400  # Limit cache to 400 tokens (fits condensed prompt)
PREFILL_STEP_SIZE = 8192  # Default mlx_lm value (faster prefill)
KV_BITS = None  # Disable quantization (RotatingKVCache Quantization NYI)
MAX_KV_SIZE = 512  # Limit total KV cache to 512 tokens (prevent OOM)
ENABLE_PREFILL = True  # Can be disabled if memory issues persist
MAX_CACHES = 3  # Maximum number of system prompt caches to keep (prevent OOM)

# Global model and tokenizer
model = None
tokenizer = None

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

def get_prefix_tokens(system_prompt):
    """Return token IDs for prefix up to and including <|im_start|>assistant\n marker."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": ""}
    ]
    template = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    tokens = tokenizer.encode(template)
    print(f"[DEBUG] Total tokens in template: {len(tokens)}")
    # Qwen: find <|im_start|>assistant\n marker for prefix split
    assistant_marker = tokenizer.encode("<|im_start|>assistant\n")
    try:
        for i in range(len(tokens) - len(assistant_marker) + 1):
            if tokens[i:i+len(assistant_marker)] == assistant_marker:
                return tokens[:i+len(assistant_marker)]
        return tokens
    except Exception:
        return tokens

def get_system_prompt_cache(system_prompt):
    """Get or create KV cache for system prompt prefix.
    
    NOTE: Caller must hold cache_lock!
    """
    # Compute hash of system prompt
    hash_key = hashlib.sha256(system_prompt.encode()).hexdigest()
    
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
    
    # Get prefix tokens length (system prompt up to <|user|> token)
    prefix_tokens = get_prefix_tokens(system_prompt)
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

def format_messages(messages: List[Dict[str, str]]) -> str:
    """Format messages using the Qwen chat template."""
    if tokenizer is None:
        raise ValueError("Tokenizer not loaded")
    
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

def can_use_system_cache(messages: List[Dict[str, str]]) -> Optional[str]:
    """
    Check if we can use system prompt caching.
    Returns the system prompt if cacheable, None otherwise.
    
    Conditions for caching:
    1. First message is a system message
    2. No other system messages
    3. At least one user message after system
    4. No assistant messages in the prompt (only system -> user chain)
    """
    if not messages:
        return None
    
    # Check if first message is system
    if messages[0]["role"] != "system":
        return None
    
    system_prompt = messages[0]["content"]
    import hashlib
    print(f"[DEBUG] System prompt length: {len(system_prompt)} chars, hash: {hashlib.sha256(system_prompt.encode()).hexdigest()[:16]}")
    
    # Check for other system messages
    for msg in messages[1:]:
        if msg["role"] == "system":
            return None
    
    # Check for assistant messages (if any assistant in prompt, can't cache)
    for msg in messages[1:]:
        if msg["role"] == "assistant":
            return None
    
    # Must have at least one user message
    has_user = any(msg["role"] == "user" for msg in messages[1:])
    if not has_user:
        return None
    
    return system_prompt

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup and clean up on shutdown."""
    global model, tokenizer
    
    # Load model on startup
    print("Loading Qwen3.5-9B-MLX model...")
    start_time = time.time()
    
    try:
        model, tokenizer = mlx_lm.load(MODEL_PATH, lazy=True)
        load_time = time.time() - start_time
        print(f"✓ Model loaded successfully in {load_time:.2f} seconds")
        
        # Set metal wired memory limit to 2GB — reduces OS paging latency
        # Benchmark-verified: consistent 1.003-1.010x speedup across prompt lengths
        # Only config that never regresses (wired_2gb wins on medium+long, competitive on short)
        try:
            mx.set_wired_limit(2 * 1024**3)
            print("✓ Metal wired memory limit set to 2GB (benchmark-verified optimization)")
        except Exception as e:
            print(f"⚠ Could not set wired memory limit: {e}")
        
        # Warm-up: Trigger JIT compilation to make first request faster
        print("Warming up model (triggering JIT compilation)...")
        warmup_start = time.time()
        try:
            # Do a small generation to compile the model
            warmup_result = mlx_lm.generate(
                model, tokenizer, 
                "Hello",  # Short prompt
                max_tokens=2,  # Minimal generation
                verbose=False,
                prefill_step_size=PREFILL_STEP_SIZE,
                kv_bits=KV_BITS,
                max_kv_size=MAX_KV_SIZE
            )
            warmup_time = time.time() - warmup_start
            print(f"✓ Warm-up completed in {warmup_time:.2f} seconds")
            print(f"  (First user request will be faster due to JIT compilation)")
            
            # Prefill system prompt cache for faster CLI requests
            print("Prefilling system prompt cache for CLI agent...")
            try:
                # Load condensed system prompt from file
                condensed_prompt_path = "cli_system_prompt_condensed_raw.txt"
                import os
                if os.path.exists(condensed_prompt_path):
                    with open(condensed_prompt_path, "r", encoding="utf-8") as f:
                        raw_prompt = f.read().strip()
                    # Format with current date (same as client does)
                    from datetime import datetime
                    current_date = datetime.now().strftime("%Y-%m-%d")
                    current_year = datetime.now().strftime("%Y")
                    system_prompt = raw_prompt.format(current_date=current_date, current_year=current_year)
                    import hashlib
                    hash_key = hashlib.sha256(system_prompt.encode()).hexdigest()
                    # Create and prefill cache (same logic as get_system_prompt_cache)
                    from mlx_lm.models import cache
                    import mlx.core as mx
                    prompt_cache = cache.make_prompt_cache(model)
                    # Get prefix tokens (system prompt up to generation prompt marker)
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": ""}
                    ]
                    template = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True
                    )
                    tokens = tokenizer.encode(template)
                    # Qwen template: ...<|im_start|>assistant\n is the generation prompt
                    # Find <|im_start|>assistant marker to split prefix
                    assistant_marker = tokenizer.encode("<|im_start|>assistant\n")
                    try:
                        # Find the subsequence in tokens
                        for i in range(len(tokens) - len(assistant_marker) + 1):
                            if tokens[i:i+len(assistant_marker)] == assistant_marker:
                                idx = i + len(assistant_marker) - 1
                                prefix_tokens = tokens[:idx+1]
                                break
                        else:
                            prefix_tokens = tokens
                    except Exception:
                        prefix_tokens = tokens
                    prefix_len = len(prefix_tokens)
                    print(f"Prefix length: {prefix_len} tokens")
                    # Prefill cache with prefix tokens
                    with mx.stream(mx.default_stream(mx.default_device())):
                        mx_tokens = mx.array([prefix_tokens])
                        _ = model(mx_tokens, cache=prompt_cache)
                    print(f"Cache prefilled with {prefix_len} tokens")
                    # Store in global cache dict
                    import threading
                    with cache_lock:
                        system_prompt_caches[hash_key] = (prompt_cache, prefix_len)
                    print(f"System prompt cache ready (hash: {hash_key[:16]}...)")
                    
                    # Warm-up generation step to compile kernels for autoregressive generation
                    # Skipped due to memory constraints - will be compiled on first request
                    try:
                        pass  # Generation warm-up skipped to conserve memory
                    except Exception as e:
                        print(f"⚠ Generation warm-up skipped: {e}")
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
    content: str = Field(..., description="Message content")

class ChatRequest(BaseModel):
    """Request model for chat completion."""
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    max_tokens: int = Field(200, ge=1, le=2048)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    stream: bool = Field(False)

class GenerationResponse(BaseModel):
    """Response model for generation."""
    text: str = Field(..., description="Generated text")
    created_at: str = Field(..., description="ISO timestamp")
    model: str = Field("Qwen3.5-9B-MLX", description="Model name")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")

# Create FastAPI app
app = FastAPI(
    title="Qwen3.5-9B-MLX Server",
    description="Local server for Qwen3.5-9B-MLX model with streaming",
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
        "message": "Qwen3.5-9B-MLX Server",
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
        "model": "Qwen3.5-9B-MLX",
        "format": "MLX 4-bit quantized",
        "path": MODEL_PATH,
        "status": "loaded",
        "parameters": "9B",
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
        max_kv_size=MAX_KV_SIZE
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
            max_kv_size=MAX_KV_SIZE
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
    """Generator function for OpenAI-compatible streaming responses."""
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
    
    try:
        print(f"[DEBUG] generate_openai_stream_generator: prompt_cache={'present' if prompt_cache else None}, prefix_len={prefix_len}")
        # Get streaming generator
        stream = mlx_lm.stream_generate(
            model,
            tokenizer,
            prompt,
            max_tokens=max_tokens,
            prefill_step_size=PREFILL_STEP_SIZE,
            kv_bits=KV_BITS,
            max_kv_size=MAX_KV_SIZE,
            prompt_cache=prompt_cache if prompt_cache else None
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
    
    # Convert messages to list of dicts for tokenizer
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    # Ensure there's at least one user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user messages found")
    
    # Format prompt using Qwen chat template
    formatted_prompt = format_messages(messages)
    
    # Handle streaming vs non-streaming
    if request.stream:
        # Check if we can use system prompt caching
        system_prompt = can_use_system_cache(messages)
        print(f"Cache check: system_prompt={'present' if system_prompt else 'None'}, messages count={len(messages)}")
        prompt_cache = None
        prefix_len = 0
        
        if system_prompt:
            try:
                with cache_lock:
                    prompt_cache, prefix_len = get_system_prompt_cache(system_prompt)
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
                model_name="Qwen3.5-9B-MLX",
                prompt_cache=prompt_cache,
                prefix_len=prefix_len
            ),
            media_type="text/event-stream"
        )
    else:
        # Check if we can use system prompt caching
        system_prompt = can_use_system_cache(messages)
        print(f"Cache check: system_prompt={'present' if system_prompt else 'None'}, messages count={len(messages)}")
        prompt_cache = None
        prefix_len = 0
        
        if system_prompt:
            try:
                with cache_lock:
                    prompt_cache, prefix_len = get_system_prompt_cache(system_prompt)
            except Exception as e:
                print(f"Warning: Failed to get system prompt cache: {e}")
                prompt_cache = None
        
        # Generate response
        print(f"Generation: cache={'present' if prompt_cache else 'None'}, prefix_len={prefix_len}")
        start_gen_time = time.time()
        response_text = mlx_lm.generate(
            model,
            tokenizer,
            formatted_prompt,
            max_tokens=request.max_tokens,
            verbose=False,
            prefill_step_size=PREFILL_STEP_SIZE,
            prompt_cache=prompt_cache if prompt_cache else None,
            kv_bits=KV_BITS,
            max_kv_size=MAX_KV_SIZE
        )
        gen_time = time.time() - start_gen_time
        print(f"Generation time: {gen_time:.2f}s")
        
        # Remove prompt from response
        if response_text.startswith(formatted_prompt):
            response_text = response_text[len(formatted_prompt):]
        
        response_text = strip_thinking(response_text.strip())
        
        # Trim cache back to prefix length if used
        if prompt_cache:
            # Determine how many tokens were added after prefix
            total_tokens = len(tokenizer.encode(formatted_prompt)) + len(tokenizer.encode(response_text))
            added_tokens = total_tokens - prefix_len
            print(f"Cache trimming: prefix_len={prefix_len}, total_tokens={total_tokens}, added_tokens={added_tokens}")
            if added_tokens > 0:
                cache.trim_prompt_cache(prompt_cache, added_tokens)
                print(f"Cache trimmed, remaining cache size approx {prefix_len} tokens")
        
        # Calculate token counts (mlx_lm.generate returns only generated tokens)
        input_tokens = len(tokenizer.encode(formatted_prompt))
        output_tokens = len(tokenizer.encode(response_text))
        
        # Return OpenAI-compatible response
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "Qwen3.5-9B-MLX",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": strip_thinking(response_text)
                },
                "finish_reason": "length" if output_tokens >= request.max_tokens else "stop"
            }],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens
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
    
    print(f"Starting Qwen3.5-9B-MLX server on http://{HOST}:{PORT}")
    print(f"API documentation: http://{HOST}:{PORT}/docs")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
#!/usr/bin/env python3
"""
GLM-4.7-Flash-4bit Local Server with Streaming

A FastAPI server that provides streaming inference for the GLM-4.7-Flash-4bit model.
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
MODEL_PATH = "./GLM-4.7-Flash-4bit"
HOST = "0.0.0.0"
PORT = int(os.environ.get('PORT', 8000))
MAX_CACHEABLE_TOKENS = 512  # Limit cache to 512 tokens for memory safety
PREFILL_STEP_SIZE = 1024  # Reduced for memory safety
KV_BITS = 8  # 8-bit quantization for KV cache (balanced speed/memory)
MAX_KV_SIZE = 2048  # Limit total KV cache size (prefix + generation)
ENABLE_PREFILL = True  # Can be disabled if memory issues persist

# Global model and tokenizer
model = None
tokenizer = None

# System prompt KV cache
system_prompt_caches = {}  # hash -> (cache, prefix_len)
cache_lock = threading.Lock()

def get_prefix_tokens(system_prompt):
    """Return token IDs for prefix up to and including <|user|> token."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": ""}
    ]
    template = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False
    )
    tokens = tokenizer.encode(template)
    # Find <|user|> token id (154827)
    user_token_id = 154827
    try:
        idx = tokens.index(user_token_id)
        return tokens[:idx+1]
    except ValueError:
        # fallback: return tokens up to the assistant token?
        # This should not happen
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
    
    # Store cache (now prefilled)
    system_prompt_caches[hash_key] = (prompt_cache, prefix_len)
    print(f"Cache stored: hash={hash_key[:16]}..., prefix_len={prefix_len}, cache_dict_size={len(system_prompt_caches)}")
    return prompt_cache, prefix_len

def format_glm4_prompt(user_message: str, system_message: Optional[str] = None) -> str:
    """Format prompt for GLM-4 model using tokenizer's chat template."""
    if tokenizer is None:
        raise ValueError("Tokenizer not loaded")
    
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": user_message})
    
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False  # We want final answer, not thinking
    )

def format_messages(messages: List[Dict[str, str]], enable_thinking: bool = False) -> str:
    """Format messages using tokenizer's chat template."""
    if tokenizer is None:
        raise ValueError("Tokenizer not loaded")
    
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=enable_thinking
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
    print("Loading GLM-4.7-Flash-4bit model...")
    start_time = time.time()
    
    try:
        model, tokenizer = mlx_lm.load(MODEL_PATH, lazy=True)
        load_time = time.time() - start_time
        print(f"✓ Model loaded successfully in {load_time:.2f} seconds")
        
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
    model: str = Field("GLM-4.7-Flash-4bit", description="Model name")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")

# Create FastAPI app
app = FastAPI(
    title="GLM-4.7-Flash-4bit Server",
    description="Local server for GLM-4.7-Flash-4bit model with streaming",
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
        "message": "GLM-4.7-Flash-4bit Server",
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
        "model": "GLM-4.7-Flash-4bit",
        "format": "MLX 4-bit quantized",
        "path": MODEL_PATH,
        "status": "loaded",
        "parameters": "30B",
        "context_window": "202K tokens",
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
        formatted_prompt = format_glm4_prompt(request.prompt, request.system_prompt)
    else:
        formatted_prompt = format_glm4_prompt(request.prompt)
    
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
    
    # Calculate token counts (approximate)
    input_tokens = len(tokenizer.encode(formatted_prompt))
    output_tokens = len(tokenizer.encode(response_text)) - input_tokens
    
    return GenerationResponse(
        text=response_text.strip(),
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        model="GLM-4.7-Flash-4bit",
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
            new_text = response.text
            accumulated_text += new_text
            last_response = response
            
            # Send SSE event with the new text
            data = {
                "text": new_text,
                "accumulated": accumulated_text,
                "finished": False,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }
            yield f"data: {json.dumps(data)}\n\n"
            
            # Check if generation is complete
            if response.finish_reason is not None:
                break
        
        # Final completion event
        total_time = time.time() - start_time
        finish_reason = "completed"
        if last_response and hasattr(last_response, 'finish_reason') and last_response.finish_reason:
            finish_reason = last_response.finish_reason
        
        final_data = {
            "text": "",
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

async def generate_openai_stream_generator(prompt: str, max_tokens: int, request_id: str = None, model_name: str = "GLM-4.7-Flash-4bit", prompt_cache=None, prefix_len=0):
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
            new_text = response.text
            if first_token_time is None:
                first_token_time = time.time() - start_time
                print(f"[DEBUG] First token after {first_token_time:.3f}s, prefix_len={prefix_len}, cache={'present' if prompt_cache else 'None'}")
            accumulated_text += new_text
            last_response = response
            
            # Create OpenAI-compatible chunk
            chunk = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model_name,
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": new_text
                    },
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            
            # Check if generation is complete
            if response.finish_reason is not None:
                break
        
        # Final completion chunk
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
        formatted_prompt = format_glm4_prompt(request.prompt, request.system_prompt)
    else:
        formatted_prompt = format_glm4_prompt(request.prompt)
    
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
    
    # Format prompt using tokenizer's chat template (no thinking)
    formatted_prompt = format_messages(messages, enable_thinking=False)
    
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
                model_name="GLM-4.7-Flash-4bit",
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
        
        response_text = response_text.strip()
        
        # Trim cache back to prefix length if used
        if prompt_cache:
            # Determine how many tokens were added after prefix
            total_tokens = len(tokenizer.encode(formatted_prompt)) + len(tokenizer.encode(response_text))
            added_tokens = total_tokens - prefix_len
            print(f"Cache trimming: prefix_len={prefix_len}, total_tokens={total_tokens}, added_tokens={added_tokens}")
            if added_tokens > 0:
                cache.trim_prompt_cache(prompt_cache, added_tokens)
                print(f"Cache trimmed, remaining cache size approx {prefix_len} tokens")
        
        # Calculate token counts
        input_tokens = len(tokenizer.encode(formatted_prompt))
        output_tokens = len(tokenizer.encode(response_text)) - input_tokens
        
        # Return OpenAI-compatible response
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "GLM-4.7-Flash-4bit",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
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
                "id": "glm-4-7-flash-4bit",
                "object": "model",
                "created": 0,
                "owned_by": "local"
            }
        ]
    }
if __name__ == "__main__":
    import uvicorn
    
    print(f"Starting GLM-4.7-Flash-4bit server on http://{HOST}:{PORT}")
    print(f"API documentation: http://{HOST}:{PORT}/docs")
    
    uvicorn.run(
        app,
        host=HOST,
        port=PORT,
        log_level="info"
    )
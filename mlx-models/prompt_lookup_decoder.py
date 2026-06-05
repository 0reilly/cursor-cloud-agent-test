#!/usr/bin/env python3
"""
Prompt-Lookup Speculative Decoding for MLX

Zero-draft-model speculative decoding using n-gram matching in the prefix.
Instead of a draft model (expensive on M1 Pro), we find n-gram matches of
recent tokens in the prompt+output history and use the continuation as drafts.

This mirrors the verification loop from mlx_lm.generate.speculative_generate_step,
but replaces the draft model with O(n) string matching — essentially free on CPU.

Algorithm (from "Prompt Lookup Decoding" by Saxena et al. and assisted generation):
1. Maintain full_tokens = prompt + all generated tokens
2. For each step, find the longest n-gram (up to n=4) ending at the current position
   that also appears earlier in full_tokens
3. Take the continuation after that earlier match as draft tokens
4. Verify N draft tokens in one target model forward pass
5. Accept all matching tokens, fall back to the first rejected token's sampled output
"""

import mlx.core as mx
import mlx.nn as nn
from typing import Optional, Callable, List, Tuple, Generator, Any
import functools
import time


def _to_scalar(x):
    """Safely convert mx.array or Python scalar to float."""
    if hasattr(x, 'item'):
        v = x.item()
        return float(v) if hasattr(v, '__float__') else float(v)
    return float(x)


def _find_ngram_match(tokens: list, needle_len: int = 4, min_len: int = 2) -> Tuple[int, int]:
    """
    Find the longest n-gram ending at tokens[-1] that also appears earlier.
    
    Args:
        tokens: List of all token ids (prompt + generated so far)
        needle_len: Maximum n-gram length to try
        min_len: Minimum n-gram length to accept
        
    Returns:
        (match_end, match_len): Position of match end in tokens[:-1], and match length.
        Returns (-1, 0) if no match found.
    """
    if len(tokens) < 2:
        return -1, 0
    
    # Try progressively shorter needles
    for n in range(min(needle_len, len(tokens) - 1), min_len - 1, -1):
        needle = tokens[-n:]  # Last n tokens
        # Search for needle in tokens[:-1] (exclude the needle itself at the end)
        haystack = tokens[:-1]
        
        # Linear scan from the end (recent matches preferred — they're more likely
        # to be contextually relevant)
        for i in range(len(haystack) - n, -1, -1):
            if haystack[i:i + n] == needle:
                # Found a match! Return the end position of the match
                return i + n, n
    
    return -1, 0


def _get_draft_tokens(tokens: list, match_end: int, num_draft: int) -> list:
    """
    Extract draft tokens from the continuation after a match.
    
    Args:
        tokens: Full token list (prompt + generated)
        match_end: Index in tokens where the match ends
        num_draft: Number of draft tokens to extract
        
    Returns:
        List of draft token ids (may be fewer than num_draft if at end of tokens)
    """
    continuation_start = match_end
    continuation_end = min(continuation_start + num_draft, len(tokens))
    if continuation_end <= continuation_start:
        return []
    return tokens[continuation_start:continuation_end]


def prompt_lookup_generate_step(
    prompt: mx.array,
    model: nn.Module,
    *,
    num_draft_tokens: int = 4,
    ngram_min: int = 2,
    ngram_max: int = 4,
    max_tokens: int = 256,
    sampler: Optional[Callable[[mx.array], mx.array]] = None,
    logits_processors: Optional[List[Callable[[mx.array, mx.array], mx.array]]] = None,
    prompt_cache: Optional[Any] = None,
    prefill_step_size: int = 2048,
    kv_bits: Optional[int] = None,
    kv_group_size: int = 64,
    quantized_kv_start: int = 0,
    generation_stream: Optional[mx.Stream] = None,
) -> Generator[Tuple[int, float, bool], None, None]:
    """
    A generator producing token ids using prompt-lookup speculative decoding.
    
    This is a drop-in replacement for speculative_generate_step that uses
    n-gram matching instead of a draft model.
    
    Args:
        prompt (mx.array): The input prompt token ids.
        model (nn.Module): The target model for generation and verification.
        num_draft_tokens (int): Maximum number of draft tokens per step. Default: 4.
        ngram_min (int): Minimum n-gram length for matching. Default: 2.
        ngram_max (int): Maximum n-gram length for matching. Default: 4.
        max_tokens (int): Maximum number of tokens to generate. Default: 256.
        sampler (Callable): Sampler for token selection. Default: argmax.
        logits_processors (List): Logits processors (repetition penalty, etc.).
        prompt_cache (Any): Pre-computed KV cache for the prompt prefix.
        prefill_step_size (int): Step size for incremental prefill.
        kv_bits (int): KV cache quantization bits.
        kv_group_size (int): KV cache quantization group size.
        quantized_kv_start (int): When to start KV cache quantization.
        generation_stream (mx.Stream): MLX stream for generation.
        
    Yields:
        Tuple[int, float, bool]: (token_id, log_prob, is_draft)
        - is_draft=True: token was accepted from draft (n-gram match)
        - is_draft=False: token came from target model sampling (verification)
    """
    from mlx_lm.models import cache
    from mlx_lm.generate import maybe_quantize_kv_cache
    
    y = prompt.astype(mx.uint32)
    prev_tokens = None
    
    # Create the KV cache for generation
    if prompt_cache is None:
        model_cache = cache.make_prompt_cache(model)
    else:
        model_cache = prompt_cache
    
    sampler = sampler or (lambda x: mx.argmax(x, axis=-1))
    
    # Set up stream
    if generation_stream is None:
        generation_stream = mx.new_stream(mx.default_device())
    
    quantize_cache_fn = functools.partial(
        maybe_quantize_kv_cache,
        quantized_kv_start=quantized_kv_start,
        kv_group_size=kv_group_size,
        kv_bits=kv_bits,
    )
    
    def _process_and_sample(tokens, logits):
        if logits_processors:
            for processor in logits_processors:
                logits = processor(tokens, logits)
        logprobs = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
        y = sampler(logprobs)
        return y, logprobs
    
    def _step(y_flat, n_predict=1):
        """Run one forward pass of the target model and sample n_predict tokens."""
        nonlocal prev_tokens
        with mx.stream(generation_stream):
            logits = model(y_flat[None], cache=model_cache)
            logits = logits[:, -n_predict:, :]
            quantize_cache_fn(model_cache)
            
            if logits_processors:
                out_y, out_logprobs = [], []
                if n_predict > 1:
                    y_flat = y_flat[:-(n_predict - 1)]
                for i in range(n_predict):
                    prev_tokens = (
                        mx.concatenate([prev_tokens, y_flat])
                        if prev_tokens is not None
                        else y_flat
                    )
                    tok, logprobs_vec = _process_and_sample(prev_tokens, logits[:, i, :])
                    out_y.append(tok)
                    out_logprobs.append(logprobs_vec)
                return mx.concatenate(out_y, axis=0), mx.concatenate(out_logprobs, axis=0)
            else:
                return _process_and_sample(None, logits.squeeze(0))
    
    def _prefill(y_tokens):
        """Prefill the model with prompt tokens."""
        while y_tokens.size > prefill_step_size:
            model(y_tokens[:prefill_step_size][None], cache=model_cache)
            quantize_cache_fn(model_cache)
            mx.eval([c.state for c in model_cache])
            y_tokens = y_tokens[prefill_step_size:]
            mx.clear_cache()
        return y_tokens
    
    def _rewind_cache(num_draft, num_accept):
        """Rewind KV cache when drafts are rejected."""
        cache.trim_prompt_cache(model_cache, num_draft - num_accept)
    
    # Prefill
    with mx.stream(generation_stream):
        y = _prefill(y)
    
    # Build the full token history as a Python list (cheap — just IDs)
    full_tokens = prompt.astype(mx.uint32).tolist()
    
    ntoks = 0
    num_draft = 0
    n_accepted = 0
    
    try:
        while ntoks < max_tokens:
            # --- DRAFT PHASE: Find n-gram match in prefix ---
            match_end, match_len = _find_ngram_match(full_tokens, ngram_max, ngram_min)
            num_draft = min(max_tokens - ntoks, num_draft_tokens)
            
            if match_end > 0 and num_draft > 0:
                # Get continuation after the match
                draft_ids = _get_draft_tokens(full_tokens, match_end, num_draft)
                num_draft = len(draft_ids)
            else:
                draft_ids = []
                num_draft = 0
            
            # --- VERIFICATION PHASE ---
            if num_draft > 0:
                # Feed current token + drafts to model for verification
                draft_tokens = mx.array(draft_ids, mx.uint32)
                if prev_tokens is not None:
                    prev_tokens = prev_tokens[:prev_tokens.size - y.size - num_draft + 1]
                
                verify_input = mx.concatenate([y, draft_tokens])
                verify_tokens, verify_logprobs = _step(verify_input, num_draft + 1)
                mx.eval(verify_tokens, draft_tokens)
                
                draft_list = draft_tokens.tolist()
                verify_list = verify_tokens.tolist()
                
                # Accept matching tokens
                n_accepted = 0
                while n_accepted < num_draft:
                    tv = verify_list[n_accepted]
                    dt = draft_list[n_accepted]
                    lp = verify_logprobs[n_accepted]
                    
                    if tv != dt:
                        break
                    n_accepted += 1
                    ntoks += 1
                    full_tokens.append(tv)
                    yield tv, lp, True  # is_draft=True
                    
                    if ntoks >= max_tokens:
                        break
                
                if ntoks >= max_tokens:
                    break
                
                # Emit the first rejected token (from target model, not draft)
                ntoks += 1
                rejected_token = verify_list[n_accepted]
                rejected_logprob = verify_logprobs[n_accepted]
                full_tokens.append(rejected_token)
                yield rejected_token, rejected_logprob, False  # is_draft=False
                
                # Set up for next iteration
                y = mx.array([rejected_token], mx.uint32)
                
                # If all drafts accepted, include the last draft token
                # (which hasn't been run through the model's forward pass yet)
                if n_accepted == num_draft:
                    y = mx.concatenate([
                        mx.array(draft_list[-1:], mx.uint32), y
                    ])
                
                if prev_tokens is not None:
                    prev_tokens = prev_tokens[:-max(num_draft - n_accepted, 1)]
                
                _rewind_cache(num_draft, n_accepted)
            else:
                # No n-gram match found — fall back to normal single-token generation
                token, logprob = _step(y)
                mx.eval(token)
                token_id = token.item()
                ntoks += 1
                full_tokens.append(token_id)
                yield token_id, logprob, False  # is_draft=False
                
                if ntoks >= max_tokens:
                    break
                
                y = mx.array([token_id], mx.uint32)
    
    finally:
        _rewind_cache(num_draft, n_accepted)


def prompt_lookup_generate(
    model: nn.Module,
    tokenizer,
    prompt,
    max_tokens: int = 256,
    num_draft_tokens: int = 4,
    ngram_min: int = 2,
    ngram_max: int = 4,
    sampler=None,
    logits_processors=None,
    prompt_cache=None,
    prefill_step_size: int = 2048,
    kv_bits: Optional[int] = None,
    kv_group_size: int = 64,
    quantized_kv_start: int = 0,
    verbose: bool = True,
) -> str:
    """
    Generate text using prompt-lookup speculative decoding.
    
    Args:
        model: The target model.
        tokenizer: The tokenizer.
        prompt: Input prompt (string, mx.array, or list of ints).
        max_tokens: Maximum tokens to generate.
        num_draft_tokens: Maximum drafts per step.
        ngram_min: Minimum n-gram size for matching.
        ngram_max: Maximum n-gram size for matching.
        
    Returns:
        Generated text string (including prompt).
    """
    # Convert prompt to tokens
    if isinstance(prompt, str):
        tokens = mx.array(tokenizer.encode(prompt))
    elif isinstance(prompt, list):
        tokens = mx.array(prompt)
    else:
        tokens = prompt
    
    gen_start = time.time()
    draft_count = 0
    total_count = 0
    generated_ids = []
    
    generator = prompt_lookup_generate_step(
        tokens,
        model,
        num_draft_tokens=num_draft_tokens,
        ngram_min=ngram_min,
        ngram_max=ngram_max,
        max_tokens=max_tokens,
        sampler=sampler,
        logits_processors=logits_processors,
        prompt_cache=prompt_cache,
        prefill_step_size=prefill_step_size,
        kv_bits=kv_bits,
        kv_group_size=kv_group_size,
        quantized_kv_start=quantized_kv_start,
    )
    
    for token_id, logprob, is_draft in generator:
        generated_ids.append(token_id)
        total_count += 1
        if is_draft:
            draft_count += 1
    
    gen_time = time.time() - gen_start
    
    # Decode
    full_ids = tokens.tolist() + generated_ids
    response = tokenizer.decode(full_ids)
    
    if verbose:
        print(f"[prompt_lookup] Generated {total_count} tokens in {gen_time:.2f}s "
              f"({total_count/gen_time:.1f} tok/s, "
              f"draft_accept={draft_count}/{total_count} "
              f"= {100*draft_count/max(1,total_count):.0f}%)")
    
    return response

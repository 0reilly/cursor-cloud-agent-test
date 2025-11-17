#!/usr/bin/env python3
"""
MLX LLM Inference Server
Run an MLX LLM inference server using mlx-lm
"""

import argparse
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Run MLX LLM Inference Server")
    parser.add_argument(
        "--model",
        type=str,
        default="mlx-community/QwQ-32B-Preview",
        help="Model name or path (default: mlx-community/QwQ-32B-Preview)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to bind to (default: 8080)",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=100,
        help="Maximum number of tokens to generate (default: 100)",
    )
    parser.add_argument(
        "--temp",
        type=float,
        default=0.0,
        help="Sampling temperature (default: 0.0)",
    )
    
    args = parser.parse_args()
    
    # Build the mlx_lm.server command (note: mlx_lm uses 'server' not 'serve')
    cmd = [
        sys.executable,
        "-m",
        "mlx_lm.server",
        "--model",
        args.model,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--max-tokens",
        str(args.max_tokens),
        "--temp",
        str(args.temp),
    ]
    
    print(f"Starting MLX LLM Inference Server...")
    print(f"Model: {args.model}")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Max tokens: {args.max_tokens}")
    print(f"Temperature: {args.temp}")
    print(f"\nRunning command: {' '.join(cmd)}\n")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\nError running server: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("\nError: mlx_lm module not found. Please install dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()

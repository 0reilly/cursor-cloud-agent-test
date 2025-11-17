# MLX LLM Inference Server

This project runs an MLX LLM inference server using Apple's MLX framework.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

Run the server with default settings:
```bash
python run_server.py
```

### Custom Configuration

Run with custom model and settings:
```bash
python run_server.py --model mlx-community/Mistral-7B-Instruct-v0.2 --port 8080 --max-tokens 200 --temp 0.7
```

### Command Line Options

- `--model`: Model name or path (default: `mlx-community/QwQ-32B-Preview`)
- `--host`: Host to bind to (default: `0.0.0.0`)
- `--port`: Port to bind to (default: `8080`)
- `--max-tokens`: Maximum number of tokens to generate (default: `100`)
- `--temp`: Sampling temperature (default: `0.0`)

### Using the Server

Once the server is running, you can make requests to it:

```bash
# Example curl request
curl http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello, how are you?",
    "max_tokens": 50
  }'
```

Or use the chat endpoint:
```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "max_tokens": 50
  }'
```

## Available Models

You can use any MLX-compatible model from Hugging Face. Some popular options:
- `mlx-community/QwQ-32B-Preview`
- `mlx-community/Mistral-7B-Instruct-v0.2`
- `mlx-community/Llama-3.2-3B-Instruct`
- `mlx-community/Qwen2.5-7B-Instruct`

## Notes

- The server will download the model on first run if it's not already cached
- Models are cached in `~/.cache/huggingface/hub/` by default
- Make sure you have sufficient disk space for the model you choose

## Linux Installation Note

MLX is primarily designed for Apple Silicon. On Linux, MLX may require building from source or installing additional runtime libraries. If you encounter `libmlx.so: cannot open shared object file` errors, you may need to:

1. Build MLX from source (see [MLX GitHub](https://github.com/ml-explore/mlx))
2. Use MLX on Apple Silicon hardware
3. Consider using alternative inference servers for Linux

For building from source on Linux, refer to the [MLX documentation](https://ml-explore.github.io/mlx/build/html/index.html).

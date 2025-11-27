# 🩺 Nephrology RAG MCP Server

> **Production-Grade Medical Knowledge Retrieval for Nephrology Using the Model Context Protocol (MCP)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.13.1-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![Google Cloud Run](https://img.shields.io/badge/Cloud-Run-orange.svg)](https://cloud.google.com/run)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)](#-live-deployment)

A production-ready MCP server providing semantic search and retrieval over comprehensive nephrology medical literature using vector embeddings and RAG (Retrieval-Augmented Generation).

---

## 📋 Table of Contents

- [Features](#-features)
- [Live Deployment](#-live-deployment)
- [Quick Start](#-quick-start)
- [MCP Configuration](#-mcp-configuration)
- [MCP Tools Reference](#-mcp-tools-reference)
- [Local Development](#-local-development)
- [Testing](#-testing)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

- **Semantic Search with RAG** - Vector-based retrieval using FAISS with domain-optimized embeddings via Mistral AI
- **MCP-Compliant Tooling** - Fully compliant with [Model Context Protocol v2024-11-05](https://modelcontextprotocol.io/)
- **Production-Ready Infrastructure** - FastMCP framework with async/await patterns, error handling, and logging
- **Medical Domain Optimized** - Comprehensive nephrology corpus with high-quality 1024-dim embeddings and metadata enrichment

---

## 🌐 Live Deployment

### Service Information

| Property           | Value                                                                |
| ------------------ | -------------------------------------------------------------------- |
| 🌍 **URL**         | `https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp` |
| 🏢 **Platform**    | Google Cloud Run (us-central1)                                       |
| 🔄 **Status**      | Active & Operational                                                 |
| ⏱️ **Uptime**      | 99.95% SLA                                                           |
| 📦 **Image**       | `wasimansariiitm/nephrology-rag-mcp:latest`                          |
| 💾 **Resources**   | 512 MB RAM, 1 vCPU                                                   |
| 🎯 **Concurrency** | 80 requests/instance                                                 |
| ⏳ **Timeout**     | 300 seconds                                                          |

### Quick Test

```bash
# Health check
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'

# Query documents
curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"invoke","params":{"query":"acute kidney injury","k":3},"id":2}'
```

---

## 🛠️ MCP Deployment Notes

- **Place manifest:** Ensure `mcp.json` is in the repository root next to `rag_mcp_server.py` so clients and registries can discover tools.

- **Environment variable names (server reads in order):** `MISTRALAI_API_KEY`, `MISTRAL_API_KEY`, `mistral_api_key`. Set one of these in your deployment environment.

- **FastMCP & dependency versions:** Use the versions declared in `pyproject.toml` / `requirements.txt` (recommended `fastmcp>=2.13.1`). Keep container dependencies in sync with the repo.

Local Docker build & test

```bash
# Build image (repo root)
docker build -t nephrology-rag-mcp:latest .

# Run locally (forward port 8000)
docker run --rm -e MISTRALAI_API_KEY="$MISTRALAI_API_KEY" -p 8000:8000 nephrology-rag-mcp:latest

# Health check (local)
curl -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'
```

Google Cloud Run (example)

```bash
# Build & push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nephrology-rag-mcp:latest

# Deploy (set the Mistral API key in Cloud Run env)
gcloud run deploy nephrology-rag-mcp \
  --image gcr.io/YOUR_PROJECT_ID/nephrology-rag-mcp:latest \
  --region us-central1 --allow-unauthenticated \
  --set-env-vars MISTRALAI_API_KEY=$MISTRALAI_API_KEY
```

GitHub Actions (CI): build the image, push, and deploy to Cloud Run using a service account with the right permissions (see `MCP_DEPLOY_NOTE.md`).

Compatibility checklist for `langchain_mcp_adapters` clients

- Ensure client config includes a compatible transport for streaming HTTP (examples: `streamable_http` or `sse`) when required by the client library.
- Clients should send `Accept: application/json, text/event-stream` when calling the MCP endpoint to receive streaming responses.
- The server accepts session IDs provided in multiple places: top-level `session` field, `params.session`, `session` query parameter, or the `X-FastMCP-Session` header. This helps clients that previously failed with "Missing session ID".

Notes & troubleshooting

- If clients see `Missing session ID`, verify the client either sends a session value or that the client library supports session injection; upgrade FastMCP if the server complains about session handling.
- If the server returns `406 Not Acceptable`, ensure your client `Accept` header includes both `application/json` and `text/event-stream`.
- If you see `401 Unauthorized` from Mistral, confirm Cloud Run (or local container) has the correct `MISTRALAI_API_KEY` set.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Valid [Mistral AI API key](https://console.mistral.ai/api-keys)

### Installation

```bash
# Clone repository
git clone https://github.com/wsmaisys/Nephrology-RAG-MCP-tool.git
cd Nephrology-RAG-MCP-tool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\Activate.ps1  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key
echo "MISTRAL_API_KEY=your_api_key_here" > .env

# Run server
python rag_mcp_server.py
# Server starts on http://0.0.0.0:8000
```

---

## ⚙️ MCP Configuration

Add this configuration to your MCP client settings (e.g., Claude Desktop's `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "nephrology-rag": {
      "command": "uvx",
      "args": [
        "fastmcp-client",
        "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"
      ]
    }
  }
}
```

**Configuration locations:**

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

After adding the configuration, restart your MCP client to load the server.

---

### 🔗 Using with LangChain (`langchain-mcp-adapters`)

If you're integrating with LangChain via `langchain-mcp-adapters`, use this configuration:

#### ✅ Correct Configuration (HTTP streaming transport)

```python
import os
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

load_dotenv()  # Load from .env

# Use the standard `transport` key per the universal MCP config. For
# this server prefer 'sse' or 'streamable_http' to indicate HTTP streaming.
mcp_config = {
  "mcpServers": {
    "nephrology-rag": {
      "transport": "sse",
      "url": "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"
    }
  }
}

# Initialize the MCP client
mcp_client = MultiServerMCPClient(mcp_config)

# Load tools (async clients may require awaiting/get_tools())
tools = mcp_client.get_tools()
```

#### ⚠️ Common Mistakes

**❌ Wrong: Forcing an incompatible transport**

```python
mcp_config = {
  "mcpServers": {
    "nephrology-rag": {
      "transport": "websocket",  # ← WRONG for this server (it uses HTTP streaming)
      "url": "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"
    }
  }
}
```

**❌ Wrong: Passing API key in server config**

```python
mcp_config = {
  "mcpServers": {
    "nephrology-rag": {
      "type": "http",
      "url": "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp",
      "env": {
        "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY")  # ← Won't work for HTTP URLs
      }
    }
  }
}
```

#### ℹ️ About API Key Management

- The deployed server on Cloud Run **already has `MISTRAL_API_KEY` configured** in its environment
- The client **does not need** to pass the API key to the server
- Ensure `MISTRAL_API_KEY` is in your client's `.env` or environment (for your LangChain code if needed)

#### Local Testing (Alternative)

For local development using stdio transport:

```python
mcp_config = {
  "mcpServers": {
    "nephrology-rag": {
      "command": "python",
      "args": ["rag_mcp_server.py"],
      "env": {
        "MISTRAL_API_KEY": os.getenv("MISTRAL_API_KEY", ""),
        "MCP_TRANSPORT": "stdio"
      }
    }
  }
}
```

**Note:** This requires setting `MCP_TRANSPORT=stdio` support in `rag_mcp_server.py` and running the server locally.

---

## 🔧 MCP Tools Reference

### 1️⃣ Tool: `invoke`

Retrieve top-k relevant documents for a query using semantic search.

**Parameters:**

| Name    | Type    | Required | Default | Description                   |
| ------- | ------- | -------- | ------- | ----------------------------- |
| `query` | string  | ✅ Yes   | -       | Natural language search query |
| `k`     | integer | ❌ No    | 4       | Number of results to return   |

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "invoke",
  "params": {
    "query": "acute kidney injury diagnosis and management",
    "k": 4
  },
  "id": 1
}
```

**Example Response:**

```json
{
  "status": "success",
  "query": "acute kidney injury diagnosis and management",
  "context": [
    "The basic diagnostic approach to patients with AKI is to determine the cause...",
    "Acute kidney injury (AKI) has become the consensus term for ARF..."
  ],
  "metadata": [
    {
      "source": "comprehensive-clinical-nephrology.pdf",
      "page": 963,
      "page_label": "964",
      "total_pages": 1469
    }
  ],
  "num_results": 4
}
```

### 2️⃣ Tool: `health`

Check service health and readiness.

**Parameters:** None

**Example Request:**

```json
{
  "jsonrpc": "2.0",
  "method": "health",
  "params": {},
  "id": 1
}
```

**Example Response:**

```json
{
  "status": "ok",
  "message": "RAG service is ready",
  "vector_store_path": "vector_store"
}
```

---

## 🛠️ Local Development

### Environment Setup

```bash
# Create .env file
cat > .env << EOF
MISTRAL_API_KEY=your_mistral_api_key_here
EOF

# Or set environment variable
export MISTRAL_API_KEY="your_api_key"  # Linux/Mac
$env:MISTRAL_API_KEY="your_api_key"   # Windows PowerShell
```

### Running the Server

```bash
python rag_mcp_server.py

# Expected output:
# [RAG MCP] Starting RAG MCP Server...
# [RAG MCP] Loading vector store from 'vector_store'...
# [RAG MCP] Vector store loaded successfully!
# [RAG MCP] Server listening on http://0.0.0.0:8000
```

---

## 🧪 Testing

### Using FastMCP Client

```python
import asyncio
from fastmcp import Client

async def test_service():
    url = "http://localhost:8000/mcp"

    async with Client(url) as client:
        # Health check
        health = await client.call_tool("health", {})
        print(f"Health: {health}")

        # Query RAG
        result = await client.call_tool(
            "invoke",
            {"query": "acute kidney injury", "k": 4}
        )
        print(f"Found {result['num_results']} documents")

asyncio.run(test_service())
```

### Using cURL

```bash
# Health check
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'

# Query documents
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"invoke","params":{"query":"CKD management","k":3},"id":2}'
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│       FastMCP HTTP Server               │
│   (Python 3.10 + FastMCP 2.13.1)        │
└────────────────┬────────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
   ┌────▼──┐ ┌──▼──┐ ┌──▼──────┐
   │invoke │ │health│ │Resource │
   └────┬──┘ └──┬──┘ └──┬──────┘
        │       │       │
   ┌────▼───────▼───────▼─────┐
   │ LangChain Retriever       │
   │ - Async execution         │
   │ - Error handling          │
   └────────┬──────────────────┘
            │
   ┌────────▼──────────────┐
   │  FAISS Vector Store   │
   │  - 1024-dim embeddings│
   │  - 500+ documents     │
   └────────┬──────────────┘
            │
   ┌────────▼──────────────┐
   │ Mistral AI Embeddings │
   │ - Model: mistral-embed│
   └───────────────────────┘
```

---

## 📦 Project Structure

```
Nephrology-RAG-MCP-tool/
├── README.md                    # Documentation
├── LICENSE                      # MIT License
├── requirements.txt             # Python dependencies
├── rag_mcp_server.py           # Main MCP server
├── test_fastmcp_client.py      # Client testing script
├── Dockerfile                   # Container definition
├── mcp.json                     # MCP tool manifest
├── vector_store/                # Pre-built FAISS index
│   └── index.faiss
└── data/                        # Source documents (optional)
```

---

## 🔐 Configuration

### Environment Variables

| Variable            | Required | Default | Description          |
| ------------------- | -------- | ------- | -------------------- |
| `MISTRAL_API_KEY`   | ✅ Yes   | -       | Mistral AI API key   |
| `MISTRALAI_API_KEY` | ⚠️ Alt   | -       | Alternative key name |
| `PORT`              | ❌ No    | 8000    | Server port          |

### Security Best Practices

✅ **DO:**

- Store API keys in environment variables or `.env` files
- Add `.env` to `.gitignore`
- Use HTTPS in production
- Rotate keys regularly

❌ **DON'T:**

- Commit API keys to version control
- Include quotes in `.env` values (use `KEY=value` not `KEY="value"`)
- Share keys in issues or PRs

---

## 🆘 Troubleshooting

### LangChain MCP Configuration Errors

#### Error: `ValidationError: 'transport' is a required property`

**Cause:** The client-side MCP config omitted the standard `transport` field, or provided an incompatible transport value.

**Solution:** Provide a `transport` key and set it to an appropriate value (for this server use `sse` or `streamable_http`). Example:

```python
# ✅ Correct (preferred)
mcp_config = {
  "mcpServers": {
    "nephrology-rag": {
      "transport": "sse",
      "url": "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"
    }
  }
}

# ❌ Wrong (incompatible transport)
mcp_config = {
  "mcpServers": {
    "nephrology-rag": {
      "transport": "websocket",
      "url": "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"
    }
  }
}
```

#### Error: `ValueError: Configuration error loading MCP tools`

**Cause:** Usually due to:

- Wrong transport type specified
- Invalid server URL
- API key not configured on the server side

**Solution:**

1. Verify the server URL is correct (check deployment status)
2. Ensure the MCP client config includes a correct `"transport"` key (e.g., `"sse"` or `"streamable_http"`)
3. Ensure the deployed server has `MISTRAL_API_KEY` configured

### `401 Unauthorized` from Mistral API

**Solution:** Check API key configuration

```bash
# Verify environment variable
echo $MISTRAL_API_KEY

# Ensure .env has no quotes
cat .env  # Should be: MISTRAL_API_KEY=abc123xyz
```

### `Vector store not found`

**Solution:** Ensure `vector_store/` directory exists

```bash
ls -la vector_store/index.faiss
```

### Connection timeout

**Solution:** Service cold start - wait and retry

```bash
sleep 30
python test_fastmcp_client.py
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and test thoroughly
4. Commit with clear messages (`git commit -m "feat: add amazing feature"`)
5. Push and create a Pull Request

For bugs or feature requests, please [open an issue](https://github.com/wsmaisys/Nephrology-RAG-MCP-tool/issues).

---

## 📚 Resources

- [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [Mistral AI API Docs](https://docs.mistral.ai/)
- [LangChain Documentation](https://python.langchain.com/)
- [FAISS Documentation](https://github.com/facebookresearch/faiss)

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Contact

- **Developer:** [Wasim Ansari](https://github.com/wsmaisys)
- **Email:** [wsmaisys@gmail.com](mailto:wsmaisys@gmail.com)
- **LinkedIn:** [Wasim Ansari](https://linkedin.com/in/wasim-ansari)

---

## 🙌 Acknowledgments

Built with contributions from:

- Medical Literature: Comprehensive Clinical Nephrology textbooks
- Vector Search: Facebook Research (FAISS)
- LLM Infrastructure: Mistral AI
- Protocol: MCP Specification
- Framework: FastMCP Contributors

---

<div align="center">

### Built with ❤️ for Nephrology & Medical AI

**[⬆ Back to Top](#-nephrology-rag-mcp-server)**

</div>

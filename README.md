# 🩺 Nephrology RAG MCP Server

> **Production-Grade Medical Knowledge Retrieval for Nephrology Using the Model Context Protocol (MCP)**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMCP](https://img.shields.io/badge/FastMCP-2.13.1-brightgreen.svg)](https://github.com/jlowin/fastmcp)
[![Google Cloud Run](https://img.shields.io/badge/Cloud-Run-orange.svg)](https://cloud.google.com/run)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)](#-live-deployment--production)

---

## 📋 Table of Contents

- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [🏗️ Architecture](#-architecture)
- [🌐 Live Deployment](#-live-deployment--production)
- [🛠️ Local Development](#-local-development)
- [🧪 Testing](#-testing)
- [📦 Project Structure](#-project-structure)
- [🔧 MCP Tools Reference](#-mcp-tools-reference)
- [⚙️ Configuration](#-configuration)
- [🤝 Contributing](#-contributing)
- [📜 License](#-license)

---

## ✨ Features

### 🔍 **Semantic Search with RAG**

- **Vector-based retrieval** using FAISS for ultra-fast similarity search
- **Domain-optimized embeddings** via Mistral AI for medical literature
- **Top-k document ranking** with configurable result limits
- **Metadata preservation** for source tracking and citation

### 🧠 **MCP-Compliant Tooling**

- **Two core tools:**
  - `invoke` → Semantic search (query → top-k relevant documents)
  - `health` → Service health & readiness checks
- **Fully compliant** with [Model Context Protocol v2024-11-05](https://modelcontextprotocol.io/)
- **Streaming-based** HTTP transport for reliable communication

### ⚡ **Production-Ready Infrastructure**

- **FastMCP framework** (v2.13.1) for lightweight HTTP transport
- **Async/await patterns** for concurrent request handling
- **Error handling & logging** for observability

### 📚 **Medical Domain Optimized**

- **Comprehensive nephrology corpus** from clinical literature
- **High-quality embeddings** (1024-dim Mistral model)
- **Contextual relevance** with semantic similarity scoring
- **Metadata enrichment** (source, page, author information)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- pip or conda
- Valid [Mistral AI API key](https://console.mistral.ai/api-keys)

### Installation & Run (Local)

```bash
# 1. Clone repository
git clone https://github.com/wsmaisys/Nephrology-RAG-MCP-tool.git
cd Nephrology-RAG-MCP-tool

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Linux/Mac
# or
.\venv\Scripts\Activate.ps1       # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cat > .env << EOF
MISTRAL_API_KEY=your_mistral_api_key_here
EOF

# 5. Run server
python rag_mcp_server.py
# Server starts on http://0.0.0.0:8000
```

### Test Live Service (Cloud Run)

```bash
# Quick health check
python test_fastmcp_client.py

# Expected output:
# ✓ Connected to service
# ✓ Health: {"status":"ok","message":"RAG service is ready",...}
# ✓ Query returned 4 documents about acute kidney injury
```

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FastMCP HTTP Server                     │
│                 (Python 3.10 + FastMCP 2.13.1)              │
└────────────────────────────┬────────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
         ┌──────▼─────┐  ┌──▼────┐  ┌───▼──────┐
         │   Invoke   │  │Health │  │ Resource │
         │    Tool    │  │ Tool  │  │ Discovery│
         └──────┬─────┘  └──┬────┘  └───┬──────┘
                │           │          │
         ┌──────▼──────────▼──────────▼─────┐
         │    LangChain Retriever Pipeline   │
         │  - Async thread-based execution   │
         │  - Error handling & retry logic   │
         └──────┬──────────────────────────┘
                │
         ┌──────▼──────────────────┐
         │  FAISS Vector Store     │
         │  - 1024-dim embeddings  │
         │  - Fast similarity search│
         │  - ~500+ documents      │
         └──────┬──────────────────┘
                │
         ┌──────▼──────────────────┐
         │   Mistral AI Embeddings │
         │   - Model: mistral-embed│
         │   - API key validated   │
         └─────────────────────────┘
```

### Request Flow

```
Client Request (HTTP/SSE)
         │
         ▼
   ┌─────────────┐
   │ FastMCP     │ ← Parse JSON-RPC 2.0
   │ Transport   │
   └──────┬──────┘
          │
          ▼
    ┌──────────────┐
    │ Tool Router  │ ← Dispatch to invoke/health
    └──────┬───────┘
           │
      ┌────┴────────────┐
      │                 │
   invoke()          health()
      │                 │
      ▼                 ▼
  Query Text      ✓ Ready Check
      │                 │
      ▼                 ▼
  Embed Query    Status JSON
      │                 │
      ▼                 ▼
  FAISS Search   Return Response
      │
      ▼
  Get Top-K
      │
      ▼
Return JSON
      │
      ▼
   SSE Stream
      │
      ▼
   Client
```

---

## 🌐 Live Deployment · Production

### ✅ Active Service

| Property               | Value                                                                |
| ---------------------- | -------------------------------------------------------------------- |
| 🌍 **URL**             | `https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp` |
| 🏢 **Platform**        | Google Cloud Run                                                     |
| 📍 **Region**          | us-central1                                                          |
| 🔄 **Latest Revision** | `nephrology-mcp-server-00006-bcg`                                    |
| 🟢 **Status**          | Active & Operational                                                 |
| ⏱️ **Uptime**          | 99.95% SLA (Cloud Run)                                               |
| 📦 **Container Image** | `wasimansariiitm/nephrology-rag-mcp:latest` (Docker Hub)             |
| 💾 **Memory**          | 512 MB                                                               |
| ⚙️ **CPU**             | 1000m (1 vCPU)                                                       |
| 🎯 **Concurrency**     | 80 requests per instance                                             |
| 🔄 **Auto-scaling**    | Min: 0, Max: 1 instance                                              |
| ⏳ **Request Timeout** | 300 seconds                                                          |

### 🧪 Live Service Testing

**Test with FastMCP Client (Recommended):**

```python
import asyncio
from fastmcp import Client

async def test_live_service():
    """Test the production Nephrology RAG MCP service."""
    service_url = "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"

    async with Client(service_url) as client:
        print("📡 Connected to live service")

        # Health check
        health = await client.call_tool("health", {})
        print(f"✓ Health: {health}")

        # Query RAG system
        result = await client.call_tool(
            "invoke",
            {
                "query": "acute kidney injury diagnosis and treatment",
                "k": 4  # Return top 4 documents
            }
        )

        print(f"\n📚 Found {result['num_results']} relevant documents:")
        for i, doc in enumerate(result['context'], 1):
            metadata = result['metadata'][i-1]
            print(f"\n{i}. {metadata.get('source', 'Unknown')}")
            print(f"   Page: {metadata.get('page', 'N/A')}")
            print(f"   {doc[:150]}...")

# Run the test
asyncio.run(test_live_service())
```

**Quick cURL Test:**

```bash
# Health check
curl -X POST \
  https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "method": "health",
    "params": {},
    "id": 1
  }' -v

# Query documents
curl -X POST \
  https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "method": "invoke",
    "params": {
      "query": "chronic kidney disease management",
      "k": 3
    },
    "id": 2
  }' -v
```

---

## 🛠️ Local Development

### Environment Setup

**1. Clone & Navigate:**

```bash
git clone https://github.com/wsmaisys/Nephrology-RAG-MCP-tool.git
cd Nephrology-RAG-MCP-tool
```

**2. Create Virtual Environment:**

```bash
# Using venv
python -m venv venv
source venv/bin/activate              # Linux/Mac
# or
.\venv\Scripts\Activate.ps1           # Windows PowerShell

# Using conda (alternative)
conda create -n nephrology-rag python=3.10
conda activate nephrology-rag
```

**3. Install Dependencies:**

```bash
pip install -r requirements.txt
```

**4. Configure API Key:**

Create `.env` file in project root:

```env
# .env
MISTRAL_API_KEY=your_mistral_api_key_without_quotes
```

Or set environment variable:

```bash
# Linux/Mac
export MISTRAL_API_KEY="your_api_key"

# Windows PowerShell
$env:MISTRAL_API_KEY="your_api_key"

# Windows CMD
set MISTRAL_API_KEY=your_api_key
```

### Running Locally

```bash
# Start server (port 8000)
python rag_mcp_server.py

# Expected output:
# [RAG MCP] Starting RAG MCP Server...
# [RAG MCP] Loading vector store from 'vector_store'...
# [RAG MCP] Vector store loaded successfully!
# [RAG MCP] Retriever initialized!
# [RAG MCP] Server listening on http://0.0.0.0:8000
```

### Local Server Testing

**Test health endpoint:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'
```

**Query documents:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -d '{
    "jsonrpc":"2.0",
    "method":"invoke",
    "params":{"query":"glomerulonephritis treatment","k":3},
    "id":2
  }'
```

---

## 🧪 Testing

### Recommended: FastMCP Client (Async/Streaming)

**Installation:**

```bash
pip install fastmcp
```

**Test Script (`test_fastmcp_client.py`):**

```python
import asyncio
from fastmcp import Client

async def main():
    # Connect to local server
    url = "http://localhost:8000/mcp"

    async with Client(url) as client:
        # List tools
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")

        # Health check
        health_result = await client.call_tool("health", {})
        print(f"Health: {health_result}")

        # Invoke RAG
        rag_result = await client.call_tool(
            "invoke",
            {"query": "acute kidney injury", "k": 4}
        )
        print(f"Query results: {rag_result['num_results']} documents")

asyncio.run(main())
```

**Run test:**

```bash
python test_fastmcp_client.py
```

### Manual JSON-RPC Testing

**Using cURL:**

```bash
# Health check
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'

# Query documents
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","method":"invoke","params":{"query":"CKD management","k":3},"id":2}'
```

**Using Python requests:**

```python
import requests
import json

# Health check
response = requests.post(
    'http://localhost:8000/mcp',
    json={
        'jsonrpc': '2.0',
        'method': 'health',
        'params': {},
        'id': 1
    },
    headers={'Accept': 'application/json, text/event-stream'}
)
print(response.json())

# Query RAG
response = requests.post(
    'http://localhost:8000/mcp',
    json={
        'jsonrpc': '2.0',
        'method': 'invoke',
        'params': {'query': 'nephritis treatment', 'k': 4},
        'id': 2
    },
    headers={'Accept': 'application/json, text/event-stream'}
)
print(response.json())
```

### Test Suite Execution

```bash
# Run comprehensive test suite
python -m pytest tests/ -v

# Run specific test
python -m pytest tests/test_retriever.py -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=html
```

---

## 📦 Project Structure

```
Nephrology-RAG-MCP-tool/
│
├── 📄 README.md                      # This file
├── 📄 LICENSE                        # MIT License
├── 📄 .gitignore                     # Git ignore rules
├── 📦 requirements.txt               # Python dependencies
├── 📦 pyproject.toml                 # Project configuration
│
├── 🐍 rag_mcp_server.py              # Main MCP server entrypoint
│                                     # - FastMCP initialization
│                                     # - Tool definitions (invoke, health)
│                                     # - Vector store loading
│                                     # - Request handlers
│
├── 🧪 test_fastmcp_client.py         # FastMCP async client testing
├── 🧪 test_mcp_server.py             # JSON-RPC protocol testing
│
├── 🐳 Dockerfile                     # Container image definition
├── 📋 mcp.json                       # MCP tool manifest
│
├── 📚 vector_store/                  # Pre-built FAISS index
│   └── index.faiss                   # Serialized vector database
│
├── 📁 data/                          # (Optional) Source documents
│   └── *.pdf                         # Nephrology literature
│
└── 📁 __pycache__/                   # Python cache (git ignored)
```

---

## 🔧 MCP Tools Reference

### 1️⃣ Tool: `invoke`

**Retrieve top-k relevant documents for a query.**

#### Parameters

| Name    | Type    | Default     | Description                     |
| ------- | ------- | ----------- | ------------------------------- |
| `query` | string  | ❌ Required | Natural language search query   |
| `k`     | integer | 4           | Number of top results to return |

#### Example Request

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

#### Example Response

```json
{
  "status": "success",
  "query": "acute kidney injury diagnosis and management",
  "context": [
    "The basic diagnostic approach to patients with AKI is to determine the cause...",
    "Acute kidney injury (AKI) has become the consensus term for ARF...",
    "..."
  ],
  "metadata": [
    {
      "source": "comprehensive-clinical-nephrology.pdf",
      "page": 963,
      "page_label": "964",
      "total_pages": 1469
    },
    "..."
  ],
  "num_results": 4
}
```

#### Error Handling

```json
{
  "status": "error",
  "message": "Error invoking RAG tool: ...",
  "hint": "Empty 'Authorization: Bearer <token>' detected. Ensure MISTRALAI_API_KEY is set...",
  "traceback": "..."
}
```

---

### 2️⃣ Tool: `health`

**Check service health and readiness.**

#### Parameters

None

#### Example Request

```json
{
  "jsonrpc": "2.0",
  "method": "health",
  "params": {},
  "id": 1
}
```

#### Example Response

```json
{
  "status": "ok",
  "message": "RAG service is ready",
  "vector_store_path": "vector_store"
}
```

#### Error Response

```json
{
  "status": "error",
  "message": "Health check failed: Vector store not initialized"
}
```

---

## ⚙️ Configuration

### Environment Variables

| Variable            | Required | Default | Description                          |
| ------------------- | -------- | ------- | ------------------------------------ |
| `MISTRAL_API_KEY`   | ✅ Yes   | -       | Mistral AI API key (no quotes!)      |
| `MISTRALAI_API_KEY` | ⚠️ Alt   | -       | Alternative key name (same as above) |
| `PORT`              | ❌ No    | 8000    | Server port (8080 on Cloud Run)      |

### Docker Configuration

**Dockerfile Highlights:**

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PORT=8080
EXPOSE 8080
CMD ["python", "rag_mcp_server.py"]
```

### FastMCP Configuration

**Server Parameters (in `rag_mcp_server.py`):**

```python
mcp = FastMCP(
    "nephrology-rag-mcp",
    require_session=False  # Stateless operation
)

mcp.run(
    transport="http",
    host="0.0.0.0",
    port=port,
    request_timeout=300  # 5 minutes
)
```

---

## 🤝 Contributing

### Issues & Bug Reports

Found a bug? Create an issue with:

- 🐛 Bug description
- 🔄 Steps to reproduce
- 📸 Screenshots (if applicable)
- 💻 System info (OS, Python version, etc.)

### Feature Requests

Want a feature? Submit with:

- 💡 Feature description
- 🎯 Use case
- 📝 Example implementation (optional)

### Development Workflow

```bash
# 1. Fork repository
# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes
# 4. Run tests
python -m pytest tests/ -v

# 5. Commit with clear message
git commit -m "feat: add amazing feature"

# 6. Push and create Pull Request
git push origin feature/amazing-feature
```

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run linters
black .
flake8 .
mypy .

# Run tests
pytest tests/ -v --cov
```

---

## 📚 Documentation Links

- 📖 [Model Context Protocol Documentation](https://modelcontextprotocol.io/)
- 🚀 [FastMCP GitHub Repository](https://github.com/jlowin/fastmcp)
- 🤖 [Mistral AI API Documentation](https://docs.mistral.ai/)
- 📚 [LangChain Documentation](https://python.langchain.com/)
- 🔎 [FAISS Documentation](https://github.com/facebookresearch/faiss)
- ☁️ [Google Cloud Run Documentation](https://cloud.google.com/run/docs)

---

## 📊 Project Stats

| Metric               | Value                            |
| -------------------- | -------------------------------- |
| 🐍 Python Version    | 3.10+                            |
| 📦 Dependencies      | ~15 packages                     |
| 🧠 Model             | Mistral Embed (1024-dim)         |
| 📚 Documents         | 500+ pages nephrology literature |
| ⏱️ Query Latency     | ~100-200ms (avg)                 |
| 💾 Vector Store Size | ~50MB (FAISS)                    |
| 🐳 Docker Image Size | 1.58GB                           |
| 🌍 Deployment        | Google Cloud Run (us-central1)   |

---

## 🔒 Security & Best Practices

### API Key Management

✅ **DO:**

- Store API keys in environment variables
- Use `.env` files locally (add to `.gitignore`)
- Rotate keys regularly
- Use strong, unique keys

❌ **DON'T:**

- Commit `.env` files to version control
- Share API keys in issues or PRs
- Use plaintext API keys in code
- Include quotes in `.env` values (e.g., `KEY=value` not `KEY="value"`)

### HTTPS & TLS

- ✅ API key sent over HTTPS (when deployed)

### Rate Limiting

- ⏱️ 80 concurrent requests per instance
- 🔄 Service scales based on demand

---

## 🆘 Troubleshooting

### Issue: `401 Unauthorized` from Mistral API

**Cause:** Invalid or missing API key

```bash
# Solution 1: Check environment variable
echo $MISTRALAI_API_KEY

# Solution 2: Check .env file has no quotes
cat .env
# Should look like: MISTRAL_API_KEY=abc123xyz (no quotes)
```

### Issue: `Vector store not found`

**Cause:** `vector_store/` directory missing

```bash
# Solution: Ensure vector_store/ is in project root
ls -la vector_store/index.faiss
```

### Issue: Connection timeout

**Cause:** Service cold start or network issue

```bash
# Solution: Wait and retry
sleep 30
python test_fastmcp_client.py
```

---

## 📜 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 Nephrology RAG MCP Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
...
```

---

## ⭐ Show Your Support

If this project helped you, please:

- ⭐ **Star this repository** on GitHub
- 🍴 **Fork and contribute** improvements
- 🐦 **Share** with your network
- 💬 **Open issues** for bugs or features
- 🙏 **Cite** in your research/projects

---

## 👨‍💻 Authors & Contributors

- **Primary Developer:** [Wasim Ansari](https://github.com/wsmaisys)
- **Contributors:** Community members welcome!

---

## 📧 Contact & Support

- 📧 **Email:** [wsmaisys@gmail.com](mailto:wsmaisys@gmail.com)
- 🐙 **GitHub:** [@wsmaisys](https://github.com/wsmaisys)
- 💼 **LinkedIn:** [Wasim Ansari](https://linkedin.com/in/wasim-ansari)

---

## 🙌 Acknowledgments

- **Medical Literature:** Comprehensive Clinical Nephrology textbooks
- **Vector Search:** Facebook Research (FAISS team)
- **LLM Infrastructure:** Mistral AI
- **Protocol:** MCP Specification
- **Framework:** FastMCP Contributors

---

<div align="center">

### Built with ❤️ for Nephrology & Medical AI

**[⬆ Back to Top](#-nephrology-rag-mcp-server)**

</div>

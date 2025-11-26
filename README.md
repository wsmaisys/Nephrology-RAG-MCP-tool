# 🩺 Nephrology RAG MCP Server

**AI-Powered Medical Knowledge Retrieval for Nephrology Using the Model Context Protocol (MCP)**

This project is a **production-grade MCP (Model Context Protocol) tool** designed to provide fast, reliable, and accurate retrieval-augmented answers in the **Nephrology** domain. Built for **FastMCP.Cloud** deployment, it delivers structured tool responses, automated document retrieval, and health-checks — making it easy to integrate into LLM workflows or agentic systems.

---

## 🚀 Features

### 🔍 **1. RAG-Based Information Retrieval**

- Retrieves the **top-k most relevant nephrology document chunks**
- Optimized for medical literature, guidelines, and domain material
- Fast vector search using an embedded FAISS/Chroma store

### 🧠 **2. Fully MCP-Compliant Tooling**

Provides two MCP tools:

- **`invoke`** → semantic search (query → top-k docs)
- **`health`** → vector store + server status

### ⚙️ **3. Lightweight & Cloud-Friendly**

- Minimal dependencies
- Fast cold start
- Designed for FastMCP.Cloud deployment
- Simple entrypoint (`rag_mcp_server.py`)

### 📦 **4. Modular Architecture**

- Separate loader for documents
- Vector store manager
- Query pipeline
- Clean async handler

---

## 📁 Project Structure

```

Nephrology-RAG-MCP-tool/
│
├── rag_mcp_server.py         # Main MCP server (entrypoint)
├── utils.py                  # Helper functions for RAG + vector operations
├── data/                     # Medical text corpus (sample nephrology docs)
└── mcp.json                  # (To be added) MCP tool manifest

```

---

## 🧩 MCP Tools Exposed

### 1️⃣ **invoke**

Retrieve top-k relevant documents for a natural language query.

**Parameters:**

```json
{
  "query": "string",
  "k": "integer (default=4)"
}
```

**Returns:**

- Ranked chunks
- Similarity scores
- Metadata

---

### 2️⃣ **health**

Quick server diagnostics.

**Returns:**

- Vector store status
- Document count
- Embedding health
- Server uptime

---

## 🛠️ Installation & Setup (Local)

### 1️⃣ Clone the repo

```bash
git clone https://github.com/wsmaisys/Nephrology-RAG-MCP-tool.git
cd Nephrology-RAG-MCP-tool
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Set up environment variables

Create a `.env` file in the root directory:

```bash
# .env
MISTRAL_API_KEY=your_mistral_api_key_here
```

Or set directly:

```bash
export MISTRAL_API_KEY="your_api_key"          # Linux/Mac
set MISTRAL_API_KEY=your_api_key               # Windows CMD
$env:MISTRAL_API_KEY="your_api_key"            # Windows PowerShell
```

### 4️⃣ Run the MCP server

```bash
python rag_mcp_server.py
```

Server will start on `http://0.0.0.0:8000` by default.

---

## 🧪 Testing

### Test Locally (Server Running)

```bash
# Install test requirements
pip install requests

# Run comprehensive test suite
python test_mcp_server.py

# Test specific port
python test_mcp_server.py --url http://localhost:8080/mcp

# Test remote deployment (Cloud Run)
python test_mcp_server.py --url https://nephrology-rag-mcp-xxxxx-uc.a.run.app/mcp
```

The test suite validates:

- ✅ Server connectivity
- ✅ MCP protocol compliance
- ✅ Vector store functionality
- ✅ Retrieval quality
- ✅ Parameter validation

### Manual Testing with cURL

**Health check:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc":"2.0",
    "method":"health",
    "params":{},
    "id":1
  }'
```

**Query the RAG system:**

```bash
curl -X POST http://localhost:8000/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc":"2.0",
    "method":"invoke",
    "params":{"query":"acute kidney injury diagnosis","k":3},
    "id":2
  }'
```

### Test with Python

```python
import requests
import json

# Initialize server
resp = requests.post(
    'http://localhost:8000/mcp',
    json={
        'jsonrpc': '2.0',
        'method': 'initialize',
        'params': {
            'protocolVersion': '2024-11-05',
            'capabilities': {},
            'clientInfo': {'name': 'test-client', 'version': '1.0'}
        },
        'id': 1
    },
    headers={'Accept': 'application/json, text/event-stream'}
)
print(resp.json())

# Query documents
resp = requests.post(
    'http://localhost:8000/mcp',
    json={
        'jsonrpc': '2.0',
        'method': 'invoke',
        'params': {'query': 'glomerulonephritis treatment', 'k': 3},
        'id': 2
    },
    headers={'Accept': 'application/json, text/event-stream'}
)
print(resp.json())
```

---

## 🐳 Docker Deployment

### Build Docker Image

```bash
docker build -t nephrology-rag-mcp:latest .
```

### Run Container Locally

```bash
docker run -d \
  --name nephrology-mcp \
  -p 8080:8080 \
  -e MISTRAL_API_KEY="your_api_key" \
  nephrology-rag-mcp:latest
```

The server will be available on `http://localhost:8080/mcp`.

### Test Docker Container

```bash
# Run test suite against container
python test_mcp_server.py --url http://localhost:8080/mcp
```

---

---

## 🌐 Cloud Deployment

### FastMCP.Cloud (Recommended - One-Click Deploy)

1. Push code to GitHub (already set up)
2. Visit [FastMCP.Cloud](https://fastmcp.cloud)
3. Connect your GitHub repository
4. Deploy with one click
5. Service URL: `https://nephrology-rag-tool.fastmcp.app/mcp`

### Google Cloud Run Deployment

**Prerequisites:**

- Google Cloud account with billing enabled
- `gcloud` CLI installed
- `MISTRAL_API_KEY` secret created in Google Secret Manager

**Deploy:**

```bash
# Ensure you're logged in to Google Cloud
gcloud auth login

# Deploy from source
gcloud run deploy nephrology-rag-mcp \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --timeout 600 \
  --set-env-vars MISTRAL_API_KEY=<your_api_key>
```

Or using secrets:

```bash
# Create secret in Google Secret Manager
echo -n "your_api_key" | gcloud secrets create mistral-api-key --data-file=-

# Deploy with secret reference
gcloud run deploy nephrology-rag-mcp \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --timeout 600 \
  --set-env-vars MISTRAL_API_KEY=<SECRET:mistral-api-key>
```

**Test deployed service:**

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe nephrology-rag-mcp --region us-central1 --format 'value(status.url)')/mcp

# Run tests against deployed service
python test_mcp_server.py --url $SERVICE_URL
```

---

## 🌐 Deployment (FastMCP.Cloud)

This project is designed for **one-click deploy**:

1. Push the following files to your repo:

   - `mcp.json`
   - `requirements.txt`

2. Connect GitHub → FastMCP.Cloud
3. Deploy
4. The platform auto-detects:

   - entrypoint
   - runtime
   - tools
   - dependencies

5. Ready to use in your LLM environment 🎉

**Deployed MCP URL**

The project is deployed at: `https://nephrology-rag-tool.fastmcp.app/mcp`

Example JSON-RPC POST (invoke tool):

```bash
curl -X POST https://nephrology-rag-tool.fastmcp.app/mcp \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","method":"invoke","params":{"query":"treatment options for CKD","k":4},"id":1}'
```

---

## 🧠 What Makes This Project Special

- Medical-domain RAG tuned for Nephrology
- Clean MCP structure
- Fast search with minimal memory footprint
- Perfect for:

  - clinicians building AI assistants
  - LLM agents needing structured retrieval
  - research projects
  - learning MCP tooling
  - hackathon-grade agentic workflows

---

## 🤝 Contributing

Pull requests are welcome!
If you want to add:

- PDF ingestion
- UI
- GPU embeddings
- Extra medical datasets
  — feel free to open an issue.

---

## 📜 License

MIT License — free for personal & commercial use.

---

## ⭐ Support

If you find this project helpful, give it a **star** ⭐ on GitHub!

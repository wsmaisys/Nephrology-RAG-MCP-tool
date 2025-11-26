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

## 🛠️ Installation (Local)

### 1️⃣ Clone the repo

```bash
git clone https://github.com/wsmaisys/Nephrology-RAG-MCP-tool.git
cd Nephrology-RAG-MCP-tool
```

### 2️⃣ Install dependencies

(After you push `requirements.txt`)

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the MCP server

```bash
python rag_mcp_server.py
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

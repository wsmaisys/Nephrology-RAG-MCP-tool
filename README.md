**Nephrology RAG MCP Tool**

- **Repository:** `Nephrology_RAG_mcp_tool`
- **Purpose:** Provides a small MCP (Microservice Control Plane) server that exposes a Retrieval-Augmented Generation (RAG) retrieval tool preloaded with a FAISS vector store containing nephrology documents. It is intended for internal/dev use to query domain documents (PDFs) and return the most relevant chunks as structured JSON via FastMCP.
- **Use Case:** Rapidly prototype or serve a domain-specific RAG retriever for clinical or research workflows where you need to fetch relevant excerpts from a curated nephrology knowledge base and integrate retrieval as an MCP tool for other services or agents.

**Features**

- **Pre-built FAISS vector store:** The repository expects a local `vector_store/` directory containing a FAISS index (`index.faiss`) and associated metadata.
- **Mistral embeddings integration:** Uses `langchain_mistralai` to compute embeddings when rebuilding the index or running embedding operations.
- **FastMCP server:** Exposes two MCP tools: `invoke` (retrieve relevant chunks) and `health` (service status), and a resource descriptor `rag:///Nephrology-RAG-Tool`.

**Quick Start / Prerequisites**

- **Python:** 3.11+ recommended (project tested with a venv). Use `python -m venv .venv` and install packages.
- **Dependencies:** The project uses `langchain-mistralai`, `langchain-community`, `fastmcp`, and FAISS-related packages. Install via your package manager (`pip`, `pipx`, or the project's lockfile depending on your environment).
- **Vector store:** The repo contains a pre-built `vector_store/` directory. If you need to rebuild it, use your own ingestion/embedding steps (not included here).

**Configuration**

- **Environment variables:**
  - `MISTRALAI_API_KEY`: (required) API key used by `langchain_mistralai`. Must be non-empty to avoid invalid `Authorization: Bearer ` headers.
  - Optional: `MCP_REQUEST_TIMEOUT` (not implemented by default) — you can modify `rag_mcp_server.py` to read this and pass into `mcp.run(...)` if desired.
- **.env file:** You may use a `.env` file in the repository root with `MISTRALAI_API_KEY=your_key_here`. The server code accepts several common names (e.g. `MISTRAL_API_KEY`) but ignores empty values to avoid illegal Authorization headers.

**Run the server (local)**

1. Create and activate a venv (PowerShell example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Ensure `MISTRALAI_API_KEY` is set in your environment or `.env` (non-empty):

```powershell
$env:MISTRALAI_API_KEY = "your_mistral_api_key_here"
```

3. Start the server:

```powershell
python .\rag_mcp_server.py
```

The server will attempt to configure `request_timeout` at runtime if supported by your FastMCP release; otherwise it falls back to a compatible start mode.

**Using the MCP tool**

- The repository exposes an MCP tool named `invoke` which accepts a single `query` string (and optional `k` for number of results). How you call the MCP tool depends on your MCP client. Example conceptual HTTP POST (the FastMCP HTTP transport receives MCP JSON-RPC requests):

```json
{
  "jsonrpc": "2.0",
  "method": "invoke",
  "params": { "query": "Find treatment options for CKD", "k": 4 },
  "id": 1
}
```

- The `invoke` tool returns JSON with keys: `status`, `query`, `context` (array of chunk text), `metadata`, and `num_results`.

**Health check**

- Call the `health` tool (no args) via MCP to confirm the retriever and vector store are loaded. It returns `status: ok` when ready.

**Troubleshooting**

- Error: `httpx.LocalProtocolError: Illegal header value b'Bearer '` — means an empty `MISTRALAI_API_KEY` was present. Fix: set `MISTRALAI_API_KEY` to a non-empty value or remove empty keys from your `.env`.
- Warning: `RequestResponder must be used as a context manager` or `notifications/cancelled` with `McpError: Request timed out` — likely caused by a handler blocking the event loop. The server runs retriever calls inside threads using `asyncio.to_thread` to avoid blocking; ensure your FastMCP release is up-to-date and configure `request_timeout` on `mcp.run(...)` if supported.
- If the server fails to start with `TypeError: FastMCP.__init__() got an unexpected keyword argument 'request_timeout'`, edit the constructor call to remove unsupported kwargs (current code uses a minimal constructor and attempts to set the timeout at runtime with a safe fallback).

**Development notes**

- `rag_mcp_server.py` contains the key logic. Important functions:
  - `_load_vector_store()` — loads FAISS index and creates the retriever.
  - `invoke(query, k=4)` — MCP tool that returns the most relevant document chunks for `query`.
- The code will raise a clear `EnvironmentError` on startup if `MISTRALAI_API_KEY` is not set (to avoid sending invalid Authorization headers).

**Next steps / suggestions**

- If you want streaming responses or interim notifications, implement FastMCP's RequestResponder as a context manager within tool handlers.
- Make `MCP` runtime options configurable via environment variables (`MCP_REQUEST_TIMEOUT`) for easier deployment.
- Add a small test harness script or example MCP client to demo `invoke` requests.

If you want, I can add an example client script (MCP HTTP or JSON-RPC) to this repo to demonstrate calling the `invoke` tool and parsing results.

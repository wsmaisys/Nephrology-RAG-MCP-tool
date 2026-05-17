# 🧬 Nephrology RAG MCP Tool

Public MCP-compatible retrieval service for nephrology education context.

This service is intentionally deployable and usable independently from MediFlow. MediFlow is one consumer, but the MCP endpoint is designed so any MCP-compatible client can query the nephrology knowledge base without needing direct access to embeddings, FAISS files, or Mistral credentials.

## 🎯 Purpose

- Expose a public nephrology knowledge base through HTTP JSON-RPC and SSE.
- Serve any MCP-compatible client, not only the MediFlow medical assistant.
- Keep Mistral embeddings and the FAISS vector store on the server side.
- Return retrieved document chunks plus metadata so downstream agents can cite and reason over grounded context.
- Provide a clean public contract that is stable enough for independent deployment and reuse.

The service returns educational retrieval context only. It does not diagnose, prescribe, triage, or replace clinician judgment.

## 🌐 Public Endpoint

```text
https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app/mcp
```

Manifest:

```text
https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app/mcp.json
```

Health checks:

```text
GET /health   process health, may return ready=false while vector store is loading
GET /ready    readiness; returns 503 until vector store is available
```

## 🧰 MCP Tools

### `query_nephrology_docs`

Retrieve top-k relevant document chunks.

Arguments:

- `query` string, required
- `k` integer, optional, default `4`, capped by `MAX_K`
- `session_id` string, optional

Returns:

- `status`
- `query`
- `context`
- `metadata`
- `num_results`
- `session_id`
- `server`
- `tool`

### `get_server_info`

Returns readiness, endpoint, capabilities, configuration limits, and session metadata.

## 🔁 Example JSON-RPC Call

```bash
curl -X POST https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "query-1",
    "method": "tools/call",
    "params": {
      "name": "query_nephrology_docs",
      "arguments": {
        "query": "acute kidney injury management",
        "k": 4
      }
    }
  }'
```

## 📡 Example SSE Call

```bash
curl -N -X POST https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "jsonrpc": "2.0",
    "id": "stream-1",
    "method": "tools/call",
    "params": {
      "name": "query_nephrology_docs",
      "transport": "http/sse",
      "arguments": {
        "query": "chronic kidney disease stages",
        "k": 3
      }
    }
  }'
```

## ⚙️ Local Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create `.env`:

```env
MISTRAL_API_KEY=your_mistral_api_key
HOST=0.0.0.0
PORT=8000
DEFAULT_K=4
MAX_K=10
MAX_QUERY_CHARS=1000
PUBLIC_BASE_URL=http://localhost:8000
```

Run:

```bash
python rag_mcp_server.py
```

## ✅ Testing

```bash
pytest test_mcp_contract.py -q
```

The contract tests validate the public manifest, tool schema, JSON-RPC behavior, and readiness expectations.

## ☁️ Deployment

This service is designed for independent auto-deploy from its own repository. Cloud Run should provide:

- `MISTRAL_API_KEY`
- `PUBLIC_BASE_URL=https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app`
- optional `DEFAULT_K`
- optional `MAX_K`
- optional `MAX_QUERY_CHARS`

The service is public by design. Clients do not send Mistral keys. If abuse protection is needed later, add gateway-level rate limiting rather than coupling this server to MediFlow authentication.

## 🤝 MediFlow Integration Contract

MediFlow should point to this service with:

```env
NEPHROLOGY_MCP_URL=https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app/mcp
```

MediFlow remains responsible for:

- patient verification
- patient context
- clinical prompting
- safety disclaimers
- deciding when to use RAG vs web search

This MCP service remains responsible for:

- vector store loading
- nephrology semantic retrieval
- public MCP-compatible JSON-RPC and SSE responses
- returning retrieved context with metadata for downstream grounding

## 🛡️ Safety Notes

- Retrieval output is educational context, not medical advice.
- Downstream assistants must decide how to present, cite, and qualify retrieved context.
- Patient-specific decisions must come from the consuming clinical application, not this retrieval service.
- Keep Mistral credentials server-side; never expose them to public clients.

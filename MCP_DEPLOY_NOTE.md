**MCP Server Deploy Notes**

- **Purpose:** Minimal deployment & CI notes so the `Nephrology-RAG-MCP-tool` server exposes a production-ready HTTP MCP endpoint compatible with `langchain_mcp_adapters`.

- **Place manifest:** Copy `mcp.json` to the repository root of `Nephrology-RAG-MCP-tool` (next to `rag_mcp_server.py`). This file is used for tool discovery.

- **Environment variables:** Ensure the Mistral API key is set in the server environment. Supported names (the server checks in order): `MISTRALAI_API_KEY`, `MISTRAL_API_KEY`, `mistral_api_key`.

- **FastMCP & dependencies:** Use the FastMCP version declared in `pyproject.toml` / `requirements.txt` (recommended `fastmcp>=2.13.1`). Confirm the deployed image installs the same versions.

**Local build & test (Docker)**

1. Build the image locally from the server repo root:

```bash
# From the Nephrology-RAG-MCP-tool repo root
docker build -t nephrology-rag-mcp:latest .
```

2. Run locally (forward port 8000):

```bash
docker run --rm -e MISTRALAI_API_KEY="$MISTRALAI_API_KEY" -p 8000:8000 nephrology-rag-mcp:latest
```

3. Test health locally:

```bash
curl -X POST http://localhost:8000/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","method":"health","params":{},"id":1}'
```

**Google Cloud Run (example)**

1. Build and push (gcloud):

```bash
# Set your project and region
gcloud config set project YOUR_PROJECT_ID
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/nephrology-rag-mcp:latest
```

2. Deploy to Cloud Run:

```bash
gcloud run deploy nephrology-rag-mcp \
  --image gcr.io/YOUR_PROJECT_ID/nephrology-rag-mcp:latest \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars MISTRALAI_API_KEY=$MISTRALAI_API_KEY
```

**GitHub Actions snippet (optional)**

Create `.github/workflows/deploy.yml` with a build-and-deploy job that:

- Builds Docker image, pushes to registry
- Deploys to Cloud Run (or your platform)


**Compatibility checklist for `langchain_mcp_adapters` clients**

- Ensure MCP endpoint URL is stable (e.g., `https://.../mcp`).
- Clients must pass `transport` in their config (e.g., `streamable_http` or `sse`).
- Clients should include header: `Accept: application/json, text/event-stream`.
- Server now accepts session via: top-level `session` field, `params.session`, `session` query param, or `X-FastMCP-Session` header (middleware injects session if missing).

**Notes & troubleshooting**

- If clients still get "Missing session ID", confirm the deployed FastMCP version supports `require_session=False`. If not, upgrade FastMCP in the image and redeploy.
- If the server returns `406 Not Acceptable`, verify the client `Accept` header includes both `application/json` and `text/event-stream`.
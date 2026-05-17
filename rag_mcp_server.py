#!/usr/bin/env python3
"""
rag_mcp_server.py

Production-ready MCP server for nephrology document retrieval.
- Uses FAISS (CPU only) to store/retrieve document embeddings.
- Bundles a pre-built FAISS index (in VECTOR_STORE_PATH) into the container.
- Uses langchain_mistralai for embeddings (model="mistral-embed").
- MISTRAL_API_KEY is read from environment (set via Cloud Run secret).
- Exposes one MCP tool 'query_nephrology_docs', supports streaming via SSE.
- No authentication; streaming via HTTP (Server-Sent Events).
- Reads $PORT (fallback 8000) for host binding (Cloud Run compatible).
- Does not include "transport" in the response payloads.
"""
import os, sys, time, json, uuid, asyncio, traceback, logging
from typing import Optional, Dict, Any, List, AsyncGenerator, Callable
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# -
# Load dotenv for local development
from dotenv import load_dotenv
load_dotenv()
# Configuration (single secret)
# ---------------------------
APP_NAME = "nephrology-rag-mcp"
APP_VERSION = "1.0.0"
VECTOR_STORE_PATH = "vector_store"
DEFAULT_K = int(os.environ.get("DEFAULT_K", "4"))
MAX_K = int(os.environ.get("MAX_K", "10"))
MAX_QUERY_CHARS = int(os.environ.get("MAX_QUERY_CHARS", "1000"))
PUBLIC_BASE_URL = os.environ.get(
    "PUBLIC_BASE_URL",
    "https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app",
).rstrip("/")

# Load .env for local development (if present)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Read Mistral API key (set via Cloud Run secret)
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    print("WARNING: MISTRAL_API_KEY not set; embeddings will fail.", file=sys.stderr)
else:
    # Some libraries look for alternative names
    os.environ.setdefault("MISTRALAI_API_KEY", MISTRAL_API_KEY)
    os.environ.setdefault("MISTRAL_APIKEY", MISTRAL_API_KEY)

# ---------------------------
# Logging
# ---------------------------
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(APP_NAME)

# ---------------------------
# Lifespan event handler for startup/shutdown
# ---------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s starting (pid=%s)", APP_NAME, os.getpid())
    logger.info("VECTOR_STORE_PATH=%s", VECTOR_STORE_PATH)
    # Load FAISS vector store at startup
    success = await asyncio.get_event_loop().run_in_executor(None, _load_vector_store)
    if success:
        logger.info("Vector store loaded successfully at startup.")
    else:
        logger.warning("Vector store failed to load; server will start but retrievals will error.")
    yield
    logger.info("%s shutting down", APP_NAME)

# ---------------------------
# FastAPI app (MCP server)
# ---------------------------
app = FastAPI(title=APP_NAME, version=APP_VERSION, lifespan=lifespan)
# Public knowledge service: allow browser and MCP clients by default.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], 
                   allow_headers=["*"], allow_credentials=False)

# ---------------------------
# In-memory state
# ---------------------------
_sessions: Dict[str, Dict[str, Any]] = {}
_vector_store = None
_retriever = None

def _create_session(session_id: Optional[str] = None) -> str:
    """Create or reuse a session ID for tracking."""
    if session_id and session_id in _sessions:
        return session_id
    sid = session_id or str(uuid.uuid4())
    _sessions[sid] = {"created_at": time.time(), "query_count": 0, 
                      "last_query": None, "last_seen": time.time()}
    logger.debug("Session created: %s", sid)
    return sid

def _update_session(session_id: str, query: str):
    """Update session stats for each query."""
    s = _sessions.get(session_id)
    if not s: 
        return
    s["query_count"] += 1
    s["last_query"] = query
    s["last_seen"] = time.time()

# ---------------------------
# Load FAISS vector store (with Mistral embeddings)
# ---------------------------
def _load_vector_store() -> bool:
    """
    Load FAISS index from disk. Uses langchain_mistralai for embeddings
    and LangChain's FAISS.load_local for the vector store:contentReference[oaicite:1]{index=1}.
    """
    global _vector_store, _retriever
    try:
        from langchain_mistralai import MistralAIEmbeddings
        from langchain_community.vectorstores import FAISS

        if not MISTRAL_API_KEY:
            logger.error("MISTRAL_API_KEY not set; cannot initialize embeddings")
            return False

        logger.info("Loading FAISS vector store from %s", VECTOR_STORE_PATH)
        logger.info("Using Mistral API (https://api.mistral.ai/v1/embeddings, model=mistral-embed)")

        # Instantiate embeddings model (Mistral)
        try:
            embeddings = MistralAIEmbeddings(model="mistral-embed", api_key=MISTRAL_API_KEY)
        except TypeError:
            embeddings = MistralAIEmbeddings(model="mistral-embed")

        # Load FAISS vector store
        # Some pickled LangChain metadata may have been created with different
        # pydantic internals and miss the '__fields_set__' key. That causes
        # a KeyError inside pydantic's BaseModel.__setstate__ when unpickling.
        # To be resilient, temporarily monkeypatch pydantic.v1.BaseModel.__setstate__
        # to supply a default '__fields_set__' and then restore it after load.
        _pyd_original_setstate = None
        _pyd_module = None
        try:
            try:
                import pydantic.v1.main as _pyd_v1_main
                _pyd_module = _pyd_v1_main
            except Exception:
                # pydantic v1 not present as v1 namespace; try fallback
                import pydantic.main as _pyd_main
                _pyd_module = _pyd_main
            if _pyd_module and hasattr(_pyd_module, 'BaseModel'):
                _pyd_original_setstate = getattr(_pyd_module.BaseModel, '__setstate__', None)
                def _safe_setstate(self, state):
                    try:
                        if isinstance(state, dict) and '__fields_set__' not in state:
                            state['__fields_set__'] = set()
                    except Exception:
                        pass
                    if _pyd_original_setstate:
                        return _pyd_original_setstate(self, state)
                    # best-effort fallback
                    try:
                        object.__setattr__(self, '__dict__', state)
                    except Exception:
                        pass
                _pyd_module.BaseModel.__setstate__ = _safe_setstate
                logger.info("Patched pydantic BaseModel.__setstate__ for compatibility during unpickle")
        except Exception as ex:
            logger.debug("Could not apply pydantic monkeypatch: %s", ex)

        try:
            _vector_store = FAISS.load_local(
                VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True
            )
        finally:
            # restore original setstate if we patched it
            try:
                if _pyd_module and _pyd_original_setstate is not None:
                    _pyd_module.BaseModel.__setstate__ = _pyd_original_setstate
                    logger.info("Restored original pydantic BaseModel.__setstate__")
            except Exception:
                logger.debug("Failed to restore pydantic BaseModel.__setstate__")
        _retriever = _vector_store.as_retriever(search_type="similarity",
                                                search_kwargs={"k": DEFAULT_K})
        return True

    except Exception as e:
        logger.error("Failed to load FAISS vector store: %s", e)
        # Ensure full traceback is visible in logs (INFO/ERROR may be captured by Cloud Run)
        tb = traceback.format_exc()
        logger.error("Full exception traceback:\n%s", tb)
        # Log Python runtime info to help diagnose deserialization mismatches
        try:
            logger.error("Python executable: %s", sys.executable)
            logger.error("Python version: %s", sys.version.replace('\n', ' '))
        except Exception:
            logger.error("Could not read Python version info")
        # Log installed packages (pip freeze) truncated to avoid excessively large logs
        try:
            import subprocess
            pip_output = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True, stderr=subprocess.STDOUT)
            # Truncate to first 32000 characters to be safe for log ingestion
            max_len = 32000
            if len(pip_output) > max_len:
                logger.error("pip freeze (truncated):\n%s", pip_output[:max_len])
            else:
                logger.error("pip freeze:\n%s", pip_output)
        except Exception:
            logger.error("Failed to run pip freeze: %s", traceback.format_exc())

        _vector_store = None
        _retriever = None
        return False

# ---------------------------
# Retriever helper (sync) for compatibility
# ---------------------------
def _sync_retrieve(retriever, query: str, k: int) -> List[Any]:
    """Sync wrapper to call retriever in executor (handles different LangChain versions)."""
    if retriever is None:
        raise RuntimeError("Retriever not initialized")
    # Try new invoke() API if available (LangChain 0.1.46+)
    if hasattr(retriever, "invoke"):
        res = retriever.invoke(query)
        return res if isinstance(res, list) else [res]
    # Fallback to legacy methods
    if hasattr(retriever, "similarity_search"):
        try:
            return retriever.similarity_search(query, k=k)
        except TypeError:
            return retriever.similarity_search(query, k)
    if hasattr(retriever, "get_relevant_documents"):
        return retriever.get_relevant_documents(query)[:k]
    if hasattr(retriever, "retrieve"):
        return retriever.retrieve(query)[:k]
    if hasattr(retriever, "search"):
        return retriever.search(query)[:k]
    if hasattr(retriever, "similarity_search_with_score"):
        results = retriever.similarity_search_with_score(query, k=k)
        return [r for r,score in results]
    raise RuntimeError("Unsupported retriever API")

# ---------------------------
# MCP tools registry
# ---------------------------
ToolFunc = Callable[[Dict[str, Any]], Any]
TOOLS: Dict[str, ToolFunc] = {}

def tool(name: str):
    """Decorator to register a tool by name."""
    def deco(fn: ToolFunc):
        TOOLS[name] = fn
        return fn
    return deco

def _tool_schema(name: str, description: str, input_schema: Dict[str, Any]) -> Dict[str, Any]:
    return {"name": name, "description": description, "input_schema": input_schema}

def _public_tools() -> List[Dict[str, Any]]:
    return [
        _tool_schema(
            "query_nephrology_docs",
            "Retrieve top-k nephrology document chunks for a natural-language clinical education query.",
            {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "maxLength": MAX_QUERY_CHARS},
                    "k": {"type": "integer", "default": DEFAULT_K, "minimum": 1, "maximum": MAX_K},
                    "session_id": {"type": "string"},
                },
                "required": ["query"],
            },
        ),
        _tool_schema("get_server_info", "Return service metadata and readiness.", {"type": "object", "properties": {}}),
    ]

def _public_manifest() -> Dict[str, Any]:
    return {
        "name": "Nephrology RAG MCP",
        "description": "Public MCP server providing retrieval-augmented nephrology education context.",
        "version": APP_VERSION,
        "endpoint": f"{PUBLIC_BASE_URL}/mcp",
        "transport": "streamable_http",
        "auth": {"required": False},
        "limits": {"max_results_per_query": MAX_K, "max_query_chars": MAX_QUERY_CHARS},
        "tools": _public_tools(),
    }

@tool("query_nephrology_docs")
async def query_nephrology_docs(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve top-K documents for the query. Returns JSON:
    { status, query, context, metadata, num_results, session_id }.
    Does NOT include 'transport' in the response.
    """
    query = params.get("query") or params.get("q") or ""
    k = max(1, min(int(params.get("k", DEFAULT_K)), MAX_K))
    session_id = params.get("session_id")

    if not query:
        return {"status": "error", "message": "Missing 'query' parameter."}
    if len(query) > MAX_QUERY_CHARS:
        return {"status": "error", "message": f"Query is too long. Maximum length is {MAX_QUERY_CHARS} characters."}
    if _retriever is None:
        return {"status": "error", "message": "Vector store not initialized."}

    sid = _create_session(session_id)
    _update_session(sid, query)

    try:
        docs = await asyncio.get_event_loop().run_in_executor(
            None, _sync_retrieve, _retriever, query, k
        )
    except Exception as exc:
        logger.exception("Retrieval error")
        return {"status": "error", "message": f"Retrieval failed: {str(exc)}"}

    context = []
    metadata = []
    for doc in docs[:k]:
        if isinstance(doc, dict):
            content = doc.get("page_content") or doc.get("content") or doc.get("text") or ""
            meta = doc.get("metadata", {})
        else:
            content = getattr(doc, "page_content", "") or getattr(doc, "content", "") or str(doc)
            meta = getattr(doc, "metadata", {})
        context.append(content)
        metadata.append(meta)

    return {
        "status": "success",
        "query": query,
        "context": context,
        "metadata": metadata,
        "num_results": len(context),
        "session_id": sid,
        "server": APP_NAME,
        "tool": "query_nephrology_docs",
        "usage_note": "Educational retrieval context only; not a medical diagnosis or treatment recommendation.",
    }

@tool("get_server_info")
async def get_server_info(params: Dict[str, Any]) -> Dict[str, Any]:
    """Return server status and metadata (for discovery)."""
    sid = params.get("session_id")
    info = _sessions.get(sid) if sid else None
    return {
        "status": "ready" if _retriever is not None else "not_ready",
        "server_name": APP_NAME,
        "version": APP_VERSION,
        "transport": "http/sse",
        "retriever_initialized": _retriever is not None,
        "active_sessions": len(_sessions),
        "session_info": info,
        "public_base_url": PUBLIC_BASE_URL,
        "mcp_endpoint": f"{PUBLIC_BASE_URL}/mcp",
        "capabilities": {"streaming": True, "multi_user": True, "max_results_per_query": MAX_K, "max_query_chars": MAX_QUERY_CHARS},
        "usage_note": "Educational retrieval context only; not a medical diagnosis or treatment recommendation.",
    }

async def _invoke_tool(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a registered tool by name with given args."""
    if tool_name not in TOOLS:
        return {"status": "error", "message": f"Tool '{tool_name}' not found."}
    try:
        return await TOOLS[tool_name](args or {})
    except Exception as exc:
        logger.exception("Tool invocation failed: %s", tool_name)
        return {"status": "error", "message": f"Invocation failed: {str(exc)}"}

# ---------------------------
# SSE (Server-Sent Events) helpers for streaming responses
# ---------------------------
def sse_format(data: str, event: Optional[str] = None, id: Optional[str] = None) -> str:
    """Format a single SSE event."""
    lines = []
    if id is not None:   lines.append(f"id: {id}")
    if event is not None: lines.append(f"event: {event}")
    for line in data.splitlines():
        lines.append(f"data: {line}")
    lines.append("")  # blank line terminates the SSE event
    return "\n".join(lines) + "\n"

async def _stream_query_nephrology_docs(args: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
    """
    Stream chunks of retrieved documents for query_nephrology_docs.
    Sends status:start, chunk events, then status:completed.
    """
    query = args.get("query") or ""
    k = max(1, min(int(args.get("k", DEFAULT_K)), MAX_K))
    session_id = args.get("session_id")
    if not query:
        yield sse_format(json.dumps({"status": "error", "message": "Missing 'query' parameter."}), event="mcp.error").encode("utf-8")
        return
    if len(query) > MAX_QUERY_CHARS:
        yield sse_format(json.dumps({"status": "error", "message": f"Query is too long. Maximum length is {MAX_QUERY_CHARS} characters."}), event="mcp.error").encode("utf-8")
        return
    sid = _create_session(session_id)
    _update_session(sid, query)

    # Send a "started" event
    yield sse_format(json.dumps({
        "status": "started", "tool": "query_nephrology_docs", "session_id": sid
    }), event="mcp.status").encode("utf-8")

    try:
        docs = await asyncio.get_event_loop().run_in_executor(
            None, _sync_retrieve, _retriever, query, k
        )
        for idx, doc in enumerate(docs[:k]):
            if isinstance(doc, dict):
                content = doc.get("page_content") or doc.get("content") or doc.get("text") or ""
                meta = doc.get("metadata", {})
            else:
                content = getattr(doc, "page_content", "") or getattr(doc, "content", "") or str(doc)
                meta = getattr(doc, "metadata", {})
            payload = {"index": idx, "content": content, "metadata": meta, "session_id": sid, "tool": "query_nephrology_docs"}
            yield sse_format(json.dumps(payload), event="mcp.chunk", id=str(idx)).encode("utf-8")
            await asyncio.sleep(0.01)  # small pause for client processing

        # Send a "completed" event
        yield sse_format(json.dumps({
            "status": "completed", "num_results": min(len(docs), k), "session_id": sid
        }), event="mcp.complete").encode("utf-8")
    except Exception as exc:
        logger.exception("Streaming retrieval error")
        err = {"status": "error", "message": str(exc)}
        yield sse_format(json.dumps(err), event="mcp.error").encode("utf-8")

async def _stream_tool_invocation(tool_name: str, args: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
    """
    Dispatch streaming or non-streaming responses. For query_nephrology_docs, stream chunks.
    For others, send one result event.
    """
    if tool_name == "query_nephrology_docs":
        if _retriever is None:
            # Error if retriever is missing
            yield sse_format(json.dumps({"status": "error", "message": "Vector store not ready"}), event="mcp.error").encode("utf-8")
            return
        async for chunk in _stream_query_nephrology_docs(args):
            yield chunk
        return

    # Non-streaming: single JSON result
    result = await _invoke_tool(tool_name, args)
    yield sse_format(json.dumps(result), event="mcp.result").encode("utf-8")

# ---------------------------
# HTTP routes: health, root, MCP endpoint
# ---------------------------
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "ready": _retriever is not None, "server": APP_NAME}

@app.get("/ready")
async def ready():
    """Readiness endpoint for clients that require vector-store availability."""
    status_code = 200 if _retriever is not None else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if _retriever is not None else "not_ready", "server": APP_NAME},
    )

@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {"server": APP_NAME, "version": APP_VERSION,
            "transport": "http/sse", 
            "status": "ready" if _retriever is not None else "starting",
            "mcp_endpoint": "/mcp",
            "tools": list(TOOLS.keys())}

@app.get("/mcp.json")
async def mcp_manifest():
    """Public manifest describing the MCP service contract."""
    return _public_manifest()

@app.post("/mcp")
async def mcp_endpoint(request: Request, 
                       accept: Optional[str] = Header(None),
                       x_session_id: Optional[str] = Header(None)):
    """
    MCP JSON-RPC endpoint. Expects a JSON-RPC body with method "tools/call".
    Supports SSE streaming if the client requests "text/event-stream" (SSE) via Accept header
    or transport="http/sse". Discovery via "mcp.discover" is also supported.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Invalid JSON-RPC structure")

    req_id = body.get("id")
    method = body.get("method")
    params = body.get("params") or {}

    # Discovery (tool list)
    if method == "mcp.discover":
        meta = {
            "name": APP_NAME,
            "version": APP_VERSION,
            "transport": "http/sse",
            "endpoint": f"{PUBLIC_BASE_URL}/mcp",
            "auth": {"required": False},
            "tools": _public_tools(),
        }
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": meta})

    # Support simple tools listing via `tools/list`
    if method == "tools/list":
        meta = {"tools": _public_tools()}
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": meta})

    if method != "tools/call":
        raise HTTPException(status_code=400, detail="Unsupported method")

    tool_name = params.get("name")
    args = params.get("arguments") or {}
    # Session ID from header overrides
    if x_session_id:
        args.setdefault("session_id", x_session_id)

    # Determine if client wants SSE
    accept_hdr = accept or ""
    wants_sse = "text/event-stream" in accept_hdr.lower()
    client_transport = (params.get("transport") or "http").lower()
    if client_transport in ("http/sse", "sse", "stream"):
        wants_sse = True

    if wants_sse:
        headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        return StreamingResponse(_stream_tool_invocation(tool_name, args),
                                 media_type="text/event-stream", headers=headers)
    else:
        # JSON (non-streaming) response
        result = await _invoke_tool(tool_name, args)
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": result})

# ---------------------------
# Main (Cloud Run entry point)
# ---------------------------
def _main():
    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0"
    # Run with a single worker to keep in-memory vector store consistent
    uvicorn.run("rag_mcp_server:app", host=host, port=port, 
                log_level="info", workers=1, timeout_keep_alive=120)

if __name__ == "__main__":
    _main()

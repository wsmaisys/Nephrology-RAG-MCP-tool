#!/usr/bin/env python3
"""
rag_mcp_server.py

Production-ready MCP server with HTTP/SSE transport (true streaming).
- Public (no auth).
- Uses only MISTRAL_API_KEY from environment (Cloud Run secret).
- Reads PORT from environment for Cloud Run compatibility.
- Streams document chunks as SSE events for "query_nephrology_docs".
- Exposes /health and MCP JSON-RPC endpoint /mcp.
"""

import os
import sys
import time
import json
import uuid
import asyncio
import traceback
from typing import Optional, Dict, Any, AsyncGenerator, Callable, List

# Ensure required packages are available in your image:
# fastapi, uvicorn[standard], langchain, langchain-mistralai, langchain-community, faiss-cpu, python-dotenv
from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

# ---------- Configuration ----------
APP_NAME = "nephrology-rag-mcp"
APP_VERSION = "1.0.0"
VECTOR_STORE_PATH = "vector_store"  # bundled into image
DEFAULT_K = 4

# Only environment variable the app reads from secrets: MISTRAL_API_KEY
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
if not MISTRAL_API_KEY:
    # Continue startup but warn loudly — Cloud Run secret must provide this
    print("WARNING: MISTRAL_API_KEY not set. Embeddings/LLM calls will fail.", file=sys.stderr)
else:
    # Map to library-expected variable (internal only)
    os.environ["MISTRALAI_API_KEY"] = MISTRAL_API_KEY

# ---------- Logging ----------
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(APP_NAME)

# ---------- FastAPI app ----------
app = FastAPI(title=APP_NAME, version=APP_VERSION)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

# ---------- In-memory state ----------
_sessions: Dict[str, Dict[str, Any]] = {}
_vector_store = None
_retriever = None

def _create_session(session_id: Optional[str] = None) -> str:
    if session_id and session_id in _sessions:
        return session_id
    sid = session_id or str(uuid.uuid4())
    _sessions[sid] = {"created_at": time.time(), "query_count": 0, "last_query": None, "last_seen": time.time()}
    logger.debug("Created session %s", sid)
    return sid

def _update_session(session_id: str, query: str):
    s = _sessions.get(session_id)
    if not s:
        return
    s["query_count"] = s.get("query_count", 0) + 1
    s["last_query"] = query
    s["last_seen"] = time.time()

# ---------- Vector store loader (FAISS compatibility) ----------
def _load_vector_store() -> bool:
    global _vector_store, _retriever
    try:
        # Lazy import to fail only at runtime if packages missing
        from langchain_mistralai import MistralAIEmbeddings
        try:
            from langchain_community.vectorstores import FAISS
        except Exception:
            # fallback to main langchain package location
            from langchain.vectorstores import FAISS

        logger.info("Loading vector store from %s", VECTOR_STORE_PATH)
        embeddings = MistralAIEmbeddings(model="mistral-embed")
        _vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)
        # best-effort retriever
        try:
            _retriever = _vector_store.as_retriever(search_type="similarity", search_kwargs={"k": DEFAULT_K})
        except Exception:
            _retriever = _vector_store
        logger.info("Vector store loaded successfully")
        return True
    except Exception as exc:
        logger.error("Failed to load vector store: %s", exc)
        logger.debug(traceback.format_exc())
        _vector_store = None
        _retriever = None
        return False

# ---------- Retriever compatibility wrapper ----------
def _sync_retrieve(retriever, query: str, k: int) -> List[Any]:
    if retriever is None:
        raise RuntimeError("Retriever not initialized")
    # try typical method names in order
    if hasattr(retriever, "get_relevant_documents"):
        return retriever.get_relevant_documents(query)[:k]
    if hasattr(retriever, "similarity_search"):
        try:
            return retriever.similarity_search(query, k=k)[:k]
        except TypeError:
            return retriever.similarity_search(query, k)[:k]
    if hasattr(retriever, "retrieve"):
        return retriever.retrieve(query)[:k]
    if hasattr(retriever, "search"):
        return retriever.search(query)[:k]
    if hasattr(retriever, "invoke"):
        return retriever.invoke(query)[:k]
    if hasattr(retriever, "similarity_search_with_score"):
        results = retriever.similarity_search_with_score(query, k=k)
        return [r[0] for r in results][:k]
    raise RuntimeError("Unrecognized retriever API")

# ---------- Tools registry ----------
TOOLS: Dict[str, Callable[[Dict[str, Any]], Any]] = {}

def tool(name: str):
    def deco(fn):
        TOOLS[name] = fn
        return fn
    return deco

@tool("query_nephrology_docs")
async def query_nephrology_docs(params: Dict[str, Any]) -> Dict[str, Any]:
    query = params.get("query") or params.get("q") or ""
    k = int(params.get("k", DEFAULT_K))
    session_id = params.get("session_id")
    if not query:
        return {"status": "error", "message": "Missing 'query' parameter."}
    if _retriever is None:
        return {"status": "error", "message": "Retriever not initialized; vector store missing or still loading."}
    sid = _create_session(session_id)
    _update_session(sid, query)
    try:
        docs = await asyncio.get_event_loop().run_in_executor(None, _sync_retrieve, _retriever, query, k)
    except Exception as e:
        logger.exception("Retrieval failed")
        return {"status": "error", "message": f"Retrieval failed: {str(e)}"}
    context = []
    metadata = []
    for d in docs[:k]:
        if isinstance(d, dict):
            content = d.get("page_content") or d.get("content") or d.get("text") or ""
            meta = d.get("metadata", {})
        else:
            content = getattr(d, "page_content", None) or getattr(d, "content", None) or str(d)
            meta = getattr(d, "metadata", {})
        context.append(content)
        metadata.append(meta)
    return {"status": "success", "query": query, "context": context, "metadata": metadata,
            "num_results": len(context), "session_id": sid, "server_info": {"model": "mistral-embed"}}

@tool("get_server_info")
async def get_server_info(params: Dict[str, Any]) -> Dict[str, Any]:
    session_id = params.get("session_id")
    session_info = _sessions.get(session_id) if session_id else None
    return {"status": "ready" if _retriever is not None else "not_ready",
            "server_name": APP_NAME, "version": APP_VERSION, "transport": "http/sse",
            "vector_store_path": VECTOR_STORE_PATH, "retriever_initialized": _retriever is not None,
            "active_sessions": len(_sessions), "session_info": session_info,
            "capabilities": {"streaming": True, "multi_user": True, "max_results": 50}}

@tool("list_sessions")
async def list_sessions(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"status": "success", "active_sessions": len(_sessions),
            "sessions": [{"session_id": sid, "query_count": info.get("query_count"), "last_query": info.get("last_query")}
                         for sid, info in _sessions.items()]}

# ---------- Tool runner ----------
async def _invoke_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if tool_name not in TOOLS:
        return {"status": "error", "message": f"Tool '{tool_name}' not found."}
    try:
        result = await TOOLS[tool_name](arguments or {})
        return result
    except Exception as exc:
        logger.exception("Tool invocation failed: %s", tool_name)
        return {"status": "error", "message": f"Tool invocation failed: {str(exc)}"}

# ---------- SSE helpers ----------
def sse_format(data: str, event: Optional[str] = None, id: Optional[str] = None) -> str:
    lines = []
    if id is not None:
        lines.append(f"id: {id}")
    if event is not None:
        lines.append(f"event: {event}")
    for line in data.splitlines():
        lines.append(f"data: {line}")
    lines.append("")  # final newline
    return "\n".join(lines) + "\n"

async def _stream_query_nephrology_docs(arguments: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
    # Streaming pattern:
    # 1) status started
    # 2) emit chunk events for each retrieved doc: event mcp.chunk
    # 3) final mcp.complete with summary
    query = arguments.get("query") or ""
    k = int(arguments.get("k", DEFAULT_K))
    session_id = arguments.get("session_id")
    sid = _create_session(session_id)
    _update_session(sid, query)
    yield sse_format(json.dumps({"status": "started", "tool": "query_nephrology_docs", "session_id": sid}),
                     event="mcp.status").encode("utf-8")
    try:
        docs = await asyncio.get_event_loop().run_in_executor(None, _sync_retrieve, _retriever, query, k)
        # stream each doc as separate event
        for idx, d in enumerate(docs[:k]):
            if isinstance(d, dict):
                content = d.get("page_content") or d.get("content") or d.get("text") or ""
                meta = d.get("metadata", {})
            else:
                content = getattr(d, "page_content", None) or getattr(d, "content", None) or str(d)
                meta = getattr(d, "metadata", {})
            payload = {"index": idx, "content": content, "metadata": meta, "session_id": sid}
            yield sse_format(json.dumps(payload), event="mcp.chunk", id=str(idx)).encode("utf-8")
            # tiny throttle to allow client processing and backpressure friendliness
            await asyncio.sleep(0.01)
        summary = {"status": "completed", "num_results": min(len(docs), k), "session_id": sid}
        yield sse_format(json.dumps(summary), event="mcp.complete").encode("utf-8")
    except Exception as exc:
        logger.exception("Streaming retrieval error")
        err = {"status": "error", "message": str(exc)}
        yield sse_format(json.dumps(err), event="mcp.error").encode("utf-8")

async def _stream_tool_invocation(tool_name: str, arguments: Dict[str, Any]) -> AsyncGenerator[bytes, None]:
    # Delegate streaming to tool-specific streamers if available
    if tool_name == "query_nephrology_docs":
        if _retriever is None:
            yield sse_format(json.dumps({"status": "error", "message": "Retriever not initialized"}), event="mcp.error").encode("utf-8")
            return
        async for chunk in _stream_query_nephrology_docs(arguments):
            yield chunk
        return
    # fallback: single result as an SSE event
    result = await _invoke_tool(tool_name, arguments)
    yield sse_format(json.dumps({"status": "completed", "result": result}), event="mcp.result").encode("utf-8")

# ---------- Routes ----------
@app.get("/health")
async def health():
    return {"status": "ok", "ready": _retriever is not None}

@app.get("/")
async def root():
    return {"server": APP_NAME, "version": APP_VERSION, "transport": "http/sse",
            "status": "ready" if _retriever is not None else "starting"}

@app.post("/mcp")
async def mcp_endpoint(request: Request, accept: Optional[str] = Header(None), x_session_id: Optional[str] = Header(None)):
    """
    Expects MCP JSON-RPC:
    {
      "jsonrpc": "2.0",
      "id": <id>,
      "method": "tools/call",
      "params": {
         "name": "<tool_name>",
         "arguments": { ... }
      }
    }
    Streaming if Accept: text/event-stream requested.
    Session id may be passed via header X-Session-Id or in arguments.session_id.
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

    # support simple discovery
    if method == "mcp.discover":
        meta = {"name": APP_NAME, "version": APP_VERSION, "transport": "http/sse", "tools": list(TOOLS.keys())}
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": meta})

    if method != "tools/call":
        raise HTTPException(status_code=400, detail="Unsupported method")

    tool_name = params.get("name")
    arguments = params.get("arguments") or {}

    if x_session_id:
        arguments.setdefault("session_id", x_session_id)

    wants_sse = accept and "text/event-stream" in accept.lower()

    if wants_sse:
        headers = {"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        return StreamingResponse(_stream_tool_invocation(tool_name, arguments), media_type="text/event-stream", headers=headers)
    else:
        result = await _invoke_tool(tool_name, arguments)
        return JSONResponse(content={"jsonrpc": "2.0", "id": req_id, "result": result})

# ---------- Startup / Shutdown ----------
@app.on_event("startup")
async def startup_event():
    logger.info("="*60)
    logger.info("%s starting (pid=%s)", APP_NAME, os.getpid())
    logger.info("VECTOR_STORE_PATH=%s", VECTOR_STORE_PATH)
    ok = await asyncio.get_event_loop().run_in_executor(None, _load_vector_store)
    if ok:
        logger.info("Vector store loaded successfully at startup")
    else:
        logger.warning("Vector store failed to load at startup; server will still run but retrievals will error")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("%s shutting down", APP_NAME)

# ---------- Entry point ----------
def _main():
    # Cloud Run injects PORT; default to 8000 for local dev
    port = int(os.environ.get("PORT", "8000"))
    host = "0.0.0.0"
    # Run uvicorn with single worker to keep in-memory vectorstore safe
    uvicorn.run("rag_mcp_server:app", host=host, port=port, log_level="info", workers=1, timeout_keep_alive=120)

if __name__ == "__main__":
    _main()
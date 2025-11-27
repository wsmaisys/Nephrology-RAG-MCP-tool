"""Production MCP server with HTTP/SSE transport for multi-user access.

Supports Server-Sent Events (SSE) for streaming responses and follows
MCP protocol standards for enterprise deployment.
"""

import os
import asyncio
import json
import uuid
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

# Normalize Mistral API key
mistral_key = (
    os.environ.get("MISTRALAI_API_KEY") 
    or os.environ.get("MISTRAL_API_KEY") 
    or os.environ.get("mistral_api_key")
)
if mistral_key:
    os.environ["MISTRALAI_API_KEY"] = mistral_key

from fastmcp import FastMCP
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
import uvicorn

# Configuration
VECTOR_STORE_PATH = os.environ.get("VECTOR_STORE_PATH", "vector_store")
DEFAULT_K = 4
API_KEY = os.environ.get("MCP_API_KEY", "Comhensive_book_on_nephrology")  # Optional: for authentication
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# Session management for multi-user
_sessions: Dict[str, Dict[str, Any]] = {}
_vector_store = None
_retriever = None

# Initialize MCP server with CORS support
mcp = FastMCP(
    "nephrology-rag",
    dependencies=[
        Middleware(
            CORSMiddleware,
            allow_origins=ALLOWED_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
)


def _load_vector_store():
    """Initialize FAISS vector store and retriever."""
    global _vector_store, _retriever

    try:
        from langchain_mistralai import MistralAIEmbeddings
        from langchain_community.vectorstores import FAISS

        print(f"[MCP] Loading vector store from: {VECTOR_STORE_PATH}")

        embeddings = MistralAIEmbeddings(model="mistral-embed")
        _vector_store = FAISS.load_local(
            VECTOR_STORE_PATH,
            embeddings,
            allow_dangerous_deserialization=True
        )

        _retriever = _vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": DEFAULT_K}
        )

        print("[MCP] ✓ Vector store loaded successfully")
        return True

    except Exception as e:
        print(f"[MCP] ✗ Failed to load vector store: {e}")
        return False


def _create_session(session_id: Optional[str] = None) -> str:
    """Create or retrieve a user session."""
    if session_id and session_id in _sessions:
        return session_id
    
    new_session_id = session_id or str(uuid.uuid4())
    _sessions[new_session_id] = {
        "created_at": asyncio.get_event_loop().time(),
        "query_count": 0,
        "last_query": None
    }
    
    print(f"[MCP] Created session: {new_session_id}")
    return new_session_id


def _update_session(session_id: str, query: str):
    """Update session metrics."""
    if session_id in _sessions:
        _sessions[session_id]["query_count"] += 1
        _sessions[session_id]["last_query"] = query


@mcp.tool()
async def query_nephrology_docs(
    query: str,
    k: int = DEFAULT_K,
    session_id: Optional[str] = None
) -> dict:
    """Retrieve relevant nephrology documentation chunks for a given query.
    
    This tool searches through indexed nephrology clinical documents and returns
    the most relevant passages based on semantic similarity.
    
    Args:
        query: The search query string (clinical question or topic)
        k: Number of document chunks to retrieve (default: 4, max: 10)
        session_id: Optional session identifier for tracking
    
    Returns:
        Dictionary containing:
        - status: "success" or "error"
        - query: The original query
        - context: List of relevant document chunks
        - metadata: List of metadata for each chunk (source, page, etc.)
        - num_results: Number of results returned
        - session_id: Session identifier
    
    Example:
        query: "What are the treatment options for acute kidney injury?"
        Returns relevant passages from nephrology guidelines and literature.
    """
    try:
        if _retriever is None:
            return {
                "status": "error",
                "message": "Vector store not initialized. Server may be starting up.",
                "session_id": session_id
            }

        # Validate k parameter
        k = max(1, min(k, 10))
        
        # Create or get session
        if session_id:
            session_id = _create_session(session_id)
            _update_session(session_id, query)

        print(f"[MCP] Query from session {session_id}: {query[:50]}...")

        # Run synchronous retriever in thread pool
        docs = await asyncio.to_thread(
            _retriever.invoke,
            query
        )

        # Extract context and metadata
        context = [doc.page_content for doc in docs[:k]]
        metadata = [doc.metadata for doc in docs[:k]]

        return {
            "status": "success",
            "query": query,
            "context": context,
            "metadata": metadata,
            "num_results": len(context),
            "session_id": session_id,
            "server_info": {
                "model": "mistral-embed",
                "search_type": "similarity"
            }
        }

    except Exception as e:
        error_msg = str(e)
        
        # Provide helpful error messages
        if "Bearer" in error_msg and "Illegal" in error_msg:
            return {
                "status": "error",
                "message": "API key configuration error",
                "hint": "Server admin: Check MISTRALAI_API_KEY environment variable",
                "session_id": session_id
            }

        return {
            "status": "error",
            "message": f"Query failed: {error_msg}",
            "session_id": session_id
        }


@mcp.tool()
async def get_server_info(session_id: Optional[str] = None) -> dict:
    """Get server status, configuration, and session information.
    
    Returns detailed information about server health, capabilities,
    and current session metrics.
    
    Args:
        session_id: Optional session identifier
    
    Returns:
        Dictionary with server status and configuration details
    """
    try:
        is_ready = _retriever is not None
        
        session_info = None
        if session_id and session_id in _sessions:
            session_info = _sessions[session_id]
        
        return {
            "status": "ready" if is_ready else "not_ready",
            "server_name": "nephrology-rag",
            "version": "1.0.0",
            "transport": "http/sse",
            "vector_store_path": VECTOR_STORE_PATH,
            "retriever_initialized": is_ready,
            "active_sessions": len(_sessions),
            "session_info": session_info,
            "capabilities": {
                "streaming": True,
                "multi_user": True,
                "max_results_per_query": 10
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}"
        }


@mcp.tool()
async def list_sessions() -> dict:
    """List all active sessions (admin tool).
    
    Returns:
        Dictionary with active session information
    """
    return {
        "status": "success",
        "active_sessions": len(_sessions),
        "sessions": [
            {
                "session_id": sid,
                "query_count": info["query_count"],
                "last_query": info["last_query"]
            }
            for sid, info in _sessions.items()
        ]
    }


@mcp.resource("nephrology://info")
def server_metadata():
    """Provide server metadata for MCP discovery."""
    return {
        "name": "Nephrology RAG Server",
        "version": "1.0.0",
        "description": "Multi-user RAG server for nephrology clinical documentation",
        "transport": "http/sse",
        "capabilities": {
            "streaming": True,
            "authentication": API_KEY is not None,
            "multi_user": True,
            "tools": [
                {
                    "name": "query_nephrology_docs",
                    "description": "Search nephrology documentation",
                    "streaming": True
                },
                {
                    "name": "get_server_info",
                    "description": "Get server health and configuration"
                },
                {
                    "name": "list_sessions",
                    "description": "List active user sessions"
                }
            ]
        },
        "usage": {
            "endpoint": "/mcp",
            "example_curl": '''curl -X POST https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp \\
  -H "Content-Type: application/json" \\
  -H "Accept: text/event-stream" \\
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "query_nephrology_docs",
      "arguments": {
        "query": "chronic kidney disease stages",
        "k": 4
      }
    }
  }'
'''
        }
    }


# Custom middleware for authentication and session management
@mcp.app.middleware("http")
async def auth_and_session_middleware(request: Request, call_next):
    """Handle authentication and session management for all requests."""
    
    # Skip middleware for health check and metadata endpoints
    if request.url.path in ["/health", "/", "/metadata"]:
        return await call_next(request)
    
    # Optional API key authentication
    if API_KEY:
        auth_header = request.headers.get("Authorization")
        api_key_param = request.query_params.get("api_key")
        
        provided_key = None
        if auth_header and auth_header.startswith("Bearer "):
            provided_key = auth_header[7:]
        elif api_key_param:
            provided_key = api_key_param
        
        if provided_key != API_KEY:
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized", "message": "Invalid or missing API key"}
            )
    
    # Extract or create session ID
    session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
    
    # Inject session ID into request state
    request.state.session_id = session_id
    
    response = await call_next(request)
    
    # Add session ID to response headers
    if hasattr(request.state, "session_id") and request.state.session_id:
        response.headers["X-Session-ID"] = request.state.session_id
    
    return response


# Health check endpoint
@mcp.app.get("/health")
async def health_check():
    """Simple health check endpoint for load balancers."""
    return {
        "status": "healthy" if _retriever is not None else "degraded",
        "service": "nephrology-rag-mcp",
        "version": "1.0.0"
    }


# Metadata endpoint
@mcp.app.get("/")
@mcp.app.get("/metadata")
async def get_metadata():
    """Get server metadata without MCP protocol."""
    return server_metadata()


def main():
    """Main entry point for production MCP server."""
    
    print("=" * 70)
    print("Nephrology RAG MCP Server - Production HTTP/SSE Transport")
    print("=" * 70)
    
    # Load vector store at startup
    vector_store_loaded = _load_vector_store()
    
    if not vector_store_loaded:
        print("[MCP] ⚠️  WARNING: Vector store failed to load")
        print("[MCP] Server will start but queries will fail")
        print("[MCP] Please check MISTRALAI_API_KEY and VECTOR_STORE_PATH")
    
    # Configuration summary
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"\n[MCP] Configuration:")
    print(f"  - Host: {host}")
    print(f"  - Port: {port}")
    print(f"  - Transport: HTTP/SSE")
    print(f"  - Authentication: {'Enabled' if API_KEY else 'Disabled'}")
    print(f"  - CORS Origins: {ALLOWED_ORIGINS}")
    print(f"  - Vector Store: {VECTOR_STORE_PATH}")
    print(f"\n[MCP] Endpoints:")
    print(f"  - MCP: http://{host}:{port}/mcp")
    print(f"  - Health: http://{host}:{port}/health")
    print(f"  - Metadata: http://{host}:{port}/metadata")
    
    if API_KEY:
        print(f"\n[MCP] 🔒 API Key authentication is ENABLED")
        print(f"[MCP] Clients must provide: Authorization: Bearer <key>")
    else:
        print(f"\n[MCP] ⚠️  WARNING: Running without authentication")
        print(f"[MCP] Set MCP_API_KEY environment variable to enable auth")
    
    print(f"\n[MCP] 🚀 Starting server...\n")
    print("=" * 70)
    
    # Run with uvicorn for production
    uvicorn.run(
        mcp.app,
        host=host,
        port=port,
        log_level="info",
        access_log=True,
        timeout_keep_alive=300,
        limit_concurrency=100,
        limit_max_requests=10000
    )


if __name__ == "__main__":
    main()
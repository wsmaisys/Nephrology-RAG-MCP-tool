"""Nephrology RAG MCP server exposing a FAISS-backed retriever via FastMCP.

Keep comments concise and informative for production use.
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
# Accept several common names for the Mistral API key.
m = os.environ.get("MISTRALAI_API_KEY") or os.environ.get("MISTRAL_API_KEY") or os.environ.get("mistral_api_key")
if m:
    os.environ["MISTRALAI_API_KEY"] = m

from fastmcp import FastMCP

VECTOR_STORE_PATH = "vector_store"

_vector_store = None
_retriever = None

# MCP server instance
# Try to construct FastMCP without requiring sessions when supported by the
# installed FastMCP version (some releases enforce session IDs). Fall back to
# the default constructor if the parameter is not supported.
try:
    mcp = FastMCP("nephrology-rag-mcp", require_session=False)
except TypeError:
    mcp = FastMCP("nephrology-rag-mcp")


def _load_vector_store():
    """Load FAISS index and initialize a retriever.

    Raises on failure so calling process can fail-fast.
    """
    global _vector_store, _retriever

    try:
        from langchain_mistralai import MistralAIEmbeddings
        from langchain_community.vectorstores import FAISS

        print(f"[RAG MCP] Loading vector store from '{VECTOR_STORE_PATH}'...")

        embeddings_model = MistralAIEmbeddings(model="mistral-embed")
        _vector_store = FAISS.load_local(
            VECTOR_STORE_PATH, embeddings_model, allow_dangerous_deserialization=True
        )

        print("[RAG MCP] Vector store loaded successfully!")

        _retriever = _vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})
        print("[RAG MCP] Retriever initialized!")

    except Exception as e:
        print(f"[RAG MCP] ERROR: Failed to load vector store: {e}")
        raise


@mcp.tool()
async def invoke(query: str, k: int = 4) -> dict:
    """Return top-k relevant document chunks for `query`.

    The retriever used by LangChain is synchronous; run it in a thread to
    avoid blocking the event loop.
    """
    try:
        if _retriever is None:
            return {"status": "error", "message": "Retriever not initialized"}

        if hasattr(_retriever, "get_relevant_documents"):
            result = await asyncio.to_thread(_retriever.get_relevant_documents, query)
        elif hasattr(_retriever, "invoke"):
            result = await asyncio.to_thread(_retriever.invoke, query)
        else:
            result = await asyncio.to_thread(lambda: _retriever(query))

        context = [doc.page_content for doc in result]
        metadata = [doc.metadata for doc in result]

        return {
            "status": "success",
            "query": query,
            "context": context,
            "metadata": metadata,
            "num_results": len(context),
        }

    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        msg = str(e)

        # Common failure when an empty API key yields an invalid 'Bearer ' header.
        if "Illegal header value b'Bearer '" in msg or msg.strip().endswith("Bearer '"):
            hint = (
                "Empty 'Authorization: Bearer <token>' detected. Ensure `MISTRALAI_API_KEY` "
                "is set and non-empty in the environment or .env."
            )
            return {"status": "error", "message": f"Error invoking RAG tool: {msg}", "hint": hint, "traceback": tb}

        return {"status": "error", "message": f"Error invoking RAG tool: {msg}", "traceback": tb}


@mcp.tool()
async def health() -> dict:
    """Return basic service health and configuration info."""
    try:
        if _retriever is None:
            return {"status": "error", "message": "Retriever not initialized"}

        return {"status": "ok", "message": "RAG service is ready", "vector_store_path": VECTOR_STORE_PATH}

    except Exception as e:
        return {"status": "error", "message": f"Health check failed: {str(e)}"}


@mcp.resource("rag:///Nephrology-RAG-Tool", mime_type="application/json")
def rag_tool_info():
    """Return tool metadata for discovery."""
    return {
        "tool_name": "Nephrology RAG Tool",
        "description": "Retrieves relevant clinical information from nephrology documents.",
        "usage": "Invoke the 'invoke' method with a query string to retrieve information.",
        "example_query": "What are the treatment options for chronic kidney disease?",
    }


if __name__ == "__main__":
    print("[RAG MCP] Starting RAG MCP Server...")
    _load_vector_store()

    # Use PORT env var (default 8000 for local, 8080 for Google Cloud Run)
    port = int(os.environ.get("PORT", 8000))
    print(f"[RAG MCP] Server listening on http://0.0.0.0:{port}")
    # Configure request timeout at runtime when supported; otherwise start
    # without it to remain compatible with different FastMCP releases.
    try:
        mcp.run(transport="http", host="0.0.0.0", port=port, request_timeout=300)
    except TypeError:
        print("[RAG MCP] FastMCP.run() does not accept 'request_timeout'; starting without it.")
        mcp.run(transport="http", host="0.0.0.0", port=port)
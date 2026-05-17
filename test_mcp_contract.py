"""
Local contract tests for the public MCP service surface.
These do not require a loaded vector store or live Mistral key.
"""

from fastapi.testclient import TestClient

import rag_mcp_server


def test_manifest_exposes_public_tools_without_session_listing():
    client = TestClient(rag_mcp_server.app)

    response = client.get("/mcp.json")

    assert response.status_code == 200
    payload = response.json()
    tool_names = [tool["name"] for tool in payload["tools"]]
    assert "query_nephrology_docs" in tool_names
    assert "get_server_info" in tool_names
    assert "list_sessions" not in tool_names
    assert payload["auth"]["required"] is False
    assert payload["limits"]["max_query_chars"] == rag_mcp_server.MAX_QUERY_CHARS


def test_tools_list_returns_schema_rich_public_tools():
    client = TestClient(rag_mcp_server.app)
    payload = {"jsonrpc": "2.0", "id": "tools", "method": "tools/list", "params": {}}

    response = client.post("/mcp", json=payload)

    assert response.status_code == 200
    result = response.json()["result"]
    first_tool = result["tools"][0]
    assert first_tool["name"] == "query_nephrology_docs"
    assert "input_schema" in first_tool
    assert "query" in first_tool["input_schema"]["properties"]


def test_long_query_is_rejected_without_retriever():
    client = TestClient(rag_mcp_server.app)
    payload = {
        "jsonrpc": "2.0",
        "id": "long-query",
        "method": "tools/call",
        "params": {
            "name": "query_nephrology_docs",
            "arguments": {"query": "x" * (rag_mcp_server.MAX_QUERY_CHARS + 1)},
        },
    }

    response = client.post("/mcp", json=payload)

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["status"] == "error"
    assert "too long" in result["message"]

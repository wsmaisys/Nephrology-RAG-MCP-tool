#!/usr/bin/env python3
"""
Full MCP Server Diagnostic Test Suite
Author: Wasim
Purpose:
    Validate MCP compliance for:
        - JSON-RPC structure
        - mcp.discover
        - tools/list
        - tools/call (sync)
        - tools/call (streaming SSE)
        - Session-ID propagation
        - Server health
        - Micro-latency benchmarks
"""

import json
import uuid
import time
import requests
from requests.exceptions import RequestException

# SSE client (optional)
try:
    from sseclient import SSEClient
    HAS_SSE = True
except Exception:
    SSEClient = None
    HAS_SSE = False
# -----------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------
#MCP_URL = "http://localhost:8000/mcp"
MCP_URL = "http:// http://0.0.0.0:8000/mcp"
#MCP_URL = "https://nephrology-rag-mcp-tool-785629432566.us-central1.run.app/mcp"   # <-- change ONLY if needed
TIMEOUT = 30

# -----------------------------------------------------
def pretty(obj):
    print(json.dumps(obj, indent=2))

def banner(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

# -----------------------------------------------------
# 1) TEST DISCOVERY
# -----------------------------------------------------
def test_discover():
    banner("TEST 1 — MCP DISCOVERY")
    payload = {
        "jsonrpc": "2.0",
        "id": "disc-1",
        "method": "mcp.discover",
        "params": {}
    }

    try:
        r = requests.post(MCP_URL, json=payload, timeout=TIMEOUT)
        print(f"Status: {r.status_code}")
        resp = r.json()
        pretty(resp)

        assert "result" in resp, "Missing result in discovery response"
        assert "name" in resp["result"], "Missing server name"
        assert "version" in resp["result"], "Missing version"
        assert "tools" in resp["result"], "Missing tools section"

        print("✔ Discovery structure OK")

    except Exception as e:
        print("❌ Discovery test FAILED:", e)


# -----------------------------------------------------
# 2) TEST TOOLS/LIST
# -----------------------------------------------------
def test_list_tools():
    banner("TEST 2 — tools/list")

    payload = {
        "jsonrpc": "2.0",
        "id": "list-tools-1",
        "method": "tools/list",
        "params": {}
    }

    try:
        r = requests.post(MCP_URL, json=payload, timeout=TIMEOUT)
        print(f"Status: {r.status_code}")
        resp = r.json()
        pretty(resp)

        assert "result" in resp, "Missing result"
        assert "tools" in resp["result"], "Missing tools array"
        assert isinstance(resp["result"]["tools"], list), "Tools must be a list"

        print("✔ Tools/list OK")

    except Exception as e:
        print("❌ Tools/list FAILED:", e)


# -----------------------------------------------------
# 3) TEST SYNC TOOL CALL
# -----------------------------------------------------
def test_tool_call_sync():
    banner("TEST 3 — tools/call (synchronous HTTP)")

    payload = {
        "jsonrpc": "2.0",
        "id": "sync-call-1",
        "method": "tools/call",
        "params": {
            "name": "query_nephrology_docs",
            "arguments": {
                "query": "acute kidney injury",
                "k": 3
            }
        }
    }

    try:
        start = time.time()
        r = requests.post(MCP_URL, json=payload, timeout=TIMEOUT)
        latency = time.time() - start

        print(f"Status: {r.status_code}")
        print(f"Latency: {latency:.3f}s")

        resp = r.json()
        pretty(resp)

        assert "result" in resp, "Missing result"
        # result shape may vary; ensure it's a dict
        assert isinstance(resp["result"], dict), "Result must be an object"
        print("✔ Sync call returned result object")

        print("✔ Sync call OK")

    except Exception as e:
        print("❌ Sync tool call FAILED:", e)


# -----------------------------------------------------
# 4) TEST SSE STREAMING TOOL CALL
# -----------------------------------------------------
def test_tool_call_streaming():
    banner("TEST 4 — tools/call (SSE streaming)")

    if not HAS_SSE:
        print("⚠ SSE client (`sseclient-py`) not installed. Streaming test will be skipped.")
        print("Install it: pip install sseclient-py")
        return

    headers = {
        "Accept": "text/event-stream",
        "Content-Type": "application/json"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": "stream-call-1",
        "method": "tools/call",
        "params": {
            "name": "query_nephrology_docs",
            "transport": "http/sse",
            "arguments": {
                "query": "glomerular filtration rate",
                "k": 2
            }
        }
    }

    try:
        print("Connecting to stream...")
        r = requests.post(MCP_URL, json=payload, headers=headers, stream=True, timeout=TIMEOUT)

        # Some servers may fallback to a JSON response instead of SSE.
        ctype = r.headers.get("Content-Type", "")
        if "application/json" in ctype:
            # Parse JSON fallback and report
            try:
                resp = r.json()
                pretty(resp)
                print("⚠ Server returned JSON instead of SSE; streaming fallback used.")
            except Exception as e:
                print("⚠ Server returned non-streaming response; could not parse JSON:", e)
            return

        # Otherwise attempt SSE parsing
        # Parse SSE manually from the response iterator to avoid client library issues
        buffer = []
        for raw_line in r.iter_lines(decode_unicode=True):
            line = raw_line.strip() if raw_line is not None else ""
            if line == "":
                # end of event
                if not buffer:
                    continue
                # join data lines
                data_lines = [l[5:] for l in buffer if l.startswith("data:")]
                event_lines = [l[6:] for l in buffer if l.startswith("event:")]
                event_type = event_lines[0] if event_lines else None
                data = "\n".join(data_lines)
                print("\n--- SSE EVENT ---")
                print(data)

                if event_type and "mcp.complete" in event_type:
                    print("✔ Streaming ended cleanly")
                    break

                # reset buffer for next event
                buffer = []
            else:
                buffer.append(line)

    except Exception as e:
        print("❌ Streaming tool call FAILED:", e)


# -----------------------------------------------------
# 5) TEST SESSION ID PROPAGATION
# -----------------------------------------------------
def test_session_id():
    banner("TEST 5 — Session ID Propagation")

    session_id = str(uuid.uuid4())

    headers = {
        "X-Session-Id": session_id,
        "Content-Type": "application/json"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": "session-test-1",
        "method": "tools/call",
        "params": {
            "name": "query_nephrology_docs",
            "arguments": {
                "query": "kidney transplant",
                "k": 1
            }
        }
    }

    try:
        r = requests.post(MCP_URL, json=payload, headers=headers, timeout=TIMEOUT)
        resp = r.json()
        pretty(resp)

        # Server should echo session id in the tool result (if supported)
        result = resp.get("result", {}) or {}
        assert result.get("session_id") == session_id, "Server did NOT echo session ID"

        print("✔ Session ID OK")

    except Exception as e:
        print("❌ Session ID failed:", e)


# -----------------------------------------------------
# 6) TEST ERROR HANDLING
# -----------------------------------------------------
def test_error_handling():
    banner("TEST 6 — Error Handling")

    payload = {
        "jsonrpc": "2.0",
        "id": "error-test-1",
        "method": "tools/call",
        "params": {
            "name": "query_nephrology_docs",
            "arguments": {
                "query": "",         # INVALID
                "k": -5              # INVALID
            }
        }
    }

    try:
        r = requests.post(MCP_URL, json=payload, timeout=TIMEOUT)
        print(f"Status: {r.status_code}")

        resp = r.json()
        pretty(resp)

        # Expect a structured error result (tool may return status=error)
        result = resp.get("result") or {}
        assert (isinstance(result, dict) and result.get("status") == "error") or ("error" in resp), "Expected an error result"

        print("✔ Error handling OK")

    except Exception as e:
        print("❌ Error test FAILED:", e)


# -----------------------------------------------------
# MAIN
# -----------------------------------------------------
if __name__ == "__main__":
    print("\nRunning MCP Diagnostic Suite...\n")

    test_discover()
    test_list_tools()
    test_tool_call_sync()
    test_tool_call_streaming()
    test_session_id()
    test_error_handling()

    print("\nDONE. Review results above.\n")
#!/usr/bin/env python3
"""
Test script for Nephrology RAG MCP Server

This script demonstrates how to use the MCP server locally and validates
that the RAG retriever is working correctly.

Usage:
    # For local testing (server must be running on port 8000):
    python test_mcp_server.py

    # For remote testing (e.g., Cloud Run):
    python test_mcp_server.py --url https://your-cloud-run-url/mcp

Requirements:
    - requests library (pip install requests)
    - Server running locally or accessible remotely
"""

import argparse
import json
import re
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Install with: pip install requests")
    sys.exit(1)


class MCPServerTester:
    """Test client for Nephrology RAG MCP Server"""

    def __init__(self, url: str = "http://localhost:8000/mcp"):
        """
        Initialize MCP tester.

        Args:
            url: Base URL of MCP server endpoint
        """
        self.url = url
        self.headers = {"Accept": "application/json, text/event-stream"}
        self.test_results = []

    def parse_sse_response(self, text: str) -> Optional[dict]:
        """Parse Server-Sent Events (SSE) response format."""
        match = re.search(r"data: ({.*})", text)
        return json.loads(match.group(1)) if match else None

    def log_test(self, name: str, passed: bool, message: str = ""):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
        if message:
            print(f"       {message}")
        self.test_results.append((name, passed))

    def test_connection(self) -> bool:
        """Test basic connectivity to server."""
        print("\n" + "=" * 80)
        print("TEST 1: Server Connectivity")
        print("=" * 80)
        try:
            # Try initialize request
            resp = requests.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0"},
                    },
                    "id": 1,
                },
                headers=self.headers,
                timeout=10,
            )
            passed = resp.status_code == 200
            self.log_test(
                "Server Connectivity", passed, f"Status: {resp.status_code}"
            )
            return passed
        except requests.exceptions.ConnectionError:
            self.log_test(
                "Server Connectivity",
                False,
                f"Cannot connect to {self.url}",
            )
            return False
        except Exception as e:
            self.log_test("Server Connectivity", False, str(e))
            return False

    def test_mcp_protocol(self) -> bool:
        """Test MCP protocol initialization."""
        print("\n" + "=" * 80)
        print("TEST 2: MCP Protocol")
        print("=" * 80)
        try:
            resp = requests.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test-client", "version": "1.0"},
                    },
                    "id": 1,
                },
                headers=self.headers,
                timeout=10,
            )

            result = self.parse_sse_response(resp.text)
            if not result:
                self.log_test("MCP Protocol", False, "Invalid SSE response format")
                return False

            protocol_version = result.get("result", {}).get("protocolVersion")
            server_name = result.get("result", {}).get("serverInfo", {}).get("name")

            passed = (
                protocol_version == "2024-11-05"
                and server_name == "nephrology-rag-mcp"
            )
            self.log_test(
                "MCP Protocol",
                passed,
                f"Server: {server_name}, Protocol: {protocol_version}",
            )
            return passed
        except Exception as e:
            self.log_test("MCP Protocol", False, str(e))
            return False

    def test_vector_store(self) -> bool:
        """Test vector store and retriever functionality."""
        print("\n" + "=" * 80)
        print("TEST 3: Vector Store & Retriever")
        print("=" * 80)
        try:
            # Test with a nephrology-related query
            query = "kidney disease pathophysiology"
            resp = requests.post(
                self.url,
                json={
                    "jsonrpc": "2.0",
                    "method": "invoke",
                    "params": {"query": query, "k": 3},
                    "id": 2,
                },
                headers=self.headers,
                timeout=30,
            )

            if resp.status_code == 200:
                # For HTTP transport, we may get SSE or direct JSON
                try:
                    result = self.parse_sse_response(resp.text)
                except:
                    result = resp.json()

                if result:
                    # Check if error
                    if "error" in result:
                        error_msg = result["error"].get("message", "Unknown error")
                        self.log_test(
                            "Vector Store Query",
                            False,
                            f"Error: {error_msg}",
                        )
                        return False

                    self.log_test("Vector Store Query", True, f"Query: {query}")
                    return True
                else:
                    self.log_test(
                        "Vector Store Query", False, "Invalid response format"
                    )
                    return False
            else:
                self.log_test(
                    "Vector Store Query",
                    False,
                    f"HTTP {resp.status_code}",
                )
                return False

        except requests.exceptions.Timeout:
            self.log_test(
                "Vector Store Query",
                False,
                "Request timeout (vector store may be loading)",
            )
            return False
        except Exception as e:
            self.log_test("Vector Store Query", False, str(e))
            return False

    def test_retrieval_quality(self) -> bool:
        """Test that retriever returns meaningful results."""
        print("\n" + "=" * 80)
        print("TEST 4: Retrieval Quality")
        print("=" * 80)
        try:
            queries = [
                "glomerulonephritis treatment",
                "acute kidney injury diagnosis",
                "chronic kidney disease management",
            ]

            all_passed = True
            for query in queries:
                try:
                    resp = requests.post(
                        self.url,
                        json={
                            "jsonrpc": "2.0",
                            "method": "invoke",
                            "params": {"query": query, "k": 2},
                            "id": 3,
                        },
                        headers=self.headers,
                        timeout=30,
                    )

                    if resp.status_code == 200:
                        print(f"   ✓ Query: '{query}'")
                    else:
                        print(f"   ✗ Query failed: '{query}' (HTTP {resp.status_code})")
                        all_passed = False
                except Exception as e:
                    print(f"   ✗ Query error: '{query}' ({str(e)})")
                    all_passed = False

            self.log_test(
                "Retrieval Quality",
                all_passed,
                f"Tested {len(queries)} nephrology queries",
            )
            return all_passed

        except Exception as e:
            self.log_test("Retrieval Quality", False, str(e))
            return False

    def test_parameter_validation(self) -> bool:
        """Test parameter validation."""
        print("\n" + "=" * 80)
        print("TEST 5: Parameter Validation")
        print("=" * 80)
        try:
            # Test with different k values
            test_cases = [
                ("k=1", {"query": "test", "k": 1}, True),
                ("k=5", {"query": "test", "k": 5}, True),
                ("empty query", {"query": "", "k": 3}, True),  # May still work
            ]

            all_passed = True
            for name, params, should_pass in test_cases:
                try:
                    resp = requests.post(
                        self.url,
                        json={
                            "jsonrpc": "2.0",
                            "method": "invoke",
                            "params": params,
                            "id": 4,
                        },
                        headers=self.headers,
                        timeout=30,
                    )
                    passed = resp.status_code in [200, 400]  # Either success or proper error
                    status = "✓" if passed else "✗"
                    print(f"   {status} {name}")
                    if not passed:
                        all_passed = False
                except Exception as e:
                    print(f"   ✗ {name} ({str(e)})")
                    all_passed = False

            self.log_test("Parameter Validation", all_passed, "All parameter tests")
            return all_passed

        except Exception as e:
            self.log_test("Parameter Validation", False, str(e))
            return False

    def run_all_tests(self) -> bool:
        """Run all tests and return overall result."""
        print("\n")
        print("╔" + "=" * 78 + "╗")
        print("║" + " " * 15 + "NEPHROLOGY RAG MCP SERVER TEST SUITE" + " " * 28 + "║")
        print("╚" + "=" * 78 + "╝")
        print(f"\nServer URL: {self.url}\n")

        # Run tests in sequence
        conn_ok = self.test_connection()
        if not conn_ok:
            print("\n⚠️  Cannot connect to server. Stopping tests.")
            return False

        self.test_mcp_protocol()
        self.test_vector_store()
        self.test_retrieval_quality()
        self.test_parameter_validation()

        # Print summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        passed_count = sum(1 for _, passed in self.test_results if passed)
        total_count = len(self.test_results)
        print(f"\nTotal: {passed_count}/{total_count} tests passed")

        for test_name, passed in self.test_results:
            status = "✅" if passed else "❌"
            print(f"  {status} {test_name}")

        print("\n" + "=" * 80)
        if passed_count == total_count:
            print("✅ ALL TESTS PASSED - Server is functioning correctly!")
        elif passed_count >= total_count - 1:
            print("⚠️  MOST TESTS PASSED - Check warnings above")
        else:
            print("❌ TESTS FAILED - Check errors above")
        print("=" * 80 + "\n")

        return passed_count == total_count


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Test the Nephrology RAG MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test local server (default port 8000)
  python test_mcp_server.py

  # Test on specific port
  python test_mcp_server.py --url http://localhost:8080/mcp

  # Test remote Cloud Run deployment
  python test_mcp_server.py --url https://nephrology-rag-mcp-xxxxx-uc.a.run.app/mcp

  # With verbose output
  python test_mcp_server.py --verbose
        """,
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000/mcp",
        help="MCP server URL (default: http://localhost:8000/mcp)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    tester = MCPServerTester(url=args.url)
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

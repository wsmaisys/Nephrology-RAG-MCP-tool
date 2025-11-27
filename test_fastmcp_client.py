#!/usr/bin/env python3
"""FastMCP client test for Nephrology RAG MCP server

This script uses the FastMCP Client to connect via streaming/SSE to the
remote MCP server and calls tools `list_tools`, `health`, and `invoke`.

Configuration:
    - Load MCP_URL and MISTRAL_API_KEY from .env file
    - Default to deployed Cloud Run service if not specified
    - Validate MISTRAL_API_KEY is set before testing

Run:
    pip install fastmcp python-dotenv
    python test_fastmcp_client.py

"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from fastmcp import Client

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
load_dotenv(env_file)

# Configuration from environment
MCP_URL = os.getenv("MCP_URL", "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

async def run_test():
    # Validate API key
    if not MISTRAL_API_KEY:
        print("❌ ERROR: MISTRAL_API_KEY not set in .env file")
        print("   Please add: MISTRAL_API_KEY=your_key_here")
        sys.exit(1)

    print(f"🔗 Connecting to {MCP_URL}")
    print(f"🔑 Using Mistral API Key: {'*' * 10}{MISTRAL_API_KEY[-4:]}")
    print()
    
    try:
        async with Client(MCP_URL) as client:
            print("✓ Connected to MCP Server\n")

            # List available tools
            print("📋 Listing available tools...")
            tools = await client.list_tools()
            print("Tools:")
            try:
                print(json.dumps(tools, indent=2))
            except Exception:
                print(repr(tools))
            print()

            # Health check
            print("🏥 Calling health tool...")
            health_res = await client.call_tool("health", {})
            print("Health response:")
            for item in health_res.content:
                print(f"  {repr(item)}")
            print()

            # Test RAG invoke
            print("🔍 Calling invoke tool with sample query...")
            test_query = "acute kidney injury diagnosis and treatment"
            print(f"Query: '{test_query}'")
            invoke_res = await client.call_tool(
                "invoke",
                {"query": test_query, "k": 3}
            )
            print("Invoke response:")
            for item in invoke_res.content:
                print(f"  {repr(item)}")
            print()

            print("✅ Client test completed successfully!")

    except Exception as e:
        print(f"❌ ERROR: FastMCP client failed:")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(run_test())

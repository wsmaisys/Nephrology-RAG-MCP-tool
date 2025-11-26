#!/usr/bin/env python3
"""FastMCP client test for Nephrology RAG MCP server

This script uses the FastMCP Client to connect via streaming/SSE to the
remote MCP server and calls tools `list_tools`, `health`, and `invoke`.

Run:
    pip install fastmcp
    python test_fastmcp_client.py

"""
import asyncio
import json

from fastmcp import Client

CLOUD_RUN_MCP = "https://nephrology-mcp-server-923690924368.us-central1.run.app/mcp"

async def run_test():
    print(f"Connecting to {CLOUD_RUN_MCP} with FastMCP Client...")
    try:
        async with Client(CLOUD_RUN_MCP) as client:
            print("Connected. Listing tools...")
            tools = await client.list_tools()
            print("Tools:")
            try:
                print(json.dumps(tools, indent=2))
            except Exception:
                print(repr(tools))

            print("\nCalling health tool...")
            health_res = await client.call_tool("health", {})
            print("Health response content:")
            for item in health_res.content:
                print(repr(item))

            print("\nCalling invoke tool for a sample query...")
            invoke_res = await client.call_tool("invoke", {"query": "acute kidney injury diagnosis", "k": 3})
            print("Invoke response content (streamed messages):")
            for item in invoke_res.content:
                print(repr(item))

            print("\nClient test completed successfully.")
    except Exception as e:
        print("ERROR: FastMCP client failed:")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    asyncio.run(run_test())

#!/usr/bin/env python3
"""FatSecret MCP Server for cloud deployment (SSE transport).

Works with Railway, Render, or any platform that sets PORT env var.
"""

import os

# Configure FastMCP for cloud deployment BEFORE importing
# FastMCP uses FASTMCP_ prefix for settings
os.environ.setdefault("FASTMCP_HOST", "0.0.0.0")
if "PORT" in os.environ:
    os.environ["FASTMCP_PORT"] = os.environ["PORT"]

from fatsecret_mcp.server import mcp


def main() -> None:
    """Run the FatSecret MCP server with SSE transport."""
    # Run with SSE transport for remote MCP clients
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""FatSecret MCP Server for cloud deployment (SSE transport).

Works with Railway, Render, or any platform that sets PORT env var.
"""

from fatsecret_mcp.server import mcp


def main() -> None:
    """Run the FatSecret MCP server with SSE transport."""
    # Run with SSE transport for remote MCP clients
    # FastMCP reads PORT from environment automatically
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()

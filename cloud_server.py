#!/usr/bin/env python3
"""FatSecret MCP Server for cloud deployment (SSE transport).

Works with Railway, Render, or any platform that sets PORT env var.
"""

import os

# Must bind to 0.0.0.0 for cloud platforms (not localhost)
os.environ["FASTMCP_HOST"] = "0.0.0.0"

from fatsecret_mcp.server import mcp


def main() -> None:
    """Run the FatSecret MCP server with SSE transport."""
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run a single test file
pytest tests/test_auth.py

# Run tests matching a pattern
pytest -k "test_search"

# Run with coverage
pytest --cov=fatsecret_mcp --cov-report=html

# Linting and formatting (uses Ruff)
ruff check .
ruff check --fix .
ruff format .

# Run the MCP server
fatsecret-mcp

# Test with MCP Inspector
npx @modelcontextprotocol/inspector fatsecret-mcp
```

## Architecture Overview

This is a Model Context Protocol (MCP) server that provides Claude with access to the FatSecret nutrition API. The architecture follows a clean layered design:

```
server.py (MCP tools) → api_client.py → auth.py (OAuth1)
                             ↓
                        models.py (Pydantic)
```

### Request Flow

1. **server.py**: Defines MCP tools using FastMCP decorators (`@mcp.tool()`). Each tool wraps an API client method and formats responses for Claude consumption.

2. **api_client.py**: `FatSecretClient` handles all HTTP communication with the FatSecret API. Uses `httpx.AsyncClient` for async requests. The `_make_request` method:
   - Builds request parameters
   - Signs requests via `OAuth1Signer`
   - Handles error code mapping to specific exceptions

3. **auth.py**: `OAuth1Signer` implements OAuth1 two-legged authentication (HMAC-SHA1). FatSecret uses OAuth1 without user tokens (consumer credentials only).

4. **config.py**: Uses `pydantic-settings` to load environment variables with `FATSECRET_` prefix. Required: `FATSECRET_CONSUMER_KEY`, `FATSECRET_CONSUMER_SECRET`.

5. **models.py**: Pydantic models for type-safe API response parsing. Key model groups: Food/FoodServing, Recipe/RecipeIngredient/RecipeServing, search results.

### Server Lifecycle

The server uses FastMCP's lifespan context manager (`server.py:24-51`) to:
- Initialize settings and `FatSecretClient` on startup
- Store client in `mcp.state["client"]`
- Close the httpx client on shutdown

### Exception Hierarchy

All exceptions inherit from `FatSecretError`. API error codes map to specific exceptions:
- Code 9 → `RateLimitError`
- Code 106 → `FoodNotFoundError`
- Code 107 → `RecipeNotFoundError`
- Code 110 → `BarcodeNotFoundError`

### Testing Patterns

Tests use `respx` to mock httpx responses. Fixtures in `conftest.py` provide:
- `settings`: Test credentials
- `mock_*_response`: Sample API responses for various endpoints

The `asyncio_mode = "auto"` pytest setting enables automatic async test handling.

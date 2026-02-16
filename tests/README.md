# FatSecret MCP Server Tests

This directory contains comprehensive tests for the FatSecret MCP Server.

## Test Structure

- **conftest.py** - Pytest fixtures and test data
  - Settings fixture with test credentials
  - Mock OAuth token responses
  - Mock API responses for foods, recipes, and barcodes

- **test_auth.py** - OAuth2 authentication tests
  - Token acquisition and caching
  - Token refresh when expired
  - Token refresh within buffer time
  - Authentication error handling
  - Concurrent request handling

- **test_api_client.py** - API client tests
  - Food search functionality
  - Food details retrieval
  - Barcode lookup
  - Recipe search and retrieval
  - Error handling (FoodNotFoundError, BarcodeNotFoundError, APIError)
  - Pagination support

## Running Tests

### Install Dependencies

```bash
# Install package with dev dependencies
pip install -e ".[dev]"
```

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_auth.py
pytest tests/test_api_client.py
```

### Run Specific Test

```bash
pytest tests/test_auth.py::test_token_acquisition
pytest tests/test_api_client.py::test_search_foods_returns_food_search_result
```

### Run with Coverage

```bash
pytest --cov=fatsecret_mcp --cov-report=html
```

### Run with Verbose Output

```bash
pytest -v
pytest -vv  # Extra verbose
```

### Run Tests Matching Pattern

```bash
pytest -k "token"  # Run all tests with 'token' in name
pytest -k "error"  # Run all error handling tests
```

## Test Configuration

Test configuration is in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
asyncio_default_fixture_loop_scope = "function"
```

## Mocking Strategy

Tests use **respx** for mocking HTTP requests:

- OAuth token endpoint is mocked for authentication
- FatSecret API endpoint is mocked for API calls
- All async tests are marked with `@pytest.mark.asyncio`

## Test Coverage Areas

### Authentication (test_auth.py)
- OAuth2 Client Credentials flow
- Token caching and refresh
- Expiry buffer handling
- Error scenarios (401, network errors, invalid responses)
- Concurrent access synchronization

### API Client (test_api_client.py)
- Food search with pagination
- Food details with servings
- Barcode lookup
- Recipe search and details
- Error handling for various API error codes
- HTTP error handling
- Empty result sets
- Concurrent API requests

## Writing New Tests

When adding new tests:

1. Add fixtures to `conftest.py` if they're reusable
2. Use `@pytest.mark.asyncio` for async tests
3. Mock HTTP requests with respx
4. Follow existing test naming conventions: `test_<functionality>_<scenario>`
5. Include docstrings explaining what the test verifies
6. Test both success and error cases

Example:

```python
@pytest.mark.asyncio
async def test_new_feature(settings, mock_token_response):
    """Test description.

    Verifies that:
    - Point 1
    - Point 2
    """
    with respx.mock:
        respx.post(settings.token_url).mock(
            return_value=Response(200, json=mock_token_response)
        )

        # Test implementation
        ...
```

## Troubleshooting

### ImportError for api_client

If you get an import error for `api_client`, the module hasn't been implemented yet. The tests will skip automatically with:

```python
pytest.skip("APIClient not yet implemented", allow_module_level=True)
```

### Async Warnings

If you see warnings about async fixtures, ensure:
- `pytest-asyncio` is installed
- `asyncio_mode = "auto"` is in `pyproject.toml`
- Tests are marked with `@pytest.mark.asyncio`

### Mock Not Working

Ensure you're using the `with respx.mock:` context manager and that the URL exactly matches the one being requested.

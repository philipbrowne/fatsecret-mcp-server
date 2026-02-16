# FatSecret MCP Server

A Model Context Protocol (MCP) server that provides Claude with access to the FatSecret nutrition API. This enables Claude to search for foods, look up nutritional information, scan barcodes, search recipes, and parse natural language food descriptions.

## Features

- **Food Search**: Search the FatSecret food database with flexible query options
- **Nutrition Lookup**: Get detailed nutritional information for specific foods
- **Barcode Scanning**: Look up food products by barcode (UPC/EAN)
- **Recipe Search**: Search for recipes with nutritional information

## Prerequisites

- Python 3.10 or higher
- FatSecret API credentials (Consumer Key and Consumer Secret)

### Getting FatSecret API Credentials

1. Visit [FatSecret Platform API](https://platform.fatsecret.com/api/)
2. Create an account or sign in
3. Navigate to your API settings
4. Create a new application to get your Consumer Key and Consumer Secret

## Installation

### Install from source

```bash
cd fatsecret-mcp-server
pip install -e .
```

### Install with development dependencies

```bash
pip install -e ".[dev]"
```

## Configuration

The server requires FatSecret API credentials to be configured via environment variables:

### Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
FATSECRET_CONSUMER_KEY=your_consumer_key_here
FATSECRET_CONSUMER_SECRET=your_consumer_secret_here
```

You can use the provided `.env.example` as a template:

```bash
cp .env.example .env
# Edit .env with your credentials
```

### Optional Configuration

- `FATSECRET_API_BASE_URL`: API base URL (default: `https://platform.fatsecret.com/rest/server.api`)

## Usage with Claude Desktop

Add this configuration to your Claude Desktop config file:

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "fatsecret": {
      "command": "fatsecret-mcp",
      "env": {
        "FATSECRET_CONSUMER_KEY": "your_consumer_key",
        "FATSECRET_CONSUMER_SECRET": "your_consumer_secret"
      }
    }
  }
}
```

After adding the configuration, restart Claude Desktop.

## Available Tools

Once configured, Claude will have access to the following tools:

### Food Search and Nutrition

- **search_foods**: Search for foods in the FatSecret database
  - Parameters: query, page, max_results
  - Returns: List of matching foods with descriptions

- **get_food**: Get detailed nutritional information for a specific food
  - Parameters: food_id
  - Returns: Complete nutrition data including all servings

- **lookup_barcode**: Look up food by barcode (UPC/EAN)
  - Parameters: barcode
  - Returns: Food information matching the barcode

### Recipe Search

- **search_recipes**: Search for recipes
  - Parameters: query, page, max_results
  - Returns: List of recipes with basic information

- **get_recipe**: Get detailed recipe information
  - Parameters: recipe_id
  - Returns: Complete recipe with ingredients, directions, and nutrition

## Development

### Running Tests

```bash
pytest
```

Run tests with coverage:

```bash
pytest --cov=fatsecret_mcp --cov-report=html
```

### Code Quality

This project uses Ruff for linting and formatting:

```bash
# Check code
ruff check .

# Format code
ruff format .
```

### Project Structure

```
fatsecret-mcp-server/
├── src/
│   └── fatsecret_mcp/
│       ├── __init__.py       # Package initialization
│       ├── auth.py           # OAuth1 signature generation
│       ├── config.py         # Settings and configuration
│       ├── exceptions.py     # Custom exceptions
│       ├── models.py         # Pydantic data models
│       ├── api_client.py     # FatSecret API client
│       └── server.py         # MCP server implementation
├── tests/                    # Test suite
├── pyproject.toml           # Project configuration
├── .env.example             # Environment template
└── README.md                # This file
```

## API Documentation

- [FatSecret Platform API Documentation](https://platform.fatsecret.com/api/Default.aspx?screen=rapiref2)
- [OAuth1 Authentication Guide](https://platform.fatsecret.com/api/Default.aspx?screen=rapiauth)

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

For issues and questions:
- FatSecret API issues: Contact [FatSecret Support](https://platform.fatsecret.com/api/)
- MCP Server issues: Open an issue in this repository

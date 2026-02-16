"""Configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """FatSecret MCP Server settings."""

    model_config = SettingsConfigDict(
        env_prefix="FATSECRET_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # OAuth1 credentials
    consumer_key: str
    consumer_secret: str

    # API endpoints
    api_base_url: str = "https://platform.fatsecret.com/rest/server.api"

    # OAuth 1.0a 3-legged authentication endpoints
    oauth_request_token_url: str = (
        "https://authentication.fatsecret.com/oauth/request_token"
    )
    oauth_authorize_url: str = "https://authentication.fatsecret.com/oauth/authorize"
    oauth_access_token_url: str = (
        "https://authentication.fatsecret.com/oauth/access_token"
    )

    # Token storage path
    token_storage_path: str = "~/.config/fatsecret-mcp/tokens.json"


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()

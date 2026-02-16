"""Tests for OAuth 1.0a 3-legged flow."""

import os
import tempfile

import pytest
import respx
from httpx import Response

from fatsecret_mcp.config import Settings
from fatsecret_mcp.exceptions import OAuthFlowError
from fatsecret_mcp.models import RequestToken
from fatsecret_mcp.oauth_flow import OAuthFlowManager
from fatsecret_mcp.token_store import TokenStore


@pytest.fixture
def settings():
    """Return settings for tests."""
    return Settings(
        consumer_key="test_consumer_key",
        consumer_secret="test_consumer_secret",
    )


@pytest.fixture
def temp_storage_path():
    """Create a temporary storage path for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "tokens.json")


@pytest.fixture
def token_store(temp_storage_path):
    """Create a TokenStore instance with temporary storage."""
    return TokenStore(temp_storage_path)


@pytest.fixture
def oauth_flow(settings, token_store):
    """Create an OAuthFlowManager instance."""
    return OAuthFlowManager(settings, token_store)


class TestOAuthFlowManager:
    """Tests for OAuthFlowManager class."""

    @respx.mock
    async def test_get_request_token_success(self, oauth_flow, token_store):
        """Test successful request token retrieval."""
        # Mock the request token endpoint
        respx.post("https://authentication.fatsecret.com/oauth/request_token").mock(
            return_value=Response(
                200,
                text="oauth_token=request_token_123&oauth_token_secret=request_secret_456",
            )
        )

        token = await oauth_flow.get_request_token()

        assert token.oauth_token == "request_token_123"
        assert token.oauth_token_secret == "request_secret_456"

        # Verify token was saved to store
        saved = token_store.load_request_token()
        assert saved is not None
        assert saved.oauth_token == "request_token_123"

    @respx.mock
    async def test_get_request_token_http_error(self, oauth_flow):
        """Test request token retrieval with HTTP error."""
        respx.post("https://authentication.fatsecret.com/oauth/request_token").mock(
            return_value=Response(401, text="Unauthorized")
        )

        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.get_request_token()

        assert "HTTP 401" in str(exc_info.value)

    @respx.mock
    async def test_get_request_token_invalid_response(self, oauth_flow):
        """Test request token retrieval with invalid response."""
        respx.post("https://authentication.fatsecret.com/oauth/request_token").mock(
            return_value=Response(200, text="invalid_response")
        )

        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.get_request_token()

        assert "Invalid response" in str(exc_info.value)

    def test_get_authorization_url(self, oauth_flow):
        """Test authorization URL generation."""
        request_token = RequestToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
        )

        url = oauth_flow.get_authorization_url(request_token)

        assert url == (
            "https://authentication.fatsecret.com/oauth/authorize"
            "?oauth_token=test_token"
        )

    def test_get_authorization_url_encodes_special_chars(self, oauth_flow):
        """Test that authorization URL properly encodes special characters."""
        request_token = RequestToken(
            oauth_token="token+with=special&chars",
            oauth_token_secret="test_secret",
        )

        url = oauth_flow.get_authorization_url(request_token)

        # urllib.parse.quote encodes +, =, & but preserves /
        assert "token%2Bwith%3Dspecial%26chars" in url

    @respx.mock
    async def test_exchange_for_access_token_success(self, oauth_flow, token_store):
        """Test successful access token exchange."""
        # First save a request token
        request_token = RequestToken(
            oauth_token="request_token_123",
            oauth_token_secret="request_secret_456",
        )
        token_store.save_request_token(request_token)

        # Mock the access token endpoint
        respx.post("https://authentication.fatsecret.com/oauth/access_token").mock(
            return_value=Response(
                200,
                text="oauth_token=access_token_789&oauth_token_secret=access_secret_012",
            )
        )

        user_token = await oauth_flow.exchange_for_access_token("verifier_code")

        assert user_token.oauth_token == "access_token_789"
        assert user_token.oauth_token_secret == "access_secret_012"
        assert user_token.created_at is not None

        # Verify user token was saved
        saved = token_store.load_user_token()
        assert saved is not None
        assert saved.oauth_token == "access_token_789"

        # Verify request token was cleared
        assert token_store.load_request_token() is None

    async def test_exchange_for_access_token_no_request_token(self, oauth_flow):
        """Test exchange fails when no request token exists."""
        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.exchange_for_access_token("verifier_code")

        assert "No request token found" in str(exc_info.value)

    @respx.mock
    async def test_exchange_for_access_token_http_error(self, oauth_flow, token_store):
        """Test exchange with HTTP error."""
        # Save a request token first
        request_token = RequestToken(
            oauth_token="request_token_123",
            oauth_token_secret="request_secret_456",
        )
        token_store.save_request_token(request_token)

        respx.post("https://authentication.fatsecret.com/oauth/access_token").mock(
            return_value=Response(401, text="Invalid verifier")
        )

        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.exchange_for_access_token("invalid_verifier")

        assert "HTTP 401" in str(exc_info.value)

    @respx.mock
    async def test_exchange_for_access_token_invalid_response(
        self, oauth_flow, token_store
    ):
        """Test exchange with invalid response."""
        # Save a request token first
        request_token = RequestToken(
            oauth_token="request_token_123",
            oauth_token_secret="request_secret_456",
        )
        token_store.save_request_token(request_token)

        respx.post("https://authentication.fatsecret.com/oauth/access_token").mock(
            return_value=Response(200, text="invalid_response")
        )

        with pytest.raises(OAuthFlowError) as exc_info:
            await oauth_flow.exchange_for_access_token("verifier_code")

        assert "Invalid response" in str(exc_info.value)

    @respx.mock
    async def test_full_oauth_flow(self, oauth_flow, token_store):
        """Test the complete OAuth flow from start to finish."""
        # Step 1: Get request token
        respx.post("https://authentication.fatsecret.com/oauth/request_token").mock(
            return_value=Response(
                200,
                text="oauth_token=request_token&oauth_token_secret=request_secret",
            )
        )

        request_token = await oauth_flow.get_request_token()
        assert request_token.oauth_token == "request_token"

        # Step 2: Get authorization URL
        auth_url = oauth_flow.get_authorization_url(request_token)
        assert "oauth_token=request_token" in auth_url

        # Step 3: Exchange verifier for access token
        respx.post("https://authentication.fatsecret.com/oauth/access_token").mock(
            return_value=Response(
                200,
                text="oauth_token=access_token&oauth_token_secret=access_secret",
            )
        )

        user_token = await oauth_flow.exchange_for_access_token("user_verifier")

        assert user_token.oauth_token == "access_token"
        assert user_token.oauth_token_secret == "access_secret"

        # Verify final state
        assert token_store.has_user_token() is True
        assert token_store.load_request_token() is None

    async def test_close(self, oauth_flow):
        """Test closing the OAuth flow manager."""
        await oauth_flow.close()
        # Should not raise

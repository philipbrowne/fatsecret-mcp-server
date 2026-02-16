"""OAuth 1.0a 3-legged flow manager for FatSecret API."""

import urllib.parse

import httpx

from .auth import OAuth1Signer
from .config import Settings
from .exceptions import OAuthFlowError
from .models import RequestToken, UserToken
from .token_store import TokenStore


class OAuthFlowManager:
    """Manages the OAuth 1.0a 3-legged authentication flow.

    This implements the three-step OAuth handshake:
    1. Get a request token from FatSecret
    2. Generate an authorization URL for the user to visit
    3. Exchange the verifier code for an access token
    """

    def __init__(self, settings: Settings, token_store: TokenStore) -> None:
        """Initialize the OAuth flow manager.

        Args:
            settings: Application settings with OAuth endpoints.
            token_store: Token storage for persisting tokens.
        """
        self._settings = settings
        self._token_store = token_store
        self._client = httpx.AsyncClient()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_request_token(self, callback: str = "oob") -> RequestToken:
        """Step 1: Get a request token from FatSecret.

        Args:
            callback: Callback URL or "oob" for out-of-band (CLI apps).

        Returns:
            Request token for the authorization step.

        Raises:
            OAuthFlowError: If the request fails.
        """
        # Create a signer without user token for this request
        signer = OAuth1Signer(self._settings)

        # Build request parameters
        params = {"oauth_callback": callback}

        # Sign the request
        signed_params = signer.sign_request(
            self._settings.oauth_request_token_url,
            "POST",
            params,
        )

        try:
            response = await self._client.post(
                self._settings.oauth_request_token_url,
                data=signed_params,
            )
            response.raise_for_status()

            # Parse the response (form-encoded: oauth_token=xxx&oauth_token_secret=yyy)
            response_data = urllib.parse.parse_qs(response.text)

            oauth_token = response_data.get("oauth_token", [None])[0]
            oauth_token_secret = response_data.get("oauth_token_secret", [None])[0]

            if not oauth_token or not oauth_token_secret:
                raise OAuthFlowError(
                    f"Invalid response from request token endpoint: {response.text}"
                )

            token = RequestToken(
                oauth_token=oauth_token,
                oauth_token_secret=oauth_token_secret,
            )

            # Save the request token for later use in exchange_for_access_token
            self._token_store.save_request_token(token)

            return token

        except httpx.HTTPStatusError as e:
            raise OAuthFlowError(
                f"Failed to get request token: HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise OAuthFlowError(f"Failed to get request token: {str(e)}") from e

    def get_authorization_url(self, request_token: RequestToken) -> str:
        """Step 2: Generate the authorization URL for the user.

        Args:
            request_token: The request token from step 1.

        Returns:
            URL for the user to visit to authorize the application.
        """
        return (
            f"{self._settings.oauth_authorize_url}"
            f"?oauth_token={urllib.parse.quote(request_token.oauth_token)}"
        )

    async def exchange_for_access_token(self, verifier: str) -> UserToken:
        """Step 3: Exchange the verifier for an access token.

        Args:
            verifier: The verification code provided by the user after authorization.

        Returns:
            User access token for authenticated API calls.

        Raises:
            OAuthFlowError: If the exchange fails or no request token is found.
        """
        # Load the request token saved in step 1
        request_token = self._token_store.load_request_token()
        if not request_token:
            raise OAuthFlowError(
                "No request token found. Please start the authentication flow first."
            )

        # Create a signer with the request token
        signer = OAuth1Signer(
            self._settings,
            user_token=request_token.oauth_token,
            user_token_secret=request_token.oauth_token_secret,
        )

        # Build request parameters
        params = {"oauth_verifier": verifier}

        # Sign the request
        signed_params = signer.sign_request(
            self._settings.oauth_access_token_url,
            "POST",
            params,
        )

        try:
            response = await self._client.post(
                self._settings.oauth_access_token_url,
                data=signed_params,
            )
            response.raise_for_status()

            # Parse the response
            response_data = urllib.parse.parse_qs(response.text)

            oauth_token = response_data.get("oauth_token", [None])[0]
            oauth_token_secret = response_data.get("oauth_token_secret", [None])[0]

            if not oauth_token or not oauth_token_secret:
                raise OAuthFlowError(
                    f"Invalid response from access token endpoint: {response.text}"
                )

            import time

            user_token = UserToken(
                oauth_token=oauth_token,
                oauth_token_secret=oauth_token_secret,
                created_at=time.time(),
            )

            # Save the user token and clear the request token
            self._token_store.save_user_token(user_token)
            self._token_store.clear_request_token()

            return user_token

        except httpx.HTTPStatusError as e:
            raise OAuthFlowError(
                f"Failed to exchange for access token: HTTP {e.response.status_code}"
            ) from e
        except httpx.RequestError as e:
            raise OAuthFlowError(
                f"Failed to exchange for access token: {str(e)}"
            ) from e

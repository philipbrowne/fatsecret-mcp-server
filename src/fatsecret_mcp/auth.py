"""OAuth1 authentication for FatSecret API."""

import base64
import hashlib
import hmac
import secrets
import time
import urllib.parse

from .config import Settings


class OAuth1Signer:
    """Signs requests using OAuth1 HMAC-SHA1.

    Supports both two-legged (no user tokens) and three-legged (with user tokens)
    OAuth1 authentication.
    """

    def __init__(
        self,
        settings: Settings,
        user_token: str | None = None,
        user_token_secret: str | None = None,
    ) -> None:
        """Initialize the OAuth1 signer.

        Args:
            settings: Application settings containing OAuth1 credentials.
            user_token: Optional OAuth token for 3-legged authentication.
            user_token_secret: Optional OAuth token secret for 3-legged authentication.
        """
        self._consumer_key = settings.consumer_key
        self._consumer_secret = settings.consumer_secret
        self._user_token = user_token
        self._user_token_secret = user_token_secret or ""

    def sign_request(
        self,
        url: str,
        method: str = "POST",
        params: dict[str, str] | None = None,
    ) -> dict[str, str]:
        """Generate OAuth1 signed parameters for a request.

        Args:
            url: The request URL.
            method: HTTP method (GET or POST).
            params: Additional request parameters.

        Returns:
            Dictionary of all parameters including OAuth signature.
        """
        params = params or {}

        # Generate OAuth parameters
        oauth_params = {
            "oauth_consumer_key": self._consumer_key,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_nonce": self._generate_nonce(),
            "oauth_version": "1.0",
        }

        # Include oauth_token for 3-legged authentication
        if self._user_token:
            oauth_params["oauth_token"] = self._user_token

        # Combine all parameters for signing
        all_params = {**params, **oauth_params}

        # Generate signature
        signature = self._generate_signature(url, method, all_params)
        oauth_params["oauth_signature"] = signature

        # Return all parameters including signature
        return {**params, **oauth_params}

    def _generate_nonce(self) -> str:
        """Generate a unique nonce for the request.

        Returns:
            A random 32-character hex string.
        """
        return secrets.token_hex(16)

    def _generate_signature(
        self,
        url: str,
        method: str,
        params: dict[str, str],
    ) -> str:
        """Generate HMAC-SHA1 signature for OAuth1 request.

        Args:
            url: The request URL.
            method: HTTP method.
            params: All parameters to sign.

        Returns:
            Base64-encoded HMAC-SHA1 signature.
        """
        # Create signature base string
        base_string = self._create_signature_base_string(url, method, params)

        # Create signing key (consumer_secret&token_secret)
        # For two-legged OAuth, token_secret is empty
        # For three-legged OAuth, token_secret is the user's token secret
        signing_key = (
            f"{self._percent_encode(self._consumer_secret)}&"
            f"{self._percent_encode(self._user_token_secret)}"
        )

        # Generate HMAC-SHA1 signature
        hashed = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        )

        return base64.b64encode(hashed.digest()).decode("utf-8")

    def _create_signature_base_string(
        self,
        url: str,
        method: str,
        params: dict[str, str],
    ) -> str:
        """Create the OAuth1 signature base string.

        Args:
            url: The request URL.
            method: HTTP method.
            params: All parameters to include.

        Returns:
            The signature base string.
        """
        # Sort parameters alphabetically
        sorted_params = sorted(params.items())

        # Encode parameters
        param_string = "&".join(
            f"{self._percent_encode(k)}={self._percent_encode(str(v))}"
            for k, v in sorted_params
        )

        # Construct base string
        base_string = "&".join(
            [
                method.upper(),
                self._percent_encode(url),
                self._percent_encode(param_string),
            ]
        )

        return base_string

    @staticmethod
    def _percent_encode(value: str) -> str:
        """Percent-encode a value according to OAuth1 spec.

        Args:
            value: The value to encode.

        Returns:
            Percent-encoded string.
        """
        # OAuth1 requires RFC 3986 encoding
        return urllib.parse.quote(str(value), safe="")

"""Token storage for OAuth1 3-legged authentication."""

import json
import os
import time
from pathlib import Path

from .models import RequestToken, UserToken


class EnvTokenStore:
    """Environment variable-based token storage for cloud deployments.

    Reads user token from FATSECRET_USER_TOKEN and FATSECRET_USER_TOKEN_SECRET
    environment variables. Does not support writing (tokens must be set via
    environment configuration).
    """

    def load_user_token(self) -> UserToken | None:
        """Load user token from environment variables."""
        oauth_token = os.environ.get("FATSECRET_USER_TOKEN")
        oauth_token_secret = os.environ.get("FATSECRET_USER_TOKEN_SECRET")

        if not oauth_token or not oauth_token_secret:
            return None

        return UserToken(
            oauth_token=oauth_token,
            oauth_token_secret=oauth_token_secret,
        )

    def save_user_token(self, token: UserToken) -> None:
        """Not supported - tokens must be set via environment variables."""
        raise NotImplementedError(
            "EnvTokenStore does not support saving tokens. "
            "Set FATSECRET_USER_TOKEN and FATSECRET_USER_TOKEN_SECRET env vars."
        )

    def delete_user_token(self) -> None:
        """Not supported - tokens must be removed via environment variables."""
        pass

    def save_request_token(self, token: RequestToken) -> None:
        """Not supported for cloud deployments."""
        raise NotImplementedError(
            "OAuth flow not supported in cloud deployment. "
            "Complete OAuth locally and set env vars."
        )

    def load_request_token(self) -> RequestToken | None:
        """Not supported for cloud deployments."""
        return None

    def clear_request_token(self) -> None:
        """No-op for env-based storage."""
        pass

    def has_user_token(self) -> bool:
        """Check if user token env vars are set."""
        return bool(
            os.environ.get("FATSECRET_USER_TOKEN")
            and os.environ.get("FATSECRET_USER_TOKEN_SECRET")
        )


class TokenStore:
    """File-based token persistence for OAuth1 tokens.

    Stores tokens in a JSON file at the configured path with secure permissions.
    """

    def __init__(self, storage_path: str) -> None:
        """Initialize the token store.

        Args:
            storage_path: Path to the token storage file (supports ~ expansion).
        """
        self._storage_path = Path(os.path.expanduser(storage_path))
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the storage directory exists with secure permissions."""
        directory = self._storage_path.parent
        if not directory.exists():
            directory.mkdir(parents=True, mode=0o700)

    def _read_storage(self) -> dict:
        """Read the storage file.

        Returns:
            Dictionary containing stored data, or empty dict if file doesn't exist.
        """
        if not self._storage_path.exists():
            return {}
        try:
            with open(self._storage_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_storage(self, data: dict) -> None:
        """Write data to the storage file with secure permissions.

        Args:
            data: Dictionary to write to storage.
        """
        self._ensure_directory()

        # Write to temp file first, then rename for atomicity
        temp_path = self._storage_path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)

        # Set secure permissions (owner read/write only)
        os.chmod(temp_path, 0o600)

        # Atomic rename
        temp_path.rename(self._storage_path)

    def save_user_token(self, token: UserToken) -> None:
        """Save a user access token.

        Args:
            token: The user token to save.
        """
        data = self._read_storage()
        data["user_token"] = {
            "oauth_token": token.oauth_token,
            "oauth_token_secret": token.oauth_token_secret,
            "created_at": token.created_at or time.time(),
        }
        self._write_storage(data)

    def load_user_token(self) -> UserToken | None:
        """Load the stored user access token.

        Returns:
            The user token if it exists, None otherwise.
        """
        data = self._read_storage()
        token_data = data.get("user_token")
        if not token_data:
            return None
        return UserToken(
            oauth_token=token_data["oauth_token"],
            oauth_token_secret=token_data["oauth_token_secret"],
            created_at=token_data.get("created_at"),
        )

    def delete_user_token(self) -> None:
        """Delete the stored user access token."""
        data = self._read_storage()
        if "user_token" in data:
            del data["user_token"]
            self._write_storage(data)

    def save_request_token(self, token: RequestToken) -> None:
        """Save a temporary request token during OAuth flow.

        Args:
            token: The request token to save.
        """
        data = self._read_storage()
        data["request_token"] = {
            "oauth_token": token.oauth_token,
            "oauth_token_secret": token.oauth_token_secret,
        }
        self._write_storage(data)

    def load_request_token(self) -> RequestToken | None:
        """Load the stored request token.

        Returns:
            The request token if it exists, None otherwise.
        """
        data = self._read_storage()
        token_data = data.get("request_token")
        if not token_data:
            return None
        return RequestToken(
            oauth_token=token_data["oauth_token"],
            oauth_token_secret=token_data["oauth_token_secret"],
        )

    def clear_request_token(self) -> None:
        """Clear the temporary request token after OAuth flow completes."""
        data = self._read_storage()
        if "request_token" in data:
            del data["request_token"]
            self._write_storage(data)

    def has_user_token(self) -> bool:
        """Check if a user token is stored.

        Returns:
            True if a user token exists, False otherwise.
        """
        return self.load_user_token() is not None

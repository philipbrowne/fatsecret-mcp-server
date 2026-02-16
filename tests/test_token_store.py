"""Tests for token storage."""

import os
import tempfile
from pathlib import Path

import pytest

from fatsecret_mcp.models import RequestToken, UserToken
from fatsecret_mcp.token_store import TokenStore


@pytest.fixture
def temp_storage_path():
    """Create a temporary storage path for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "tokens.json")


@pytest.fixture
def token_store(temp_storage_path):
    """Create a TokenStore instance with temporary storage."""
    return TokenStore(temp_storage_path)


class TestTokenStore:
    """Tests for TokenStore class."""

    def test_save_and_load_user_token(self, token_store):
        """Test saving and loading a user token."""
        token = UserToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
            created_at=1234567890.0,
        )

        token_store.save_user_token(token)
        loaded = token_store.load_user_token()

        assert loaded is not None
        assert loaded.oauth_token == "test_token"
        assert loaded.oauth_token_secret == "test_secret"
        assert loaded.created_at == 1234567890.0

    def test_load_user_token_not_exists(self, token_store):
        """Test loading a user token when none exists."""
        loaded = token_store.load_user_token()
        assert loaded is None

    def test_delete_user_token(self, token_store):
        """Test deleting a user token."""
        token = UserToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
        )

        token_store.save_user_token(token)
        assert token_store.load_user_token() is not None

        token_store.delete_user_token()
        assert token_store.load_user_token() is None

    def test_delete_user_token_not_exists(self, token_store):
        """Test deleting a user token when none exists (no error)."""
        token_store.delete_user_token()  # Should not raise

    def test_save_and_load_request_token(self, token_store):
        """Test saving and loading a request token."""
        token = RequestToken(
            oauth_token="request_token",
            oauth_token_secret="request_secret",
        )

        token_store.save_request_token(token)
        loaded = token_store.load_request_token()

        assert loaded is not None
        assert loaded.oauth_token == "request_token"
        assert loaded.oauth_token_secret == "request_secret"

    def test_load_request_token_not_exists(self, token_store):
        """Test loading a request token when none exists."""
        loaded = token_store.load_request_token()
        assert loaded is None

    def test_clear_request_token(self, token_store):
        """Test clearing a request token."""
        token = RequestToken(
            oauth_token="request_token",
            oauth_token_secret="request_secret",
        )

        token_store.save_request_token(token)
        assert token_store.load_request_token() is not None

        token_store.clear_request_token()
        assert token_store.load_request_token() is None

    def test_clear_request_token_not_exists(self, token_store):
        """Test clearing a request token when none exists (no error)."""
        token_store.clear_request_token()  # Should not raise

    def test_has_user_token_true(self, token_store):
        """Test has_user_token when token exists."""
        token = UserToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
        )
        token_store.save_user_token(token)

        assert token_store.has_user_token() is True

    def test_has_user_token_false(self, token_store):
        """Test has_user_token when no token exists."""
        assert token_store.has_user_token() is False

    def test_storage_file_permissions(self, temp_storage_path, token_store):
        """Test that storage file has secure permissions."""
        token = UserToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
        )
        token_store.save_user_token(token)

        # Check file permissions (should be 0600)
        stat = os.stat(temp_storage_path)
        mode = stat.st_mode & 0o777
        assert mode == 0o600

    def test_storage_directory_permissions(self, temp_storage_path, token_store):
        """Test that storage directory has secure permissions."""
        # Create a nested path
        nested_path = os.path.join(
            os.path.dirname(temp_storage_path), "nested", "dir", "tokens.json"
        )
        store = TokenStore(nested_path)

        token = UserToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
        )
        store.save_user_token(token)

        # Check directory permissions (should be 0700)
        parent_dir = Path(nested_path).parent
        stat = os.stat(parent_dir)
        mode = stat.st_mode & 0o777
        assert mode == 0o700

    def test_both_tokens_can_coexist(self, token_store):
        """Test that user token and request token can both be stored."""
        user_token = UserToken(
            oauth_token="user_token",
            oauth_token_secret="user_secret",
        )
        request_token = RequestToken(
            oauth_token="request_token",
            oauth_token_secret="request_secret",
        )

        token_store.save_user_token(user_token)
        token_store.save_request_token(request_token)

        loaded_user = token_store.load_user_token()
        loaded_request = token_store.load_request_token()

        assert loaded_user is not None
        assert loaded_user.oauth_token == "user_token"
        assert loaded_request is not None
        assert loaded_request.oauth_token == "request_token"

    def test_user_token_created_at_auto_set(self, token_store):
        """Test that created_at is auto-set when not provided."""
        token = UserToken(
            oauth_token="test_token",
            oauth_token_secret="test_secret",
        )

        token_store.save_user_token(token)
        loaded = token_store.load_user_token()

        assert loaded is not None
        assert loaded.created_at is not None
        assert loaded.created_at > 0

    def test_handles_corrupted_storage(self, temp_storage_path, token_store):
        """Test that corrupted storage is handled gracefully."""
        # Write invalid JSON
        with open(temp_storage_path, "w") as f:
            f.write("not valid json")

        # Should return None, not raise
        loaded = token_store.load_user_token()
        assert loaded is None

    def test_tilde_expansion(self):
        """Test that ~ is expanded in storage path."""
        # Create with tilde path
        store = TokenStore("~/.config/test-fatsecret/tokens.json")

        # The internal path should be expanded
        assert "~" not in str(store._storage_path)
        assert store._storage_path.is_absolute()

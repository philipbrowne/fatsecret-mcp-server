"""Tests for OAuth1 authentication module."""

import base64
import hashlib
import hmac
import urllib.parse

import pytest

from fatsecret_mcp.auth import OAuth1Signer
from fatsecret_mcp.config import Settings


@pytest.fixture
def signer(settings: Settings) -> OAuth1Signer:
    """Create an OAuth1Signer with test credentials."""
    return OAuth1Signer(settings)


def test_sign_request_includes_oauth_params(signer: OAuth1Signer):
    """Test that signed requests include all required OAuth parameters."""
    url = "https://platform.fatsecret.com/rest/server.api"
    params = {"method": "foods.search", "search_expression": "banana"}

    signed = signer.sign_request(url, "POST", params)

    # Check all required OAuth params are present
    assert "oauth_consumer_key" in signed
    assert "oauth_signature_method" in signed
    assert "oauth_timestamp" in signed
    assert "oauth_nonce" in signed
    assert "oauth_version" in signed
    assert "oauth_signature" in signed

    # Check values
    assert signed["oauth_consumer_key"] == "test_consumer_key"
    assert signed["oauth_signature_method"] == "HMAC-SHA1"
    assert signed["oauth_version"] == "1.0"

    # Original params should be preserved
    assert signed["method"] == "foods.search"
    assert signed["search_expression"] == "banana"


def test_sign_request_generates_valid_signature(settings: Settings):
    """Test that the signature is correctly calculated."""
    signer = OAuth1Signer(settings)
    url = "https://platform.fatsecret.com/rest/server.api"
    params = {"method": "foods.search", "format": "json"}

    signed = signer.sign_request(url, "POST", params)

    # Verify signature is base64 encoded
    signature = signed["oauth_signature"]
    try:
        decoded = base64.b64decode(signature)
        # SHA1 produces 20 bytes
        assert len(decoded) == 20
    except Exception:
        pytest.fail("Signature is not valid base64")


def test_sign_request_unique_nonce():
    """Test that each request gets a unique nonce."""
    settings = Settings(
        consumer_key="test_key",
        consumer_secret="test_secret",
    )
    signer = OAuth1Signer(settings)
    url = "https://example.com/api"

    signed1 = signer.sign_request(url, "POST", {})
    signed2 = signer.sign_request(url, "POST", {})

    assert signed1["oauth_nonce"] != signed2["oauth_nonce"]


def test_sign_request_timestamp_is_current():
    """Test that timestamp is a reasonable Unix timestamp."""
    import time

    settings = Settings(
        consumer_key="test_key",
        consumer_secret="test_secret",
    )
    signer = OAuth1Signer(settings)
    url = "https://example.com/api"

    before = int(time.time())
    signed = signer.sign_request(url, "POST", {})
    after = int(time.time())

    timestamp = int(signed["oauth_timestamp"])
    assert before <= timestamp <= after


def test_percent_encode_special_characters():
    """Test that special characters are properly percent-encoded."""
    # OAuth1 requires RFC 3986 encoding
    assert OAuth1Signer._percent_encode("hello world") == "hello%20world"
    assert OAuth1Signer._percent_encode("test+value") == "test%2Bvalue"
    assert OAuth1Signer._percent_encode("foo=bar") == "foo%3Dbar"
    assert OAuth1Signer._percent_encode("a&b") == "a%26b"


def test_signature_base_string_format(settings: Settings):
    """Test signature base string is correctly formatted."""
    signer = OAuth1Signer(settings)

    # Create a known set of parameters
    params = {"b": "2", "a": "1", "c": "3"}
    base_string = signer._create_signature_base_string(
        "https://example.com/api",
        "POST",
        params,
    )

    # Should be: METHOD&URL&PARAMS (all percent-encoded)
    parts = base_string.split("&")
    assert len(parts) == 3
    assert parts[0] == "POST"
    assert urllib.parse.unquote(parts[1]) == "https://example.com/api"

    # Parameters should be sorted alphabetically
    param_string = urllib.parse.unquote(parts[2])
    assert param_string == "a=1&b=2&c=3"


def test_sign_request_with_empty_params(signer: OAuth1Signer):
    """Test signing a request with no additional parameters."""
    url = "https://platform.fatsecret.com/rest/server.api"

    signed = signer.sign_request(url, "POST", {})

    # Should still have OAuth params
    assert "oauth_consumer_key" in signed
    assert "oauth_signature" in signed


def test_sign_request_get_method(signer: OAuth1Signer):
    """Test signing a GET request."""
    url = "https://platform.fatsecret.com/rest/server.api"
    params = {"method": "foods.search"}

    signed = signer.sign_request(url, "GET", params)

    # Verify signature was generated
    assert "oauth_signature" in signed


def test_signature_changes_with_different_params(signer: OAuth1Signer):
    """Test that signature changes when parameters change."""
    url = "https://platform.fatsecret.com/rest/server.api"

    # Note: We can't directly compare signatures because nonce/timestamp
    # change each time. But we can verify the signature calculation is
    # deterministic by checking the base string.
    params1 = {"method": "foods.search", "query": "apple"}
    params2 = {"method": "foods.search", "query": "banana"}

    base1 = signer._create_signature_base_string(url, "POST", params1)
    base2 = signer._create_signature_base_string(url, "POST", params2)

    assert base1 != base2


def test_signature_verification_known_values():
    """Test signature generation against known values.

    This test uses fixed OAuth parameters to verify the signature
    calculation is correct.
    """
    settings = Settings(
        consumer_key="dpUt3F7ztk6D9Acjs9P8f",
        consumer_secret="qABCd1234efGHIJklmnOPqrs56",
    )
    signer = OAuth1Signer(settings)

    # Create base string manually to verify
    url = "https://platform.fatsecret.com/rest/server.api"
    params = {
        "method": "foods.search",
        "format": "json",
        "search_expression": "banana",
        "oauth_consumer_key": "dpUt3F7ztk6D9Acjs9P8f",
        "oauth_nonce": "abc123",
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": "1234567890",
        "oauth_version": "1.0",
    }

    # Calculate expected signature
    base_string = signer._create_signature_base_string(url, "POST", params)
    signing_key = f"{signer._percent_encode(settings.consumer_secret)}&"

    expected_sig = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("utf-8")

    # Generate signature using the signer
    actual_sig = signer._generate_signature(url, "POST", params)

    assert actual_sig == expected_sig

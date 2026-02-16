"""Custom exceptions for FatSecret MCP Server."""


class FatSecretError(Exception):
    """Base exception for FatSecret errors."""

    pass


class AuthenticationError(FatSecretError):
    """Raised when authentication fails."""

    pass


class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired."""

    pass


class APIError(FatSecretError):
    """Raised when the FatSecret API returns an error."""

    def __init__(self, message: str, error_code: int | None = None):
        super().__init__(message)
        self.error_code = error_code


class FoodNotFoundError(APIError):
    """Raised when a food item is not found."""

    pass


class RecipeNotFoundError(APIError):
    """Raised when a recipe is not found."""

    pass


class BarcodeNotFoundError(APIError):
    """Raised when a barcode lookup fails."""

    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""

    pass


class ConfigurationError(FatSecretError):
    """Raised when configuration is invalid or missing."""

    pass


class OAuthFlowError(FatSecretError):
    """Raised when OAuth handshake fails."""

    pass


class UserNotAuthenticatedError(FatSecretError):
    """Raised when an operation requires user auth but no user is connected."""

    pass

"""Exception hierarchy for the GitLab client."""


class GitLabError(Exception):
    """Base exception for all GitLab client errors."""


class AuthenticationError(GitLabError):
    """Raised when authentication fails (401)."""


class NotFoundError(GitLabError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found", status_code: int = 404):
        self.status_code = status_code
        super().__init__(message)


class APIError(GitLabError):
    """Raised for general API errors."""

    def __init__(self, message: str, status_code: int, response_body: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class ConfigurationError(GitLabError):
    """Raised when client configuration is invalid."""

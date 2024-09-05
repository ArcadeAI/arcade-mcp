from typing import Optional

import httpx


class ArcadeError(Exception):
    """Top-level exception for Arcade Client errors."""

    pass


class EngineOfflineError(ArcadeError):
    """Raised when the Arcade Engine is offline."""

    def __init__(self, message: str):
        super().__init__(message)


class EngineNotHealthyError(ArcadeError):
    """Raised when the Arcade Engine is not healthy."""

    def __init__(
        self,
        message: str,
        status_code: int,
    ):
        super().__init__(message)
        self.status_code = status_code


class APIError(ArcadeError):
    """Base class for API-related errors."""

    def __init__(self, message: str, request: httpx.Request, *, body: Optional[object] = None):
        super().__init__(message)
        self.message = message
        self.request = request
        self.body = body


class APIStatusError(APIError):
    """Raised when an API response has a status code of 4xx or 5xx."""

    def __init__(self, message: str, *, response: httpx.Response, body: Optional[object] = None):
        super().__init__(message, response.request, body=body)
        self.response = response
        self.status_code = response.status_code


class BadRequestError(APIStatusError):
    """400 Bad Request"""

    status_code = 400


class UnauthorizedError(APIStatusError):
    """401 Unauthorized"""

    status_code = 401


class PermissionDeniedError(APIStatusError):
    """403 Forbidden"""

    status_code = 403


class NotFoundError(APIStatusError):
    """404 Not Found"""

    status_code = 404


class RateLimitError(APIStatusError):
    """429 Too Many Requests"""

    status_code = 429


class InternalServerError(APIStatusError):
    """500 Internal Server Error"""

    status_code = 500


class UnprocessableEntityError(APIStatusError):
    """422 Unprocessable Entity"""

    status_code = 422


class ServiceUnavailableError(APIStatusError):
    """503 Service Unavailable"""

    status_code = 503

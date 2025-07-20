from typing import Any, NoReturn

import httpx
from pydantic import BaseModel

from .constants import API_BASE_URL, API_VERSION, MAX_ROWS_RETURNED


class GibsonAIError(Exception):
    """Base exception for GibsonAI API errors."""

    pass


class GibsonAIHTTPError(GibsonAIError):
    """HTTP-related errors from GibsonAI API."""

    pass


class GibsonAIQueryError(GibsonAIError):
    """Query execution errors from GibsonAI API."""

    pass


class GibsonAITimeoutError(GibsonAIError):
    """Timeout errors from GibsonAI API."""

    pass


class GibsonAINetworkError(GibsonAIError):
    """Network-related errors when connecting to GibsonAI API."""

    pass


class GibsonAIResponse(BaseModel):
    """Response model for GibsonAI API."""

    data: list[dict[str, Any]]
    success: bool
    error: str | None = None


def _raise_http_error(status_code: int, response_text: str) -> NoReturn:
    """Raise an HTTP error with formatted message."""
    error_msg = f"HTTP {status_code}: {response_text}"
    raise GibsonAIHTTPError(f"GibsonAI API error: {error_msg}")


def _raise_query_error(error_message: str) -> NoReturn:
    """Raise a query error with formatted message."""
    raise GibsonAIQueryError(f"GibsonAI query error: {error_message}")


def _raise_timeout_error() -> NoReturn:
    """Raise a timeout error."""
    raise GibsonAITimeoutError("Request timeout - GibsonAI API took too long to respond")


def _raise_network_error(error: Exception) -> NoReturn:
    """Raise a network error with original exception details."""
    raise GibsonAINetworkError(f"Network error connecting to GibsonAI API: {error}")


def _raise_unexpected_error(error: Exception) -> NoReturn:
    """Raise an unexpected error."""
    raise GibsonAIError(f"Unexpected error: {error}")


def _process_response_data(result: Any) -> list[str]:
    """Process the API response data into a list of strings."""
    if isinstance(result, dict):
        if result.get("error"):
            _raise_query_error(result["error"])
        elif "data" in result:
            return [str(row) for row in result["data"]]
        else:
            return [str(result)]
    elif isinstance(result, list):
        return [str(row) for row in result]
    else:
        return [str(result)]


class GibsonAIClient:
    """Client for interacting with GibsonAI Data API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"{API_BASE_URL}/{API_VERSION}"
        self.headers = {"Content-Type": "application/json", "X-Gibson-API-Key": api_key}

    async def execute_query(self, query: str, params: list[Any] | None = None) -> list[str]:
        """Execute a query against GibsonAI database."""
        if params is None:
            params = []

        payload = {"array_mode": False, "params": params, "query": query}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/-/query",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code != 200:
                    _raise_http_error(response.status_code, response.text)

                result = response.json()
                results = _process_response_data(result)

                # Limit results to avoid memory issues
                return results[:MAX_ROWS_RETURNED]

        except httpx.TimeoutException:
            _raise_timeout_error()
        except httpx.RequestError as e:
            _raise_network_error(e)
        except GibsonAIError:
            # Re-raise our custom exceptions as-is
            raise
        except Exception as e:
            _raise_unexpected_error(e)

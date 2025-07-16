from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel

from .constants import API_BASE_URL, API_VERSION, MAX_ROWS_RETURNED


class GibsonAIResponse(BaseModel):
    """Response model for GibsonAI API."""

    data: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None


class GibsonAIClient:
    """Client for interacting with GibsonAI Data API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = f"{API_BASE_URL}/{API_VERSION}"
        self.headers = {"Content-Type": "application/json", "X-Gibson-API-Key": api_key}

    async def execute_query(
        self, query: str, params: Optional[List[Any]] = None
    ) -> List[str]:
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
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    raise Exception(f"GibsonAI API error: {error_msg}")

                result = response.json()

                # Handle different response formats
                if isinstance(result, dict):
                    if "error" in result and result["error"]:
                        raise Exception(f"GibsonAI query error: {result['error']}")
                    elif "data" in result:
                        results = [str(row) for row in result["data"]]
                    else:
                        results = [str(result)]
                elif isinstance(result, list):
                    results = [str(row) for row in result]
                else:
                    results = [str(result)]

                # Limit results to avoid memory issues
                return results[:MAX_ROWS_RETURNED]

        except httpx.TimeoutException:
            raise Exception("Request timeout - GibsonAI API took too long to respond")
        except httpx.RequestError as e:
            raise Exception(f"Network error connecting to GibsonAI API: {e}")
        except Exception as e:
            # Re-raise if it's already our custom exception
            if "GibsonAI" in str(e):
                raise
            else:
                raise Exception(f"Unexpected error: {e}")

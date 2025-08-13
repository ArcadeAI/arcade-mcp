import logging
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_opentable.utils import (
    validate_coordinates,
    validate_date_format,
    validate_limit_parameter,
    validate_party_size,
    validate_time_format,
)

logger = logging.getLogger(__name__)


@tool(
    requires_auth=OAuth2(id="opentable", scopes=["read"]),
    requires_secrets=["OPENTABLE_PARTNER_ID"],
)
async def search_restaurants(
    context: ToolContext,
    query: Annotated[
        str | None,
        "Search query for restaurant name, cuisine type, or location",
    ] = None,
    location: Annotated[
        str | None,
        "Location to search for restaurants (city, address, or coordinates)",
    ] = None,
    latitude: Annotated[
        float | None,
        "Latitude coordinate for location-based search",
    ] = None,
    longitude: Annotated[
        float | None,
        "Longitude coordinate for location-based search",
    ] = None,
    party_size: Annotated[
        int,
        "Number of people in the party (defaults to 2)",
    ] = 2,
    date: Annotated[
        str | None,
        "Reservation date in YYYY-MM-DD format",
    ] = None,
    time: Annotated[
        str | None,
        "Reservation time in HH:MM format (24-hour)",
    ] = None,
    cuisine_type: Annotated[
        str | None,
        "Type of cuisine (e.g., Italian, Japanese, Mexican)",
    ] = None,
    price_range: Annotated[
        str | None,
        "Price range filter (e.g., $, $$, $$$, $$$$)",
    ] = None,
    radius: Annotated[
        float | None,
        "Search radius in miles from the specified location (defaults to 5)",
    ] = 5.0,
    limit: Annotated[
        int,
        "Maximum number of restaurants to return (defaults to 20)",
    ] = 20,
) -> Annotated[
    dict[str, Any],
    "List of restaurants matching the search criteria with details like name, address, "
    "cuisine type, price range, ratings, and availability",
]:
    """
    Search for restaurants using OpenTable's database.

    This tool searches for restaurants based on various criteria including location,
    cuisine type, price range, and availability. At least one search parameter
    (query, location, or coordinates) must be provided.

    The search returns detailed restaurant information including:
    - Restaurant name and description
    - Address and contact information
    - Cuisine type and price range
    - Ratings and reviews summary
    - Availability for the specified date/time
    - Reservation booking links
    """
    return await _search_restaurants_impl(
        context,
        query,
        location,
        latitude,
        longitude,
        party_size,
        date,
        time,
        cuisine_type,
        price_range,
        radius,
        limit,
    )


async def _search_restaurants_impl(
    context: ToolContext,
    query: str | None,
    location: str | None,
    latitude: float | None,
    longitude: float | None,
    party_size: int,
    date: str | None,
    time: str | None,
    cuisine_type: str | None,
    price_range: str | None,
    radius: float | None,
    limit: int,
) -> dict[str, Any]:
    """Implementation of search_restaurants to reduce complexity."""
    # Validate inputs
    _validate_search_inputs(query, location, latitude, longitude, party_size, date, time, limit)

    auth_token = context.get_auth_token_or_empty()
    partner_id = context.get_secret("OPENTABLE_PARTNER_ID")

    # OpenTable API base URL (this would be the actual endpoint)
    url = "https://api.opentable.com/v1/restaurants/search"

    # Build search parameters
    params = _build_search_params(
        partner_id,
        query,
        location,
        latitude,
        longitude,
        party_size,
        date,
        time,
        cuisine_type,
        price_range,
        radius,
        limit,
    )

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Arcade-OpenTable-Toolkit/1.0",
            }

            response = await client.get(url, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()

            data = response.json()

            logger.info(f"Restaurant search returned {len(data.get('restaurants', []))} results")

            return {
                "restaurants": data.get("restaurants", []),
                "total_count": data.get("total_count", 0),
                "search_params": params,
                "has_more": data.get("has_more", False),
            }

        except httpx.HTTPStatusError as e:
            _handle_http_error_for_search(e, url, params)
        except httpx.TimeoutException as e:
            logger.exception("Timeout during restaurant search")
            raise RetryableToolError(
                message="Request timed out while searching restaurants.",
                developer_message=f"Timeout occurred. URL: {url}, params: {params}",
                retry_after_ms=5000,
            ) from e

        except Exception as e:
            logger.exception("Unexpected error during restaurant search")
            raise ToolExecutionError(
                message=f"Failed to search restaurants: {e!s}",
                developer_message=f"Unexpected error: {type(e).__name__}: {e!s}",
            ) from e


def _validate_search_inputs(
    query: str | None,
    location: str | None,
    latitude: float | None,
    longitude: float | None,
    party_size: int,
    date: str | None,
    time: str | None,
    limit: int,
) -> None:
    """Validate search input parameters to reduce complexity."""
    # Validate that at least one search parameter is provided
    if not any([query, location, latitude, longitude]):
        raise RetryableToolError(
            message="At least one search parameter must be provided.",
            developer_message="No search parameters were provided",
            retry_after_ms=100,
            additional_prompt_content=(
                "Provide at least one of: query, location, or coordinates (latitude/longitude)"
            ),
        )

    # Use utility functions for validation
    validate_coordinates(latitude, longitude)
    validate_party_size(party_size)
    validate_limit_parameter(limit)

    # Validate optional date and time parameters
    if date:
        validate_date_format(date, allow_past=False)

    if time:
        validate_time_format(time, param_name="time")


def _build_search_params(
    partner_id: str,
    query: str | None,
    location: str | None,
    latitude: float | None,
    longitude: float | None,
    party_size: int,
    date: str | None,
    time: str | None,
    cuisine_type: str | None,
    price_range: str | None,
    radius: float | None,
    limit: int,
) -> dict[str, Any]:
    """Build search parameters to reduce complexity."""
    params: dict[str, Any] = {
        "partner_id": partner_id,
        "party_size": party_size,
        "limit": limit,
    }

    if query:
        params["query"] = query

    if location:
        params["location"] = location

    if latitude is not None and longitude is not None:
        params["latitude"] = latitude
        params["longitude"] = longitude
        params["radius"] = radius

    if date:
        params["date"] = date

    if time:
        params["time"] = time

    if cuisine_type:
        params["cuisine"] = cuisine_type

    if price_range:
        params["price_range"] = price_range

    return params


def _handle_http_error_for_search(
    e: httpx.HTTPStatusError, url: str, params: dict[str, Any]
) -> None:
    """Handle HTTP errors for restaurant search to reduce complexity."""
    logger.exception(f"HTTP error during restaurant search: {e.response.status_code}")

    if e.response.status_code == 401:
        raise ToolExecutionError(
            message="Authentication failed. Please check your OpenTable API credentials.",
            developer_message=f"HTTP 401 Unauthorized: {e.response.text}",
        ) from e
    elif e.response.status_code == 403:
        raise ToolExecutionError(
            message="Access forbidden. Your API key may not have permission for this operation.",
            developer_message=f"HTTP 403 Forbidden: {e.response.text}",
        ) from e
    elif e.response.status_code == 429:
        raise RetryableToolError(
            message="Rate limit exceeded. Please try again later.",
            developer_message=f"HTTP 429 Rate Limited: {e.response.text}",
            retry_after_ms=60000,  # 1 minute
        ) from e
    else:
        raise ToolExecutionError(
            message=f"Failed to search restaurants: HTTP {e.response.status_code}",
            developer_message=f"HTTP {e.response.status_code} error: {e.response.text}",
        ) from e

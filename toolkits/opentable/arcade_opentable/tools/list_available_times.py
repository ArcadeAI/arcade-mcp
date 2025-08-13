import logging
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_opentable.utils import (
    validate_date_format,
    validate_non_empty_string,
    validate_party_size,
    validate_time_format,
    validate_time_range,
)

logger = logging.getLogger(__name__)


@tool(
    requires_auth=OAuth2(id="opentable", scopes=["read"]),
    requires_secrets=["OPENTABLE_PARTNER_ID"],
)
async def list_available_times(
    context: ToolContext,
    restaurant_id: Annotated[
        str,
        "OpenTable restaurant ID (obtained from search_restaurants)",
    ],
    date: Annotated[
        str,
        "Date to check availability in YYYY-MM-DD format",
    ],
    party_size: Annotated[
        int,
        "Number of people in the party",
    ],
    earliest_time: Annotated[
        str | None,
        "Earliest acceptable reservation time in HH:MM format (24-hour)",
    ] = None,
    latest_time: Annotated[
        str | None,
        "Latest acceptable reservation time in HH:MM format (24-hour)",
    ] = None,
    seating_preference: Annotated[
        str | None,
        "Preferred seating type (e.g., 'indoor', 'outdoor', 'bar', 'standard')",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "Available reservation times with details about each time slot including duration, "
    "seating options, and any special notes or restrictions",
]:
    """
    Get available reservation times for a specific restaurant on a given date.

    This tool retrieves all available booking time slots for the specified restaurant,
    date, and party size. Use this before making a reservation to see what times
    are actually available.

    The response includes:
    - Available time slots with exact times
    - Duration of each reservation slot
    - Seating type and table availability
    - Any special notes or restrictions for each time slot
    - Pricing information if applicable
    - Whether online booking is available for each slot
    """
    return await _list_available_times_impl(
        context, restaurant_id, date, party_size, earliest_time, latest_time, seating_preference
    )


async def _list_available_times_impl(
    context: ToolContext,
    restaurant_id: str,
    date: str,
    party_size: int,
    earliest_time: str | None,
    latest_time: str | None,
    seating_preference: str | None,
) -> dict[str, Any]:
    """Implementation of list_available_times to reduce complexity."""
    # Validate inputs
    _validate_availability_inputs(restaurant_id, date, party_size, earliest_time, latest_time)

    auth_token = context.get_auth_token_or_empty()
    partner_id = context.get_secret("OPENTABLE_PARTNER_ID")

    # OpenTable API availability endpoint
    url = f"https://api.opentable.com/v1/restaurants/{restaurant_id}/availability"

    # Build query parameters
    params = _build_availability_params(
        partner_id, date, party_size, earliest_time, latest_time, seating_preference
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

            available_times = data.get("available_times", [])
            logger.info(
                f"Found {len(available_times)} available time slots for restaurant {restaurant_id}"
            )

            # Format the response with comprehensive information
            result = {
                "restaurant_id": restaurant_id,
                "date": date,
                "party_size": party_size,
                "available_times": available_times,
                "restaurant_info": {
                    "name": data.get("restaurant", {}).get("name"),
                    "address": data.get("restaurant", {}).get("address"),
                    "phone": data.get("restaurant", {}).get("phone"),
                    "timezone": data.get("restaurant", {}).get("timezone"),
                },
                "search_criteria": {
                    "earliest_time": earliest_time,
                    "latest_time": latest_time,
                    "seating_preference": seating_preference,
                },
                "booking_policies": data.get("booking_policies", {}),
                "special_notes": data.get("special_notes", []),
                "has_availability": len(available_times) > 0,
            }

        except httpx.HTTPStatusError as e:
            _handle_http_error_for_availability(e, url, params)
        except httpx.TimeoutException as e:
            logger.exception("Timeout during availability check")
            raise RetryableToolError(
                message="Request timed out while checking availability.",
                developer_message=f"Timeout occurred. URL: {url}, params: {params}",
                retry_after_ms=5000,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during availability check")
            raise ToolExecutionError(
                message=f"Failed to check availability: {e!s}",
                developer_message=f"Unexpected error: {type(e).__name__}: {e!s}",
            ) from e
        else:
            return result


def _validate_availability_inputs(
    restaurant_id: str,
    date: str,
    party_size: int,
    earliest_time: str | None,
    latest_time: str | None,
) -> None:
    """Validate availability input parameters to reduce complexity."""
    # Use utility functions for validation
    validate_non_empty_string(restaurant_id, "restaurant_id")
    validate_party_size(party_size)
    validate_date_format(date, allow_past=False)

    # Validate optional time parameters
    if earliest_time:
        validate_time_format(earliest_time, param_name="earliest_time")

    if latest_time:
        validate_time_format(latest_time, param_name="latest_time")

    # Validate time range if both times are provided
    if earliest_time and latest_time:
        validate_time_range(earliest_time, latest_time)


def _build_availability_params(
    partner_id: str,
    date: str,
    party_size: int,
    earliest_time: str | None,
    latest_time: str | None,
    seating_preference: str | None,
) -> dict[str, Any]:
    """Build availability query parameters to reduce complexity."""
    params: dict[str, Any] = {
        "partner_id": partner_id,
        "date": date,
        "party_size": party_size,
    }

    if earliest_time:
        params["earliest_time"] = earliest_time

    if latest_time:
        params["latest_time"] = latest_time

    if seating_preference:
        params["seating_preference"] = seating_preference

    return params


def _handle_http_error_for_availability(
    e: httpx.HTTPStatusError, url: str, params: dict[str, Any]
) -> None:
    """Handle HTTP errors for availability check to reduce complexity."""
    logger.exception(f"HTTP error during availability check: {e.response.status_code}")

    if e.response.status_code == 400:
        error_data = (
            e.response.json()
            if e.response.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        error_message = error_data.get("message", "Invalid availability request")

        raise RetryableToolError(
            message=f"Availability request failed: {error_message}",
            developer_message=f"HTTP 400 Bad Request: {e.response.text}",
            retry_after_ms=1000,
            additional_prompt_content="Check request parameters and try again",
        ) from e

    elif e.response.status_code == 401:
        raise ToolExecutionError(
            message="Authentication failed. Please check your OpenTable API credentials.",
            developer_message=f"HTTP 401 Unauthorized: {e.response.text}",
        ) from e

    elif e.response.status_code == 403:
        raise ToolExecutionError(
            message="Access forbidden. Your API key may not have permission for availability checks.",
            developer_message=f"HTTP 403 Forbidden: {e.response.text}",
        ) from e

    elif e.response.status_code == 404:
        raise ToolExecutionError(
            message="Restaurant not found. Please verify the restaurant ID.",
            developer_message=f"HTTP 404 Not Found: {e.response.text}",
        ) from e

    elif e.response.status_code == 429:
        raise RetryableToolError(
            message="Rate limit exceeded. Please try again later.",
            developer_message=f"HTTP 429 Rate Limited: {e.response.text}",
            retry_after_ms=60000,  # 1 minute
        ) from e
    else:
        raise ToolExecutionError(
            message=f"Failed to check availability: HTTP {e.response.status_code}",
            developer_message=f"HTTP {e.response.status_code} error: {e.response.text}",
        ) from e

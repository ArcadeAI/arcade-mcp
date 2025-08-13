import logging
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import RetryableToolError, ToolExecutionError

from arcade_opentable.utils import (
    validate_date_format,
    validate_email_format,
    validate_non_empty_string,
    validate_party_size,
    validate_phone_format,
    validate_time_format,
)

logger = logging.getLogger(__name__)


@tool(
    requires_auth=OAuth2(id="opentable", scopes=["read", "write"]),
    requires_secrets=["OPENTABLE_PARTNER_ID"],
)
async def make_reservation(
    context: ToolContext,
    restaurant_id: Annotated[
        str,
        "OpenTable restaurant ID (obtained from search_restaurants)",
    ],
    date: Annotated[
        str,
        "Date for the reservation in YYYY-MM-DD format",
    ],
    time: Annotated[
        str,
        "Reservation time in HH:MM format (24-hour)",
    ],
    party_size: Annotated[
        int,
        "Number of people in the party",
    ],
    customer_first_name: Annotated[
        str,
        "Customer's first name",
    ],
    customer_last_name: Annotated[
        str,
        "Customer's last name",
    ],
    customer_email: Annotated[
        str,
        "Customer's email address",
    ],
    customer_phone: Annotated[
        str,
        "Customer's phone number",
    ],
    special_requests: Annotated[
        str | None,
        "Any special requests or dietary restrictions",
    ] = None,
    seating_preference: Annotated[
        str | None,
        "Preferred seating type (e.g., 'indoor', 'outdoor', 'bar', 'standard')",
    ] = None,
    occasion: Annotated[
        str | None,
        "Special occasion (e.g., 'birthday', 'anniversary', 'business')",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "Reservation confirmation with details including reservation ID, confirmation number, "
    "and next steps for the customer",
]:
    """
    Make a reservation at a specific restaurant.

    This tool creates a new reservation at the specified restaurant with the given
    date, time, and party size. The reservation includes customer contact information
    and can accommodate special requests and seating preferences.

    The response includes:
    - Reservation ID and confirmation number
    - Restaurant details and contact information
    - Reservation date, time, and party size
    - Customer information provided
    - Any special requests or preferences
    - Next steps and booking confirmation
    """
    return await _make_reservation_impl(
        context,
        restaurant_id,
        date,
        time,
        party_size,
        customer_first_name,
        customer_last_name,
        customer_email,
        customer_phone,
        special_requests,
        seating_preference,
        occasion,
    )


async def _make_reservation_impl(
    context: ToolContext,
    restaurant_id: str,
    date: str,
    time: str,
    party_size: int,
    customer_first_name: str,
    customer_last_name: str,
    customer_email: str,
    customer_phone: str,
    special_requests: str | None,
    seating_preference: str | None,
    occasion: str | None,
) -> dict[str, Any]:
    """Implementation of make_reservation to reduce complexity."""
    # Use utility functions for validation
    validate_non_empty_string(restaurant_id, "restaurant_id")
    validate_date_format(date, allow_past=False)
    validate_time_format(time, param_name="time")
    validate_party_size(party_size)
    validate_non_empty_string(customer_first_name, "customer_first_name")
    validate_non_empty_string(customer_last_name, "customer_last_name")
    validate_email_format(customer_email)
    validate_phone_format(customer_phone)

    auth_token = context.get_auth_token_or_empty()
    partner_id = context.get_secret("OPENTABLE_PARTNER_ID")

    # OpenTable API reservation endpoint
    url = f"https://api.opentable.com/v1/restaurants/{restaurant_id}/reservations"

    # Build request payload
    payload: dict[str, Any] = {
        "partner_id": partner_id,
        "date": date,
        "time": time,
        "party_size": party_size,
        "customer": {
            "first_name": customer_first_name,
            "last_name": customer_last_name,
            "email": customer_email,
            "phone": customer_phone,
        },
    }

    if special_requests:
        payload["special_requests"] = special_requests

    if seating_preference:
        payload["seating_preference"] = seating_preference

    if occasion:
        payload["occasion"] = occasion

    async with httpx.AsyncClient() as client:
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "Arcade-OpenTable-Toolkit/1.0",
            }

            response = await client.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()

            data = response.json()

            # Format the response to include all relevant information
            result = {
                "reservation_id": data.get("reservation_id"),
                "confirmation_number": data.get("confirmation_number"),
                "status": data.get("status", "pending"),
                "restaurant": {
                    "id": restaurant_id,
                    "name": data.get("restaurant", {}).get("name"),
                    "address": data.get("restaurant", {}).get("address"),
                    "phone": data.get("restaurant", {}).get("phone"),
                },
                "reservation_details": {
                    "date": date,
                    "time": time,
                    "party_size": party_size,
                    "customer": {
                        "name": f"{customer_first_name} {customer_last_name}",
                        "email": customer_email,
                        "phone": customer_phone,
                    },
                },
                "booking_url": data.get("booking_url"),
                "next_steps": data.get("next_steps", []),
                "special_requests": special_requests,
                "seating_preference": seating_preference,
                "occasion": occasion,
            }

        except httpx.HTTPStatusError as e:
            _handle_http_error_for_reservation(e, url)
        except httpx.TimeoutException as e:
            logger.exception("Timeout during reservation creation")
            raise RetryableToolError(
                message="Request timed out while creating reservation.",
                developer_message=f"Timeout occurred. URL: {url}",
                retry_after_ms=5000,
            ) from e
        except Exception as e:
            logger.exception("Unexpected error during reservation creation")
            raise ToolExecutionError(
                message=f"Failed to create reservation: {e!s}",
                developer_message=f"Unexpected error: {type(e).__name__}: {e!s}",
            ) from e
        else:
            return result


def _handle_http_error_for_reservation(e: httpx.HTTPStatusError, url: str) -> None:
    """Handle HTTP errors for reservation creation to reduce complexity."""
    logger.exception(f"HTTP error during reservation: {e.response.status_code}")

    if e.response.status_code == 400:
        error_data = (
            e.response.json()
            if e.response.headers.get("content-type", "").startswith("application/json")
            else {}
        )
        error_message = error_data.get("message", "Invalid reservation request")

        raise RetryableToolError(
            message=f"Reservation request failed: {error_message}",
            developer_message=f"HTTP 400 Bad Request: {e.response.text}",
            retry_after_ms=1000,
            additional_prompt_content="Check reservation details and try again",
        ) from e

    elif e.response.status_code == 401:
        raise ToolExecutionError(
            message="Authentication failed. Please check your OpenTable API credentials.",
            developer_message=f"HTTP 401 Unauthorized: {e.response.text}",
        ) from e

    elif e.response.status_code == 403:
        raise ToolExecutionError(
            message="Access forbidden. Your API key may not have permission for reservations.",
            developer_message=f"HTTP 403 Forbidden: {e.response.text}",
        ) from e

    elif e.response.status_code == 404:
        raise ToolExecutionError(
            message="Restaurant not found. Please verify the restaurant ID.",
            developer_message=f"HTTP 404 Not Found: {e.response.text}",
        ) from e

    elif e.response.status_code == 409:
        raise ToolExecutionError(
            message="Reservation conflict. The requested time slot may not be available.",
            developer_message=f"HTTP 409 Conflict: {e.response.text}",
        ) from e

    elif e.response.status_code == 429:
        raise RetryableToolError(
            message="Rate limit exceeded. Please try again later.",
            developer_message=f"HTTP 429 Rate Limited: {e.response.text}",
            retry_after_ms=60000,  # 1 minute
        ) from e
    else:
        raise ToolExecutionError(
            message=f"Failed to make reservation: HTTP {e.response.status_code}",
            developer_message=f"HTTP {e.response.status_code} error: {e.response.text}",
        ) from e

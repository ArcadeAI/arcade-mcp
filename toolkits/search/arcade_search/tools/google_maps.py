from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_search.constants import (
    DEFAULT_GOOGLE_MAPS_COUNTRY,
    DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
    DEFAULT_GOOGLE_MAPS_LANGUAGE,
    DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
)
from arcade_search.enums import GoogleMapsDistanceUnit, GoogleMapsTravelMode
from arcade_search.utils import get_google_maps_directions


@tool(requires_secrets=["SERP_API_KEY"])
async def get_directions_between_addresses(
    context: ToolContext,
    origin_address: Annotated[
        str, "The origin address. Example: '123 Main St, New York, NY 10001'"
    ],
    destination_address: Annotated[
        str, "The destination address. Example: '456 Main St, New York, NY 10001'"
    ],
    language: Annotated[
        str,
        "2-character language code to use in the Google Maps search. "
        f"Defaults to '{DEFAULT_GOOGLE_MAPS_LANGUAGE}'.",
    ] = DEFAULT_GOOGLE_MAPS_LANGUAGE,
    country: Annotated[
        str | None,
        "2-character country code to use in the Google Maps search. "
        f"Defaults to '{DEFAULT_GOOGLE_MAPS_COUNTRY}'.",
    ] = DEFAULT_GOOGLE_MAPS_COUNTRY,
    distance_unit: Annotated[
        GoogleMapsDistanceUnit,
        f"Distance unit to use in the Google Maps search. Defaults to "
        f"'{DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT}'.",
    ] = DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
    travel_mode: Annotated[
        GoogleMapsTravelMode,
        f"Travel mode to use in the Google Maps search. Defaults to "
        f"'{DEFAULT_GOOGLE_MAPS_TRAVEL_MODE}'.",
    ] = DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
) -> Annotated[dict, "The directions from Google Maps"]:
    """Get directions from Google Maps."""
    return {
        "directions": get_google_maps_directions(
            context=context,
            origin_address=origin_address,
            destination_address=destination_address,
            language=language,
            country=country,
            distance_unit=distance_unit,
            travel_mode=travel_mode,
        ),
    }


@tool(requires_secrets=["SERP_API_KEY"])
async def get_directions_between_coordinates(
    context: ToolContext,
    origin_latitude: Annotated[str, "The origin latitude. E.g. '40.7128'"],
    origin_longitude: Annotated[str, "The origin longitude. E.g. '-74.0060'"],
    destination_latitude: Annotated[str, "The destination latitude. E.g. '40.7128'"],
    destination_longitude: Annotated[str, "The destination longitude. E.g. '-74.0060'"],
    language: Annotated[
        str,
        "2-letter language code to use in the Google Maps search. "
        f"Defaults to '{DEFAULT_GOOGLE_MAPS_LANGUAGE}'.",
    ] = DEFAULT_GOOGLE_MAPS_LANGUAGE,
    country: Annotated[
        str | None,
        f"2-letter country code to use in the Google Maps search. Defaults to "
        f"'{DEFAULT_GOOGLE_MAPS_COUNTRY}'.",
    ] = DEFAULT_GOOGLE_MAPS_COUNTRY,
    distance_unit: Annotated[
        GoogleMapsDistanceUnit,
        f"Distance unit to use in the Google Maps search. Defaults to "
        f"'{DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT}'.",
    ] = DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
    travel_mode: Annotated[
        GoogleMapsTravelMode,
        f"Travel mode to use in the Google Maps search. Defaults to "
        f"'{DEFAULT_GOOGLE_MAPS_TRAVEL_MODE}'.",
    ] = DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
) -> Annotated[dict, "The directions from Google Maps"]:
    """Get directions from Google Maps."""
    return {
        "directions": get_google_maps_directions(
            context=context,
            origin_latitude=origin_latitude,
            origin_longitude=origin_longitude,
            destination_latitude=destination_latitude,
            destination_longitude=destination_longitude,
            language=language,
            country=country,
            distance_unit=distance_unit,
            travel_mode=travel_mode,
        ),
    }

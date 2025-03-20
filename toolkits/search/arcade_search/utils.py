import contextlib
import re
from datetime import datetime
from typing import Any, Optional, cast
from zoneinfo import ZoneInfo

from arcade.sdk import ToolContext
from arcade.sdk.errors import ToolExecutionError
from serpapi import Client as SerpClient

from arcade_search.constants import (
    DEFAULT_GOOGLE_COUNTRY,
    DEFAULT_GOOGLE_LANGUAGE,
    DEFAULT_GOOGLE_MAPS_COUNTRY,
    DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
    DEFAULT_GOOGLE_MAPS_LANGUAGE,
    DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
)
from arcade_search.enums import GoogleMapsDistanceUnit, GoogleMapsTravelMode
from arcade_search.exceptions import CountryNotFoundError, LanguageNotFoundError
from arcade_search.google_data import COUNTRY_CODES, LANGUAGE_CODES


# ------------------------------------------------------------------------------------------------
# General SerpAPI utils
# ------------------------------------------------------------------------------------------------
def prepare_params(engine: str, **kwargs: Any) -> dict[str, Any]:
    """
    Prepares a parameters dictionary for the SerpAPI call.

    Parameters:
        engine: The engine name (e.g., "google", "google_finance").
        kwargs: Any additional parameters to include.

    Returns:
        A dictionary containing the base parameters plus any extras,
        excluding any parameters whose value is None.
    """
    params = {"engine": engine}
    params.update({k: v for k, v in kwargs.items() if v is not None})
    return params


def call_serpapi(context: ToolContext, params: dict) -> dict:
    """
    Execute a search query using the SerpAPI client and return the results as a dictionary.

    Args:
        context: The tool context containing required secrets.
        params: A dictionary of parameters for the SerpAPI search.

    Returns:
        The search results as a dictionary.
    """
    api_key = context.get_secret("SERP_API_KEY")
    client = SerpClient(api_key=api_key)
    try:
        search = client.search(params)
        return cast(dict[str, Any], search.as_dict())
    except Exception as e:
        # SerpAPI error messages sometimes contain the API key, so we need to sanitize it
        sanitized_e = re.sub(r"(api_key=)[^ &]+", r"\1***", str(e))
        raise ToolExecutionError(
            message="Failed to fetch search results",
            developer_message=sanitized_e,
        )


# ------------------------------------------------------------------------------------------------
# Google general utils
# ------------------------------------------------------------------------------------------------
def default_language_code(default_service_language_code: Optional[str] = None) -> Optional[str]:
    if isinstance(default_service_language_code, str):
        return default_service_language_code.lower()
    elif isinstance(DEFAULT_GOOGLE_LANGUAGE, str):
        return DEFAULT_GOOGLE_LANGUAGE.lower()
    return None


def default_country_code(default_service_country_code: Optional[str] = None) -> Optional[str]:
    if isinstance(default_service_country_code, str):
        return default_service_country_code.lower()
    elif isinstance(DEFAULT_GOOGLE_COUNTRY, str):
        return DEFAULT_GOOGLE_COUNTRY.lower()
    return None


def resolve_language_code(
    language_code: Optional[str] = None,
    default_service_language_code: Optional[str] = None,
) -> Optional[str]:
    language_code = language_code or default_language_code(default_service_language_code)

    if isinstance(language_code, str):
        language_code = language_code.lower()
        if language_code not in LANGUAGE_CODES:
            raise LanguageNotFoundError(language_code)

    return language_code


def resolve_country_code(
    country_code: Optional[str] = None,
    default_service_country_code: Optional[str] = None,
) -> Optional[str]:
    country_code = country_code or default_country_code(default_service_country_code)

    if isinstance(country_code, str):
        country_code = country_code.lower()
        if country_code not in COUNTRY_CODES:
            raise CountryNotFoundError(country_code)

    return country_code


# ------------------------------------------------------------------------------------------------
# Google Maps utils
# ------------------------------------------------------------------------------------------------
def get_google_maps_directions(
    context: ToolContext,
    origin_address: Optional[str] = None,
    destination_address: Optional[str] = None,
    origin_latitude: Optional[str] = None,
    origin_longitude: Optional[str] = None,
    destination_latitude: Optional[str] = None,
    destination_longitude: Optional[str] = None,
    language: str = DEFAULT_GOOGLE_MAPS_LANGUAGE,
    country: Optional[str] = DEFAULT_GOOGLE_MAPS_COUNTRY,
    distance_unit: GoogleMapsDistanceUnit = DEFAULT_GOOGLE_MAPS_DISTANCE_UNIT,
    travel_mode: GoogleMapsTravelMode = DEFAULT_GOOGLE_MAPS_TRAVEL_MODE,
) -> list[dict[str, Any]]:
    """Get directions from Google Maps.

    Provide either all(origin_address, destination_address) or
    all(origin_latitude, origin_longitude, destination_latitude, destination_longitude).

    Args:
        context: Tool context containing required Serp API Key secret.
        origin_address: Origin address.
        destination_address: Destination address.
        origin_latitude: Origin latitude.
        origin_longitude: Origin longitude.
        destination_latitude: Destination latitude.
        destination_longitude: Destination longitude.
        language: Language to use in the Google Maps search. Defaults to 'en' (English).
        country: 2-letter country code to use in the Google Maps search. Defaults to None
            (no country is specified).
        distance_unit: Distance unit to use in the Google Maps search. Defaults to 'km'
            (kilometers).
        travel_mode: Travel mode to use in the Google Maps search. Defaults to 'best'
            (best mode).

    Returns:
        The directions from Google Maps.
    """
    language = language.lower()

    if language not in LANGUAGE_CODES:
        raise LanguageNotFoundError(language)

    params = prepare_params(
        engine="google_maps_directions",
        hl=language,
        distance_unit=distance_unit.to_api_value(),
        travel_mode=travel_mode.to_api_value(),
    )

    if any([
        origin_latitude,
        origin_longitude,
        destination_latitude,
        destination_longitude,
    ]) and any([origin_address, destination_address]):
        raise ValueError("Either coordinates or addresses must be provided, not both")

    elif all([origin_latitude, origin_longitude, destination_latitude, destination_longitude]):
        params["start_coords"] = f"{origin_latitude},{origin_longitude}"
        params["end_coords"] = f"{destination_latitude},{destination_longitude}"

    elif all([origin_address, destination_address]):
        params["start_addr"] = str(origin_address)
        params["end_addr"] = str(destination_address)

    else:
        raise ValueError("Either coordinates or addresses must be provided")

    if country:
        country = country.lower()
        if country not in COUNTRY_CODES:
            raise CountryNotFoundError(country)
        params["gl"] = country

    results = call_serpapi(context, params)

    directions = cast(list[dict[str, Any]], results.get("directions", []))

    for direction in directions:
        clean_google_maps_direction(direction)

        if "arrive_around" in direction:
            direction["arrive_around"] = enrich_google_maps_arrive_around(
                direction["arrive_around"]
            )

    return directions


def clean_google_maps_direction(direction: dict[str, Any]) -> None:
    for trip in direction.get("trips", []):
        with contextlib.suppress(KeyError):
            del trip["start_stop"]["data_id"]
            del trip["end_stop"]["data_id"]

        for detail in trip.get("details", []):
            with contextlib.suppress(KeyError):
                del detail["geo_photo"]
                del detail["gps_coordinates"]

        for stop in trip.get("stops", []):
            with contextlib.suppress(KeyError):
                del stop["data_id"]


def enrich_google_maps_arrive_around(timestamp: Optional[int]) -> dict[str, Any]:
    if not timestamp:
        return {}

    dt = datetime.fromtimestamp(timestamp, tz=ZoneInfo("UTC")).isoformat()
    return {"datetime": dt, "timestamp": timestamp}


# ------------------------------------------------------------------------------------------------
# Google Flights utils
# ------------------------------------------------------------------------------------------------
def parse_flight_results(results: dict[str, Any]) -> dict[str, Any]:
    """Parse the flight results from the Google Flights API

    Note: Best flights is not always returned from the API.
    """
    flight_data = {}
    flights = []

    if "best_flights" in results:
        flights.extend(results["best_flights"])
    if "other_flights" in results:
        flights.extend(results["other_flights"])
    if "price_insights" in results:
        flight_data["price_insights"] = results["price_insights"]

    flight_data["flights"] = flights

    return flight_data


# ------------------------------------------------------------------------------------------------
# Google News utils
# ------------------------------------------------------------------------------------------------
def extract_news_results(
    results: dict[str, Any], limit: Optional[int] = None
) -> list[dict[str, Any]]:
    news_results = []
    for result in results.get("news_results", []):
        news_results.append({
            "title": result.get("title"),
            "snippet": result.get("snippet"),
            "link": result.get("link"),
            "date": result.get("date"),
            "source": result.get("source", {}).get("name"),
        })

    if limit:
        return news_results[:limit]
    return news_results


# ------------------------------------------------------------------------------------------------
# Google News utils
# ------------------------------------------------------------------------------------------------
def extract_shopping_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": result.get("title"),
            "direct_link": result.get("link"),
            "google_link": result.get("product_link"),
            "source": result.get("source"),
            "price": result.get("price"),
            "product_rating": result.get("rating"),
            "product_reviews": result.get("reviews"),
            "store_rating": result.get("store_rating"),
            "store_reviews": result.get("store_reviews"),
            "delivery": result.get("delivery"),
        }
        for result in results
    ]

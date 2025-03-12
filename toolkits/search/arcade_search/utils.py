from typing import Any

import serpapi
from arcade.sdk import ToolContext
from arcade.sdk.errors import ToolExecutionError


# ------------------------------------------------------------------------------------------------
# General SerpAPI utils
# ------------------------------------------------------------------------------------------------
def prepare_params(engine: str, **kwargs: Any) -> dict:
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
    client = serpapi.Client(api_key=api_key)
    try:
        search = client.search(params)
        return search.as_dict()  # type: ignore[no-any-return]
    except Exception as e:
        error_message = str(e)
        if "api_key" in error_message:
            error_message = error_message.split("api_key")[0] + "api_key=***"
        raise ToolExecutionError(
            message="Failed to fetch search results",
            developer_message=error_message,
        )


# ------------------------------------------------------------------------------------------------
# Google Flights utils
# ------------------------------------------------------------------------------------------------
def parse_flight_results(results: dict[str, Any]) -> dict[str, Any]:
    """Parse the flight results from the Google Flights API"""
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

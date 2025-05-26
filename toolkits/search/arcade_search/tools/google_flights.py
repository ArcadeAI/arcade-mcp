from typing import Annotated, Any

from arcade.sdk import ToolContext, tool

from arcade_search.enums import GoogleFlightsMaxStops, GoogleFlightsSortBy, GoogleFlightsTravelClass
from arcade_search.utils import call_serpapi, parse_flight_results, prepare_params


@tool(requires_secrets=["SERP_API_KEY"])
async def search_departing_flights(
    context: ToolContext,
    departure_airport_code: Annotated[
        str, "The departure airport code. An uppercase 3-letter code"
    ],
    arrival_airport_code: Annotated[str, "The arrival airport code. An uppercase 3-letter code"],
    outbound_date: Annotated[str, "Flight outbound date in YYYY-MM-DD format"],
    return_date: Annotated[
        str | None,
        "Flight return date in YYYY-MM-DD format. Provide a return date if you want to "
        "get a departure token for a returning flight (for roundtrip flights). "
        "If you do not provide a return date, then the tool will return "
        "flight search results for a one-way flight.",
    ] = None,
    currency_code: Annotated[
        str | None, "Currency of the returned prices. Defaults to 'USD'"
    ] = "USD",
    travel_class: Annotated[
        GoogleFlightsTravelClass,
        "Travel class of the flight. Defaults to 'ECONOMY'",
    ] = GoogleFlightsTravelClass.ECONOMY,
    num_adults: Annotated[int | None, "Number of adult passengers. Defaults to 1"] = 1,
    num_children: Annotated[int | None, "Number of child passengers. Defaults to 0"] = 0,
    max_stops: Annotated[
        GoogleFlightsMaxStops,
        "Maximum number of stops (layovers) for the flight. Defaults to any number of stops",
    ] = GoogleFlightsMaxStops.ANY,
    sort_by: Annotated[
        GoogleFlightsSortBy,
        "The sorting order of the results. Defaults to TOP_FLIGHTS.",
    ] = GoogleFlightsSortBy.TOP_FLIGHTS,
) -> Annotated[dict[str, Any], "Flight search results from the Google Flights API"]:
    """Retrieve flight search results for a departing flight using Google Flights.

    If you provide a return date, the tool will return departure tokens for returning flights.
    You can then use the departure token to search for a returning flight.

    If you do not provide a return date, then the tool will return
    flight search results for a one-way flight.
    """
    # Prepare the request
    params = prepare_params(
        "google_flights",
        departure_id=departure_airport_code.upper(),
        arrival_id=arrival_airport_code.upper(),
        outbound_date=outbound_date,
        return_date=return_date,
        currency=currency_code,
        travel_class=travel_class.to_api_value(),
        adults=num_adults,
        children=num_children,
        stops=max_stops.to_api_value(),
        sort_by=sort_by.to_api_value(),
        type=1 if return_date else 2,  # 1 is roundtrip, 2 is one-way,
        deep_search=True,  # Same search depth of the Google Flights page in the browser
    )

    # Execute the request
    results = call_serpapi(context, params)

    # Parse the results
    flights = parse_flight_results(results)

    return flights


@tool(requires_secrets=["SERP_API_KEY"])
async def search_returning_flights(
    context: ToolContext,
    departure_token: Annotated[str, "The departure token for the flight"],
    departure_airport_code: Annotated[
        str, "The departure airport code. An uppercase 3-letter code"
    ],
    arrival_airport_code: Annotated[str, "The arrival airport code. An uppercase 3-letter code"],
    outbound_date: Annotated[str, "Flight outbound date in YYYY-MM-DD format"],
    return_date: Annotated[str, "Flight return date in YYYY-MM-DD format"],
    currency_code: Annotated[
        str | None, "Currency of the returned prices. Defaults to 'USD'"
    ] = "USD",
    travel_class: Annotated[
        GoogleFlightsTravelClass,
        "Travel class of the flight. Defaults to 'ECONOMY'",
    ] = GoogleFlightsTravelClass.ECONOMY,
    num_adults: Annotated[int | None, "Number of adult passengers. Defaults to 1"] = 1,
    num_children: Annotated[int | None, "Number of child passengers. Defaults to 0"] = 0,
    max_stops: Annotated[
        GoogleFlightsMaxStops,
        "Maximum number of stops (layovers) for the flight. Defaults to any number of stops",
    ] = GoogleFlightsMaxStops.ANY,
    sort_by: Annotated[
        GoogleFlightsSortBy,
        "The sorting order of the results. Defaults to TOP_FLIGHTS.",
    ] = GoogleFlightsSortBy.TOP_FLIGHTS,
) -> Annotated[dict[str, Any], "Flight search results from the Google Flights API"]:
    """Retrieve flight search results for a returning flight using Google Flights.

    This tool can only be used after calling search_departing_flights tool.
    You must provide the exact same parameters as your previous search_departing_flights
    tool call in addition to the departure_token of the flight. You can find the departure_token
    in the 'departure_token' field of the flight search results.
    """
    # Prepare the request
    params = prepare_params(
        "google_flights",
        departure_token=departure_token,
        departure_id=departure_airport_code.upper(),
        arrival_id=arrival_airport_code.upper(),
        outbound_date=outbound_date,
        return_date=return_date,
        currency=currency_code,
        travel_class=travel_class.to_api_value(),
        adults=num_adults,
        children=num_children,
        stops=max_stops.to_api_value(),
        sort_by=sort_by.to_api_value(),
    )

    # Execute the request
    results = call_serpapi(context, params)

    # Parse the results
    flights = parse_flight_results(results)

    return flights

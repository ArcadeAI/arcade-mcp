from typing import Annotated, Any

from arcade_tdk import ToolContext, tool

from arcade_search.enums import GoogleHotelsSortBy
from arcade_search.utils import call_serpapi, prepare_params


@tool(requires_secrets=["SERP_API_KEY"])
async def search_hotels(
    context: ToolContext,
    location: Annotated[str, "Location to search for hotels, e.g., a city name, a state, etc."],
    check_in_date: Annotated[str, "Check-in date in YYYY-MM-DD format"],
    check_out_date: Annotated[str, "Check-out date in YYYY-MM-DD format"],
    query: Annotated[
        str | None, "Anything that would be used in a regular Google Hotels search"
    ] = None,
    currency: Annotated[str | None, "Currency code for prices. Defaults to 'USD'"] = "USD",
    min_price: Annotated[int | None, "Minimum price per night. Defaults to no minimum"] = None,
    max_price: Annotated[int | None, "Maximum price per night. Defaults to no maximum"] = None,
    num_adults: Annotated[int | None, "Number of adults per room. Defaults to 2"] = 2,
    num_children: Annotated[int | None, "Number of children per room. Defaults to 0"] = 0,
    sort_by: Annotated[
        GoogleHotelsSortBy, "The sorting order of the results. Defaults to RELEVANCE"
    ] = GoogleHotelsSortBy.RELEVANCE,
    num_results: Annotated[
        int | None, "Maximum number of results to return. Defaults to 5. Max 20"
    ] = 5,
) -> Annotated[dict[str, Any], "Hotel search results from the Google Hotels API"]:
    """Retrieve hotel search results using the Google Hotels API."""
    # Prepare the request
    params = prepare_params(
        "google_hotels",
        q=f"{query}, {location}" if query else location,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        currency=currency,
        min_price=min_price,
        max_price=max_price,
        adults=num_adults,
        children=num_children,
        sort_by=sort_by.to_api_value(),
    )

    # Execute the request
    results = call_serpapi(context, params)

    # Parse the results
    properties = results.get("properties", [])[:num_results]

    # Remove unwanted fields from each property
    for hotel in properties:
        hotel.pop("images", None)
        hotel.pop("extracted_hotel_class", None)
        hotel.pop("reviews_breakdown", None)
        hotel.pop("serpapi_property_details_link", None)

    return {"properties": properties}

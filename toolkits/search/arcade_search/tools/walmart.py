from typing import Annotated, Any

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from arcade_tdk.tool import tool

from arcade_search.enums import WalmartSortBy
from arcade_search.utils import (
    call_serpapi,
    extract_walmart_product_details,
    extract_walmart_results,
    get_walmart_last_page_integer,
    prepare_params,
)


@tool(requires_secrets=["SERP_API_KEY"])
async def search_walmart_products(
    context: ToolContext,
    keywords: Annotated[str, "Keywords to search for. E.g. 'apple iphone' or 'samsung galaxy'"],
    sort_by: Annotated[
        WalmartSortBy,
        "Sort the results by the specified criteria. "
        f"Defaults to '{WalmartSortBy.RELEVANCE.value}'.",
    ] = WalmartSortBy.RELEVANCE,
    min_price: Annotated[
        float | None,
        "Minimum price to filter the results by. E.g. 100.00",
    ] = None,
    max_price: Annotated[
        float | None,
        "Maximum price to filter the results by. E.g. 100.00",
    ] = None,
    next_day_delivery: Annotated[
        bool,
        "Filters products that are eligible for next day delivery. "
        "Defaults to False (returns all products, regardless of delivery status).",
    ] = False,
    page: Annotated[
        int,
        "Page number to fetch. Defaults to 1 (first page of results). "
        "The maximum page value is 100.",
    ] = 1,
) -> Annotated[dict[str, Any], "List of Walmart products matching the search query."]:
    """Search Walmart products using SerpAPI."""
    if page > 100:
        raise ToolExecutionError(f"The maximum page value for Walmart search is 100, got {page}.")

    sort_by_value = sort_by.to_api_value()

    params = prepare_params(
        "walmart",
        query=keywords,
        sort=sort_by_value,
        # When the user selects a sorting option, we have to disable the relevance sorting
        # using the soft_sort parameter.
        soft_sort=not sort_by_value,
        min_price=min_price,
        max_price=max_price,
        nd_en=next_day_delivery,
        page=page,
        include_filters=False,
    )

    response = call_serpapi(context, params)

    return {
        "products": extract_walmart_results(response.get("organic_results", [])),
        "current_page": page,
        "last_available_page": get_walmart_last_page_integer(response),
    }


@tool(requires_secrets=["SERP_API_KEY"])
async def get_walmart_product_details(
    context: ToolContext,
    item_id: Annotated[
        str,
        "Item ID. E.g. '414600577'. This can be retrieved from the search results of the "
        f"{search_walmart_products.__tool_name__} tool.",
    ],
) -> Annotated[dict[str, Any], "Product details"]:
    """Get product details from Walmart."""
    params = prepare_params("walmart_product", product_id=item_id)
    response = call_serpapi(context, params)

    product_result = response.get("product_result")

    if not product_result:
        return {
            "product_details": None,
            "message": f"No product details found for item ID '{item_id}'.",
        }

    return {"product_details": extract_walmart_product_details(product_result)}

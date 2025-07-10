import re
from typing import Any, cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from serpapi import Client as SerpClient


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


def extract_walmart_results(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "item_id": result.get("us_item_id"),
            "title": result.get("title"),
            "description": result.get("description"),
            "rating": result.get("rating"),
            "reviews_count": result.get("reviews"),
            "seller": {
                "id": result.get("seller_id"),
                "name": result.get("seller_name"),
            },
            "price": {
                "value": result.get("primary_offer", {}).get("offer_price"),
                "currency": result.get("primary_offer", {}).get("offer_currency"),
            },
            "link": result.get("product_page_url"),
        }
        for result in results
    ]


def get_walmart_last_page_integer(results: dict[str, Any]) -> int:
    try:
        return int(list(results["pagination"]["other_pages"].keys())[-1])
    except (KeyError, IndexError, ValueError):
        return 1


def extract_walmart_product_details(product: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_id": product.get("us_item_id"),
        "product_type": product.get("product_type"),
        "title": product.get("title"),
        "description_html": product.get("short_description_html"),
        "rating": product.get("rating"),
        "reviews_count": product.get("reviews"),
        "seller": {
            "id": product.get("seller_id"),
            "name": product.get("seller_name"),
        },
        "manufacturer_name": product.get("manufacturer"),
        "price": {
            "value": product.get("price_map", {}).get("price"),
            "currency": product.get("price_map", {}).get("currency"),
            "previous_price": product.get("price_map", {}).get("was_price", {}).get("price"),
        },
        "link": product.get("product_page_url"),
        "variant_options": extract_walmart_variant_options(product.get("variant_swatches", [])),
    }


def extract_walmart_variant_options(variant_swatches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    variants = []

    for variant_swatch in variant_swatches:
        variant_name = variant_swatch.get("name")
        if not variant_name:
            continue

        options = []

        for selection in variant_swatch.get("available_selections", []):
            selection_name = selection.get("name")
            if selection_name and selection_name not in options:
                options.append(selection_name)

        variants.append({variant_name: options})

    return variants

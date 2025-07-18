import re
from typing import Any, cast

from arcade_tdk import ToolContext
from arcade_tdk.errors import ToolExecutionError
from serpapi import Client as SerpClient

from arcade_google_shopping.constants import (
    DEFAULT_GOOGLE_COUNTRY,
    DEFAULT_GOOGLE_LANGUAGE,
)
from arcade_google_shopping.exceptions import CountryNotFoundError, LanguageNotFoundError
from arcade_google_shopping.google_data import COUNTRY_CODES, LANGUAGE_CODES


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


def default_language_code(default_service_language_code: str | None = None) -> str | None:
    if isinstance(default_service_language_code, str):
        return default_service_language_code.lower()
    elif isinstance(DEFAULT_GOOGLE_LANGUAGE, str):
        return DEFAULT_GOOGLE_LANGUAGE.lower()
    return None


def default_country_code(default_service_country_code: str | None = None) -> str | None:
    if isinstance(default_service_country_code, str):
        return default_service_country_code.lower()
    elif isinstance(DEFAULT_GOOGLE_COUNTRY, str):
        return DEFAULT_GOOGLE_COUNTRY.lower()
    return None


def resolve_language_code(
    language_code: str | None = None,
    default_service_language_code: str | None = None,
) -> str | None:
    language_code = language_code or default_language_code(default_service_language_code)

    if isinstance(language_code, str):
        language_code = language_code.lower()
        if language_code not in LANGUAGE_CODES:
            raise LanguageNotFoundError(language_code)

    return language_code


def resolve_country_code(
    country_code: str | None = None,
    default_service_country_code: str | None = None,
) -> str | None:
    country_code = country_code or default_country_code(default_service_country_code)

    if isinstance(country_code, str):
        country_code = country_code.lower()
        if country_code not in COUNTRY_CODES:
            raise CountryNotFoundError(country_code)

    return country_code


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

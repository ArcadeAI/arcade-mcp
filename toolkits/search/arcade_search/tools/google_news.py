from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import ToolExecutionError

from arcade_search.constants import DEFAULT_GOOGLE_NEWS_COUNTRY, DEFAULT_GOOGLE_NEWS_LANGUAGE
from arcade_search.exceptions import CountryNotFoundError, LanguageNotFoundError
from arcade_search.google_data import COUNTRY_CODES, LANGUAGE_CODES
from arcade_search.utils import call_serpapi, extract_news_results, prepare_params


@tool(requires_secrets=["SERP_API_KEY"])
async def search_news_stories(
    context: ToolContext,
    keywords: Annotated[
        str,
        "Keywords to search for news articles. E.g. 'Apple launches new iPhone'.",
    ],
    country_code: Annotated[
        str | None,
        "2-character country code to search for news articles. E.g. 'us' (United States). "
        f"Defaults to '{DEFAULT_GOOGLE_NEWS_COUNTRY}'.",
    ] = None,
    language_code: Annotated[
        str,
        "2-character language code to search for news articles. E.g. 'en' (English). "
        f"Defaults to '{DEFAULT_GOOGLE_NEWS_LANGUAGE}'.",
    ] = DEFAULT_GOOGLE_NEWS_LANGUAGE,
    limit: Annotated[
        int | None,
        "Maximum number of news articles to return. Defaults to None "
        "(returns all results found by the API).",
    ] = None,
) -> Annotated[dict[str, list[dict[str, Any]]], "News results."]:
    """Search for news articles related to a given query."""
    if not keywords:
        raise ToolExecutionError("Keywords are required to search for news articles.")

    if country_code and country_code not in COUNTRY_CODES:
        raise CountryNotFoundError(country_code)

    if language_code not in LANGUAGE_CODES:
        raise LanguageNotFoundError(language_code)

    params = prepare_params("google_news", q=keywords, gl=country_code, hl=language_code)
    results = call_serpapi(context, params)
    return {"news_results": extract_news_results(results, limit=limit)}

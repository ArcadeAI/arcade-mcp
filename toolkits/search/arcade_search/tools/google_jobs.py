from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_search.constants import DEFAULT_GOOGLE_JOBS_LANGUAGE
from arcade_search.exceptions import LanguageNotFoundError
from arcade_search.google_data import LANGUAGE_CODES
from arcade_search.utils import call_serpapi, prepare_params


@tool(requires_secrets=["SERP_API_KEY"])
async def search_jobs(
    context: ToolContext,
    query: Annotated[
        str,
        "Search query. Provide a job title, company name, and/or any keywords in general "
        "representing what kind of jobs the user is looking for. E.g. 'software engineer' "
        "or 'data analyst at Apple'.",
    ],
    location: Annotated[
        str | None,
        "Location to search for jobs. E.g. 'United States' or 'New York, NY'. Defaults to None.",
    ] = None,
    language: Annotated[
        str,
        "2-character language code to use in the Google Jobs search. "
        f"E.g. 'en' for English. Defaults to '{DEFAULT_GOOGLE_JOBS_LANGUAGE}'.",
    ] = DEFAULT_GOOGLE_JOBS_LANGUAGE,
    limit: Annotated[
        int,
        "Maximum number of results to retrieve. Defaults to 10 (max supported by the API).",
    ] = 10,
    next_page_token: Annotated[
        str | None,
        "Next page token to paginate results. Defaults to None (start from the first page).",
    ] = None,
) -> Annotated[dict, "Google Jobs results"]:
    """Search Google Jobs using SerpAPI."""
    if language not in LANGUAGE_CODES:
        raise LanguageNotFoundError(language)

    params = prepare_params(
        engine="google_jobs",
        q=query,
        hl=language,
    )

    if location:
        params["location"] = location

    if next_page_token:
        params["next_page_token"] = next_page_token

    results = call_serpapi(context, params)
    jobs_results = results.get("jobs_results", [])

    try:
        next_page_token = results["serpapi_pagination"]["next_page_token"]
    except KeyError:
        next_page_token = None

    return {
        "jobs": jobs_results[:limit],
        "next_page_token": next_page_token,
    }

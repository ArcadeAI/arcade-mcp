from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.errors import ToolExecutionError

from arcade_search.constants import DEFAULT_YOUTUBE_SEARCH_COUNTRY, DEFAULT_YOUTUBE_SEARCH_LANGUAGE
from arcade_search.utils import (
    call_serpapi,
    default_country_code,
    default_language_code,
    extract_video_details,
    extract_video_results,
    prepare_params,
    resolve_country_code,
    resolve_language_code,
)


@tool(requires_secrets=["SERP_API_KEY"])
async def search_youtube_videos(
    context: ToolContext,
    keywords: Annotated[
        str,
        "The keywords to search for. E.g. 'Python tutorial'.",
    ],
    language_code: Annotated[
        str | None,
        "2-character language code to search for. E.g. 'en' for English. "
        f"Defaults to '{default_language_code(DEFAULT_YOUTUBE_SEARCH_LANGUAGE)}'.",
    ] = None,
    country_code: Annotated[
        str | None,
        "2-character country code to search for. E.g. 'us' for United States. "
        f"Defaults to '{default_country_code(DEFAULT_YOUTUBE_SEARCH_COUNTRY)}'.",
    ] = None,
    next_page_token: Annotated[
        str | None,
        "The next page token to use for pagination. "
        "Defaults to `None` (start from the first page).",
    ] = None,
) -> Annotated[dict[str, Any], "List of YouTube videos related to the query."]:
    """Search for YouTube videos related to the query."""
    language_code = resolve_language_code(language_code, DEFAULT_YOUTUBE_SEARCH_LANGUAGE)
    country_code = resolve_country_code(country_code, DEFAULT_YOUTUBE_SEARCH_COUNTRY)

    params = prepare_params(
        "youtube",
        search_query=keywords,
        hl=language_code,
        gl=country_code,
        sp=next_page_token,
    )
    results = call_serpapi(context, params)

    if results.get("error"):
        error_msg = cast(str, results.get("error"))
        raise ToolExecutionError(error_msg)

    return {
        "videos": extract_video_results(results),
        "next_page_token": results.get("serpapi_pagination", {}).get("next_page_token"),
    }


@tool(requires_secrets=["SERP_API_KEY"])
async def get_youtube_video_details(
    context: ToolContext,
    video_id: Annotated[
        str,
        "The ID of the YouTube video to get details about. E.g. 'dQw4w9WgXcQ'.",
    ],
    language_code: Annotated[
        str | None,
        "2-character language code to search for. E.g. 'en' for English. "
        f"Defaults to '{default_language_code(DEFAULT_YOUTUBE_SEARCH_LANGUAGE)}'.",
    ] = None,
    country_code: Annotated[
        str | None,
        "2-character country code to search for. E.g. 'us' for United States. "
        f"Defaults to '{default_country_code(DEFAULT_YOUTUBE_SEARCH_COUNTRY)}'.",
    ] = None,
) -> Annotated[dict[str, Any], "Details about a YouTube video."]:
    """Get details about a YouTube video."""
    language_code = resolve_language_code(language_code, DEFAULT_YOUTUBE_SEARCH_LANGUAGE)
    country_code = resolve_country_code(country_code, DEFAULT_YOUTUBE_SEARCH_COUNTRY)

    params = prepare_params(
        "youtube_video",
        v=video_id,
        hl=language_code,
        gl=country_code,
    )
    results = call_serpapi(context, params)

    if results.get("error"):
        error_msg = cast(str, results.get("error"))
        raise ToolExecutionError(error_msg)

    return {
        "video": extract_video_details(results),
    }

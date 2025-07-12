"""Popular Search Engine Tools - Specific implementations for top search engines."""

from enum import Enum
from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_search_engine.tools.search import TimeRange, search_with_bang


class TranslationEngine(str, Enum):
    """Available translation engines."""

    LINGVA = "lingva"
    LIBRETRANSLATE = "libretranslate"
    MOZHI = "mozhi"
    MYMEMORY = "mymemory"


class MastodonSearchType(str, Enum):
    """Mastodon search type options."""

    HASHTAGS = "hashtags"
    USERS = "users"


# Web Search Engines


@tool
async def google_search(
    context: ToolContext,
    query: Annotated[str, "The search query to execute on Google"],
    language: Annotated[str, "Language code for search results"] = "en",
    safe_search: Annotated[
        int, "Safe search level (0=off, 1=moderate, 2=strict)"
    ] = 1,
    time_range: Annotated[TimeRange | None, "Time range filter for results"] = None,
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Google search results"]:
    """
    Search using Google through SearXNG.
    Use when you specifically need results from Google's search engine.
    """
    result = await search_with_bang(
        context=context,
        query=query,
        bang="!g",
        language=language,
        safe_search=safe_search,
        page=page,
    )
    return result


@tool
async def duckduckgo_search(
    context: ToolContext,
    query: Annotated[str, "The search query to execute on DuckDuckGo"],
    language: Annotated[str, "Language code for search results"] = "en",
    safe_search: Annotated[
        int, "Safe search level (0=off, 1=moderate, 2=strict)"
    ] = 1,
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing DuckDuckGo search results"]:
    """
    Search using DuckDuckGo through SearXNG.
    Use when you need privacy-focused search results from DuckDuckGo.
    """
    return await search_with_bang(
        context=context,
        query=query,
        bang="!ddg",
        language=language,
        safe_search=safe_search,
        page=page,
    )


@tool
async def brave_search(
    context: ToolContext,
    query: Annotated[str, "The search query to execute on Brave"],
    language: Annotated[str, "Language code for search results"] = "en",
    safe_search: Annotated[
        int, "Safe search level (0=off, 1=moderate, 2=strict)"
    ] = 1,
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Brave search results"]:
    """
    Search using Brave through SearXNG.
    Use when you need independent privacy-focused search results from Brave.
    """
    return await search_with_bang(
        context=context,
        query=query,
        bang="!br",
        language=language,
        safe_search=safe_search,
        page=page,
    )


@tool
async def bing_search(
    context: ToolContext,
    query: Annotated[str, "The search query to execute on Bing"],
    language: Annotated[str, "Language code for search results"] = "en",
    safe_search: Annotated[
        int, "Safe search level (0=off, 1=moderate, 2=strict)"
    ] = 1,
    time_range: Annotated[TimeRange | None, "Time range filter for results"] = None,
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Bing search results"]:
    """
    Search using Bing through SearXNG.
    Use when you specifically need results from Microsoft's Bing search engine.
    """
    return await search_with_bang(
        context=context,
        query=query,
        bang="!bi",
        language=language,
        safe_search=safe_search,
        page=page,
    )


@tool
async def startpage_search(
    context: ToolContext,
    query: Annotated[str, "The search query to execute on Startpage"],
    language: Annotated[str, "Language code for search results"] = "en",
    safe_search: Annotated[
        int, "Safe search level (0=off, 1=moderate, 2=strict)"
    ] = 1,
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Startpage search results"]:
    """
    Search using Startpage through SearXNG.
    Use when you need private Google search results via Startpage proxy.
    """
    return await search_with_bang(
        context=context,
        query=query,
        bang="!sp",
        language=language,
        safe_search=safe_search,
        page=page,
    )


# Knowledge & Reference


@tool
async def wikipedia_search(
    context: ToolContext,
    query: Annotated[str, "The topic or article to search on Wikipedia"],
    language: Annotated[
        str, "Language code for Wikipedia (e.g., 'en', 'es', 'fr')"
    ] = "en",
) -> Annotated[str, "JSON string containing Wikipedia search results"]:
    """
    Search Wikipedia through SearXNG.
    Use when you need encyclopedic information or general knowledge about a topic.
    """
    return await search_with_bang(
        context=context, query=query, bang="!wp", language=language
    )


@tool
async def wiktionary_search(
    context: ToolContext,
    query: Annotated[str, "The word or phrase to look up in Wiktionary"],
    language: Annotated[str, "Language code for dictionary results"] = "en",
) -> Annotated[str, "JSON string containing Wiktionary search results"]:
    """
    Search Wiktionary for word definitions through SearXNG.
    Use when you need dictionary definitions, etymology, or linguistic information.
    """
    return await search_with_bang(
        context=context, query=query, bang="!wt", language=language
    )


@tool()
async def arxiv_search(
    context: ToolContext,
    query: Annotated[str, "The search query for scientific papers on arXiv"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing arXiv search results"]:
    """
    Search arXiv for scientific papers through SearXNG.
    Use when you need to find academic papers in physics, mathematics, computer science, and related fields.
    """
    return await search_with_bang(
        context=context, query=query, bang="!arx", page=page
    )


@tool
async def pubmed_search(
    context: ToolContext,
    query: Annotated[str, "The search query for medical/life science papers"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing PubMed search results"]:
    """
    Search PubMed for medical and life science papers through SearXNG.
    Use when you need to find biomedical literature and life science research papers.
    """
    return await search_with_bang(
        context=context, query=query, bang="!pubmed", page=page
    )


# Developer Tools


@tool
async def github_search(
    context: ToolContext,
    query: Annotated[
        str, "The search query for GitHub repositories, code, or issues"
    ],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing GitHub search results"]:
    """
    Search GitHub repositories through SearXNG.
    Use when you need to find code repositories, projects, or GitHub-hosted content.
    """
    return await search_with_bang(context=context, query=query, bang="!gh", page=page)


@tool
async def stackoverflow_search(
    context: ToolContext,
    query: Annotated[str, "The programming question or error to search"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Stack Overflow search results"]:
    """
    Search Stack Overflow for programming questions through SearXNG.
    Use when you need to find solutions to programming problems or technical Q&A.
    """
    return await search_with_bang(context=context, query=query, bang="!so", page=page)


@tool
async def npm_search(
    context: ToolContext,
    query: Annotated[str, "The npm package name or search keywords"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing npm package search results"]:
    """
    Search npm packages through SearXNG.
    Use when you need to find JavaScript/Node.js packages in the npm registry.
    """
    return await search_with_bang(
        context=context, query=query, bang="!npm", page=page
    )


@tool
async def pypi_search(
    context: ToolContext,
    query: Annotated[str, "The PyPI package name or search keywords"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing PyPI package search results"]:
    """
    Search PyPI packages through SearXNG.
    Use when you need to find Python packages in the Python Package Index.
    """
    return await search_with_bang(
        context=context, query=query, bang="!pypi", page=page
    )


# Media Search


@tool
async def youtube_search(
    context: ToolContext,
    query: Annotated[str, "The search query for YouTube videos"],
    safe_search: Annotated[
        int, "Safe search level (0=off, 1=moderate, 2=strict)"
    ] = 1,
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing YouTube video search results"]:
    """
    Search YouTube videos through SearXNG.
    Use when you need to find video content on YouTube.
    """
    return await search_with_bang(
        context=context, query=query, bang="!yt", safe_search=safe_search, page=page
    )


@tool
async def soundcloud_search(
    context: ToolContext,
    query: Annotated[str, "The search query for SoundCloud music/audio"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing SoundCloud search results"]:
    """
    Search SoundCloud for music through SearXNG.
    Use when you need to find music, podcasts, or audio content on SoundCloud.
    """
    return await search_with_bang(context=context, query=query, bang="!sc", page=page)


# Translation Services


@tool
async def translate_text(
    context: ToolContext,
    text: Annotated[str, "The text to translate"],
    target_language: Annotated[str, "Target language code (e.g., 'es', 'fr', 'de')"],
    source_language: Annotated[
        str, "Source language code or 'auto' for automatic detection"
    ] = "auto",
    engine: Annotated[
        TranslationEngine, "Translation engine to use"
    ] = TranslationEngine.LINGVA,
) -> Annotated[str, "JSON string containing translation results"]:
    """
    Translate text using various translation engines through SearXNG.
    Use when you need to translate text between different languages.
    """
    bang_map = {
        TranslationEngine.LINGVA: "!lv",
        TranslationEngine.LIBRETRANSLATE: "!lt",
        TranslationEngine.MOZHI: "!mz",
        TranslationEngine.MYMEMORY: "!tl",
    }

    bang = bang_map.get(engine, "!lv")
    query = f"{source_language}:{target_language} {text}"

    return await search_with_bang(context=context, query=query, bang=bang)


# Maps & Location


@tool
async def openstreetmap_search(
    context: ToolContext,
    query: Annotated[str, "Location, address, or place to search on OpenStreetMap"],
    language: Annotated[str, "Language code for results"] = "en",
) -> Annotated[str, "JSON string containing OpenStreetMap search results"]:
    """
    Search OpenStreetMap for locations through SearXNG.
    Use when you need to find geographic locations, addresses, or map data.
    """
    return await search_with_bang(
        context=context, query=query, bang="!osm", language=language
    )


# Social Media


@tool
async def reddit_search(
    context: ToolContext,
    query: Annotated[str, "The search query for Reddit posts and discussions"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Reddit search results"]:
    """
    Search Reddit through SearXNG.
    Use when you need to find Reddit posts, discussions, or community content.
    """
    return await search_with_bang(context=context, query=query, bang="!re", page=page)


@tool
async def mastodon_search(
    context: ToolContext,
    query: Annotated[str, "The search query for Mastodon content"],
    search_type: Annotated[
        MastodonSearchType, "Type of Mastodon content to search"
    ] = MastodonSearchType.HASHTAGS,
) -> Annotated[str, "JSON string containing Mastodon search results"]:
    """
    Search Mastodon through SearXNG.
    Use when you need to find Mastodon posts, hashtags, or user profiles.
    """
    bang = "!mah" if search_type == MastodonSearchType.HASHTAGS else "!mau"

    return await search_with_bang(context=context, query=query, bang=bang)


# File Sharing


@tool
async def piratebay_search(
    context: ToolContext,
    query: Annotated[str, "The search query for torrents"],
    page: Annotated[int, "Page number for pagination"] = 1,
) -> Annotated[str, "JSON string containing Pirate Bay torrent search results"]:
    """
    Search The Pirate Bay for torrents through SearXNG.
    Use when you need to find torrent files for content sharing.
    """
    return await search_with_bang(
        context=context, query=query, bang="!tpb", page=page
    )

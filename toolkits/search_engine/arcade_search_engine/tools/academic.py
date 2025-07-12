"""Research Assistant Tools - High-level research capabilities using SearXNG."""

import json
from datetime import datetime
from enum import Enum
from logging import getLogger
from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_search_engine.tools.popular_engines import (
    arxiv_search,
    google_search,
    pubmed_search,
    wikipedia_search,
)
from arcade_search_engine.tools.search import search

logger = getLogger(__name__)


class ResearchSource(str, Enum):
    """Available research paper sources."""

    ARXIV = "arxiv"
    PUBMED = "pubmed"
    GOOGLE_SCHOLAR = "google_scholar"


class TimePeriod(str, Enum):
    """Time period options for research trends."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class YearRange(str, Enum):
    """Year range options for filtering research papers."""

    THIS_YEAR = "this_year"
    LAST_TWO_YEARS = "last_two_years"
    LAST_FIVE_YEARS = "last_five_years"
    LAST_DECADE = "last_decade"
    SINCE_2020 = "since_2020"
    SINCE_2010 = "since_2010"
    SINCE_2000 = "since_2000"
    ALL_TIME = "all_time"


def get_year_range_tuple(year_range: YearRange) -> tuple[int, int] | None:
    """Convert YearRange enum to tuple of (start_year, end_year)."""
    current_year = datetime.now().year

    if year_range == YearRange.THIS_YEAR:
        return (current_year, current_year)
    elif year_range == YearRange.LAST_TWO_YEARS:
        return (current_year - 2, current_year)
    elif year_range == YearRange.LAST_FIVE_YEARS:
        return (current_year - 5, current_year)
    elif year_range == YearRange.LAST_DECADE:
        return (current_year - 10, current_year)
    elif year_range == YearRange.SINCE_2020:
        return (2020, current_year)
    elif year_range == YearRange.SINCE_2010:
        return (2010, current_year)
    elif year_range == YearRange.SINCE_2000:
        return (2000, current_year)
    elif year_range == YearRange.ALL_TIME:
        return None  # No year filter
    else:
        return None


@tool
async def research_papers(
    context: ToolContext,
    topic: Annotated[str, "Research topic or keywords to search for"],
    sources: Annotated[
        list[str], "List of sources to search (arxiv, pubmed, google_scholar)"
    ] = [
        ResearchSource.ARXIV,
        ResearchSource.PUBMED,
        ResearchSource.GOOGLE_SCHOLAR,
    ],
    max_results: Annotated[int, "Maximum number of results per source"] = 10,
    time_range: Annotated[
        str | None, "Time range filter (day, week, month, year)"
    ] = None,
) -> Annotated[
    str, "JSON string containing aggregated research papers from multiple sources"
]:
    """
    Search for academic papers across multiple scientific databases.
    Use when you need to find research papers on a specific topic from various sources.
    """
    results = {
        "query": topic,
        "timestamp": datetime.now().isoformat(),
        "sources": {},
        "total_results": 0,
    }

    # Search each source
    for source in sources:
        try:
            if source == ResearchSource.ARXIV:
                source_results = json.loads(await arxiv_search(context, topic))
            elif source == ResearchSource.PUBMED:
                source_results = json.loads(await pubmed_search(context, topic))
            elif source == ResearchSource.GOOGLE_SCHOLAR:
                # Use Google with scholar-specific query
                scholar_query = f'site:scholar.google.com OR "academic paper" OR "research paper" {topic}'
                source_results = json.loads(
                    await google_search(context, scholar_query, time_range=time_range)
                )
            else:
                continue

            # Process and limit results
            if "results" in source_results:
                limited_results = source_results["results"][:max_results]
                results["sources"][source] = {
                    "results": limited_results,
                    "count": len(limited_results),
                }
                results["total_results"] += len(limited_results)

        except Exception as e:
            logger.exception(f"Error searching {source}")
            results["sources"][source] = {"error": str(e), "count": 0}

    return json.dumps(results)


@tool(
    name="find_and_review_literature_online",
    desc="Conduct a comprehensive literature review on a research topic.\
         Use when you need a thorough overview including definitions, recent papers, and review articles.",
)
async def literature_review(
    context: ToolContext,
    topic: Annotated[str, "Research topic for literature review"],
    include_definitions: Annotated[
        bool, "Include Wikipedia definitions and overview"
    ] = True,
    include_recent_papers: Annotated[bool, "Include recent research papers"] = True,
    include_reviews: Annotated[bool, "Search specifically for review papers"] = True,
    year_range: Annotated[
        YearRange | None,
        "Year range to filter results (e.g., 'last_five_years', 'since_2020')",
    ] = YearRange.LAST_FIVE_YEARS,
) -> Annotated[
    str,
    "JSON string containing comprehensive literature review with definitions, papers, and reviews",
]:
    """
    Conduct a comprehensive literature review on a research topic.
    Use when you need a thorough overview including definitions, recent papers, and review articles.
    """
    review = {"topic": topic, "timestamp": datetime.now().isoformat(), "sections": {}}

    # Convert year range enum to tuple
    year_range_tuple = get_year_range_tuple(year_range) if year_range else None

    # Get definitions and overview from Wikipedia
    if include_definitions:
        try:
            wiki_results = json.loads(await wikipedia_search(context, topic))
            if wiki_results.get("results"):
                review["sections"]["overview"] = {
                    "source": "Wikipedia",
                    "content": wiki_results["results"][:3],  # Top 3 Wikipedia results
                }
        except Exception as e:
            logger.exception(f"Error searching Wikipedia for {topic}")
            review["sections"]["overview"] = {"error": str(e)}

    # Search for review papers
    if include_reviews:
        review_query = f'"{topic}" AND (review OR survey OR "systematic review" OR meta-analysis)'
        if year_range_tuple:
            review_query += f" AND year:{year_range_tuple[0]}..{year_range_tuple[1]}"

        try:
            review_papers = json.loads(
                await research_papers(
                    context,
                    review_query,
                    sources=[ResearchSource.ARXIV, ResearchSource.PUBMED],
                    max_results=5,
                )
            )
            review["sections"]["review_papers"] = review_papers
        except Exception as e:
            logger.exception(f"Error searching review papers for {topic}")
            review["sections"]["review_papers"] = {"error": str(e)}

    # Get recent papers
    if include_recent_papers:
        recent_query = topic
        if year_range_tuple:
            recent_query += f" year:{year_range_tuple[0]}..{year_range_tuple[1]}"
        else:
            # Default to last 2 years if no year range specified
            current_year = datetime.now().year
            recent_query += f" year:{current_year - 2}..{current_year}"

        try:
            recent_papers = json.loads(
                await research_papers(
                    context,
                    recent_query,
                    sources=[
                        ResearchSource.ARXIV,
                        ResearchSource.PUBMED,
                        ResearchSource.GOOGLE_SCHOLAR,
                    ],
                    max_results=10,
                )
            )
            review["sections"]["recent_papers"] = recent_papers
        except Exception as e:
            logger.exception(f"Error searching recent papers for {topic}")
            review["sections"]["recent_papers"] = {"error": str(e)}

    return json.dumps(review)


@tool
async def find_citations(
    context: ToolContext,
    paper_title: Annotated[str, "Title of the paper to find citations for"],
    author: Annotated[str | None, "Optional author name to refine search"] = None,
    year: Annotated[int | None, "Optional publication year"] = None,
) -> Annotated[
    str,
    "JSON string containing citation information and papers that cite the given paper",
]:
    """
    Find citations and references for a specific research paper.
    Use when you need to track citations or find papers that reference a particular work.
    """
    # Build search query
    query_parts = [f'"{paper_title}"']
    if author:
        query_parts.append(f'author:"{author}"')
    if year:
        query_parts.append(f"year:{year}")

    query = " ".join(query_parts)

    results = {
        "query_paper": {"title": paper_title, "author": author, "year": year},
        "citations": {},
    }

    # Search for the paper itself first
    try:
        paper_search = json.loads(
            await search(
                context,
                query=query + " citations",
                categories=["science"],
                engines=["google", "arxiv", "pubmed"],
            )
        )

        if "results" in paper_search:
            results["paper_info"] = paper_search["results"][:1]  # First result

        # Search for papers citing this one
        citing_query = f'"{paper_title}" cited by OR references "{paper_title}"'
        citing_papers = json.loads(
            await search(
                context,
                query=citing_query,
                categories=["science"],
                engines=["google", "arxiv"],
            )
        )

        if "results" in citing_papers:
            results["citations"]["citing_papers"] = citing_papers["results"][:10]
            results["citations"]["count"] = len(citing_papers["results"])

    except Exception as e:
        logger.exception(f"Error searching for citations for {paper_title}")
        results["error"] = str(e)

    return json.dumps(results)


@tool
async def research_trends(
    context: ToolContext,
    field: Annotated[str, "Research field or domain to analyze"],
    time_period: Annotated[TimePeriod, "Time period to analyze"] = TimePeriod.YEAR,
    include_conferences: Annotated[
        bool, "Include conference papers in analysis"
    ] = True,
    include_journals: Annotated[
        bool, "Include journal publications in analysis"
    ] = True,
) -> Annotated[
    str,
    "JSON string containing research trends analysis including hot topics and recent developments",
]:
    """
    Analyze current research trends in a specific field.
    Use when you need to understand emerging topics, hot areas, and recent developments in a research domain.
    """
    trends = {
        "field": field,
        "time_period": time_period.value,
        "timestamp": datetime.now().isoformat(),
        "trends": {},
    }

    # Search for trending topics
    trend_queries = [
        f'"{field}" "hot topics" OR "emerging trends" OR "recent advances"',
        f'"{field}" "state of the art" OR "survey" {datetime.now().year}',
        f'"{field}" "breakthrough" OR "novel approach" OR "significant progress"',
    ]

    if include_conferences:
        trend_queries.append(
            f'"{field}" conference proceedings {datetime.now().year}'
        )

    if include_journals:
        trend_queries.append(
            f'"{field}" "journal" "special issue" OR "call for papers"'
        )

    for i, query in enumerate(trend_queries):
        try:
            results = json.loads(
                await search(
                    context,
                    query=query,
                    categories=["science", "general"],
                    time_range=time_period.value,
                )
            )

            if "results" in results:
                trends["trends"][f"query_{i + 1}"] = {
                    "query": query,
                    "results": results["results"][:5],
                    "count": len(results["results"]),
                }
        except Exception as e:
            logger.exception(f"Error searching for trends in {field}")
            trends["trends"][f"query_{i + 1}"] = {"query": query, "error": str(e)}

    return json.dumps(trends)


@tool
async def find_datasets(
    context: ToolContext,
    topic: Annotated[str, "Research topic or domain to find datasets for"],
    data_type: Annotated[
        str | None, "Type of data (e.g., 'image', 'text', 'tabular', 'time series')"
    ] = None,
    include_benchmarks: Annotated[
        bool, "Include benchmark datasets in search"
    ] = True,
) -> Annotated[
    str, "JSON string containing available datasets and benchmarks for the topic"
]:
    """
    Find datasets and benchmarks related to a research topic.
    Use when you need to locate datasets for machine learning, research, or analysis.
    """
    datasets = {"topic": topic, "data_type": data_type, "results": {}}

    # Build search queries for different dataset sources
    base_query = f'"{topic}" dataset'
    if data_type:
        base_query += f' "{data_type}"'

    queries = {
        "general": base_query + " download OR available",
        "kaggle": f"site:kaggle.com {base_query}",
        "github": f"site:github.com {base_query} OR benchmark",
        "papers_with_code": f"site:paperswithcode.com {base_query}",
        "huggingface": f"site:huggingface.co {base_query}",
    }

    if include_benchmarks:
        queries["benchmarks"] = (
            f'"{topic}" benchmark evaluation metrics state-of-the-art'
        )

    # Search each source
    for source, query in queries.items():
        try:
            results = json.loads(
                await search(context, query=query, categories=["general", "it"])
            )

            if "results" in results:
                datasets["results"][source] = {
                    "query": query,
                    "datasets": results["results"][:5],
                    "count": len(results["results"]),
                }
        except Exception as e:
            logger.exception(f"Error searching for datasets for {topic}")
            datasets["results"][source] = {"query": query, "error": str(e)}

    return json.dumps(datasets)


@tool
async def find_code_implementations(
    context: ToolContext,
    paper_title: Annotated[
        str, "Title of the paper or algorithm to find implementations for"
    ],
    algorithm_name: Annotated[
        str | None, "Specific algorithm name if different from paper title"
    ] = None,
    language: Annotated[str, "Programming language preference"] = "python",
) -> Annotated[str, "JSON string containing code repositories and implementations"]:
    """
    Find code implementations for research papers or algorithms.
    Use when you need to find practical implementations of theoretical work or algorithms.
    """
    implementations = {
        "paper": paper_title,
        "algorithm": algorithm_name or paper_title,
        "language": language,
        "sources": {},
    }

    search_term = algorithm_name if algorithm_name else paper_title

    # Search different code repositories
    queries = {
        "github": f'site:github.com "{search_term}" implementation {language}',
        "papers_with_code": f'site:paperswithcode.com "{search_term}"',
        "gitlab": f'site:gitlab.com "{search_term}" {language}',
        "general": f'"{search_term}" code implementation {language} repository',
    }

    for source, query in queries.items():
        try:
            results = json.loads(
                await search(context, query=query, categories=["it", "general"])
            )

            if "results" in results:
                implementations["sources"][source] = results["results"][:5]
        except Exception as e:
            logger.exception(
                f"Error searching for code implementations for {paper_title}"
            )
            implementations["sources"][source] = {"error": str(e)}

    return json.dumps(implementations)

from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import Atlassian
from arcade.sdk.errors import ToolExecutionError

from arcade_confluence.client import ConfluenceClientV1


@tool(
    requires_auth=Atlassian(
        scopes=["search:confluence"],
    )
)
async def search_content(
    context: ToolContext,
    terms: Annotated[
        list[str] | None,
        "A list of single words to search for in content. "
        "For example, ['project', 'documentation']",
    ] = None,
    phrases: Annotated[
        list[str] | None,
        "A list of groups of words that match content containing all the words in any order. "
        "For example, ['software developer']",
    ] = None,
    enable_fuzzy: Annotated[
        bool,
        "Enable fuzzy matching to find similar terms (e.g. 'roam' will find 'foam'). "
        "Defaults to False",
    ] = False,
    limit: Annotated[int, "Maximum number of results to return (1-100). Defaults to 25"] = 25,
) -> Annotated[dict, "Search results containing content items matching the criteria"]:
    """Search for content in Confluence.

    At least one of `terms` or `phrases` must be provided.
    All terms and phrases are OR'd together.
    The search is performed across all content in the authenticated user's Confluence workspace.
    All search terms in Confluence are case insensitive.

    ALWAYS prefer providing multiple terms & phrases
    in a single call over calling this tool multiple times.
    """
    if not terms and not phrases:
        raise ToolExecutionError(message="At least one of `terms` or `phrases` must be provided")

    client = ConfluenceClientV1(context.get_auth_token_or_empty())
    cql = client.construct_cql(terms, phrases, enable_fuzzy)
    resp = await client.get("search", params={"cql": cql, "limit": max(1, min(limit, 100))})

    return client.transform_search_content_response(resp)

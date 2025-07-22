from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Microsoft
from msgraph_beta.generated.models.entity_type import EntityType
from msgraph_beta.generated.models.search_query import SearchQuery
from msgraph_beta.generated.models.search_request import SearchRequest
from msgraph_beta.generated.search.query.query_post_request_body import QueryPostRequestBody

from arcade_teams.client import get_client
from arcade_teams.serializers import serialize_chat_message_search_hit
from arcade_teams.utils import build_offset_pagination


@tool(requires_auth=Microsoft(scopes=["Chat.Read", "ChatMessage.Read", "ChannelMessage.Read.All"]))
async def search_messages(
    context: ToolContext,
    keywords: Annotated[str, "The keywords to match against messages' content."],
    limit: Annotated[
        int,
        "The maximum number of messages to return. Defaults to 50, max is 50.",
    ] = 50,
    offset: Annotated[int, "The offset to start from."] = 0,
) -> Annotated[dict, "The messages matching the search criteria."]:
    """Searches for messages across Microsoft Teams chats and channels."""
    limit = min(50, max(1, limit))
    client = get_client(context.get_auth_token_or_empty())

    request_body = QueryPostRequestBody(
        requests=[
            SearchRequest(
                entity_types=[EntityType.ChatMessage],
                query=SearchQuery(query_string=keywords),
                from_=offset,
                size=limit,
            )
        ]
    )

    response = await client.search.query.post(request_body)

    search_hits = response.value[0].hits_containers[0].hits  # type: ignore[index,union-attr]
    messages = [serialize_chat_message_search_hit(search_hit) for search_hit in search_hits]  # type: ignore[union-attr]
    more_results = bool(response.value[0].hits_containers[0].more_results_available)  # type: ignore[index,union-attr]
    pagination = build_offset_pagination(messages, limit, offset, more_results)

    return {
        "messages": messages,
        "count": len(messages),
        "pagination": pagination,
    }

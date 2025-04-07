from typing import Annotated, Any, Optional

import httpx
from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_hubspot.utils import remove_none_values


@tool(
    requires_auth=OAuth2(
        id="arcade-hubspot",
        scopes=["oauth", "crm.objects.companies.read"],
    ),
)
async def search_companies(
    context: ToolContext,
    query: Annotated[
        str, "The query to search for companies. E.g. 'Acme Inc' or 'company_name:Acme Inc'"
    ],
    limit: Annotated[
        int, "The maximum number of companies to return. Defaults to 10. Max is 100."
    ] = 10,
    next_page_token: Annotated[
        Optional[str],
        "The token to get the next page of results. "
        "Defaults to None (returns first page of results)",
    ] = None,
) -> Annotated[dict[str, Any], "The companies that match the query."]:
    """Search for companies in Hubspot."""
    print("auth token", context.auth.get_auth_token_or_empty())
    base_url = "https://api.hubapi.com/crm/v3/objects/companies"
    headers = {
        "Authorization": f"Bearer {context.auth.get_auth_token_or_empty()}",
        "Content-Type": "application/json",
    }

    params = remove_none_values({
        "query": query,
        "limit": limit,
        "after": next_page_token,
    })

    async with httpx.AsyncClient() as client:
        hubspot_response = await client.get(base_url, headers=headers, params=params)
        print("hubspot_response", hubspot_response.text)
        hubspot_response.raise_for_status()
        data = hubspot_response.json()
        next_page_token = data["paging"].get("next", {}).get("after")
        response = {"companies": data["results"]}
        if next_page_token:
            response["next_page_token"] = next_page_token
        return response

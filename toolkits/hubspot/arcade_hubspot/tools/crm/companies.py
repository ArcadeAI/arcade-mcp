from typing import Annotated, Any, Optional

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Hubspot

from arcade_hubspot.enums import HubspotObject
from arcade_hubspot.models import HubspotCrmClient


@tool(
    requires_auth=Hubspot(
        scopes=[
            "oauth",
            "crm.objects.companies.read",
            "crm.objects.contacts.read",
            "crm.objects.deals.read",
            "sales-email-read",
        ],
    ),
)
async def get_company_data_by_keywords(
    context: ToolContext,
    keywords: Annotated[
        str,
        "The keywords to search for companies. It will match against the company name, phone, "
        "and website.",
    ],
    limit: Annotated[
        int, "The maximum number of companies to return. Defaults to 10. Max is 10."
    ] = 10,
    next_page_token: Annotated[
        Optional[str],
        "The token to get the next page of results. "
        "Defaults to None (returns first page of results)",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "Retrieve company data with associated contacts, deals, calls, emails, "
    "meetings, notes, and tasks.",
]:
    """Retrieve company data with associated contacts, deals, calls, emails,
    meetings, notes, and tasks.

    This tool will return up to 10 items of each associated object (contacts, leads, etc).
    """
    limit = min(limit, 10)
    client = HubspotCrmClient(context.get_auth_token_or_empty())
    return await client.search_by_keywords(
        object_type=HubspotObject.COMPANY,
        keywords=keywords,
        limit=limit,
        next_page_token=next_page_token,
        associations=[
            HubspotObject.CALL,
            HubspotObject.CONTACT,
            HubspotObject.DEAL,
            HubspotObject.EMAIL,
            HubspotObject.MEETING,
            HubspotObject.NOTE,
            HubspotObject.TASK,
        ],
    )

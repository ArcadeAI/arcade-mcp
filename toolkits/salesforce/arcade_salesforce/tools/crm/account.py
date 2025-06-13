import asyncio
from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import ToolExecutionError

from arcade_salesforce.enums import SalesforceObject
from arcade_salesforce.models import SalesforceClient
from arcade_salesforce.utils import clean_account_data


# TODO: We only return up to 10 items of each related object (e.g. contacts). Need to implement
# separate tools for each related object, so that we can return more items, when needed.
@tool(
    requires_auth=OAuth2(
        id="salesforce",
        scopes=[
            "read_account",
            "read_contact",
            "read_lead",
            "read_note",
            "read_opportunity",
            "read_task",
        ],
    )
)
async def get_account_data_by_keywords(
    context: ToolContext,
    query: Annotated[
        str,
        "The query to search for accounts. MUST be longer than one character. It will match the "
        "keywords against all account fields, such as name, website, phone, address, etc. "
        "E.g. 'Acme'",
    ],
    # Note: Salesforce supports up to 200 results, but since we're enriching each account with
    # related objects, we limit to 10, so that the response is not too lengthy for LLMs.
    limit: Annotated[
        int,
        "The maximum number of accounts to return. Defaults to 10. Maximum allowed is 10.",
    ] = 10,
    page: Annotated[int, "The page number to return. Defaults to 1 (first page of results)."] = 1,
) -> Annotated[
    dict,
    "The accounts matching the query with related info: contacts, leads, notes, calls, "
    "opportunities, tasks, emails, and events (up to 10 items of each type)",
]:
    """Searches for accounts in Salesforce and returns them with related info: contacts, leads,
    notes, calls, opportunities, tasks, emails, and events (up to 10 items of each type).

    An account is an organization (such as a customer, supplier, or partner, though more commonly
    a customer). In some Salesforce account setups, an account can also represent a person.
    """
    if len(query) < 2:
        raise ToolExecutionError("The `query` argument must have two or more characters.")

    limit = min(limit, 10)

    client = SalesforceClient(context.get_auth_token_or_empty())

    params = {
        "q": query,
        "sobjects": [
            {
                "name": "Account",
                "fields": await client.get_object_fields(SalesforceObject.ACCOUNT),
            }
        ],
        "in": "ALL",
        "overallLimit": limit,
        "offset": (page - 1) * limit,
    }
    response = await client.post("parameterizedSearch", json_data=params)
    search_results = response["searchRecords"]

    accounts = await asyncio.gather(*[
        client.enrich_account(
            account_data=account,
            limit_per_association=10,
        )
        for account in search_results
    ])
    return {"accounts": [clean_account_data(account) for account in accounts]}


@tool(
    requires_auth=OAuth2(
        id="salesforce",
        scopes=[
            "read_account",
            "read_contact",
            "read_lead",
            "read_note",
            "read_opportunity",
            "read_task",
        ],
    )
)
async def get_account_data_by_id(
    context: ToolContext,
    account_id: Annotated[
        str,
        "The ID of the account to get data for.",
    ],
) -> Annotated[
    dict,
    "The account with related info: contacts, leads, notes, calls, opportunities, tasks, emails, "
    "and events (up to 10 items of each type)",
]:
    """Gets the account with related info: contacts, leads, notes, calls, opportunities, tasks,
    emails, and events (up to 10 items of each type).

    An account is an organization (such as a customer, supplier, or partner, though more commonly
    a customer). In some Salesforce account setups, an account can also represent a person.
    """
    client = SalesforceClient(context.get_auth_token_or_empty())

    account = await client.get_account(account_id)

    if not account:
        return {"account": None, "error": f"No account found with id '{account_id}'"}

    account = await client.enrich_account(account_data=account)
    account = clean_account_data(account)

    return {"account": account}

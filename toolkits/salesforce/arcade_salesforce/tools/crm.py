import asyncio
from typing import Annotated

from arcade.sdk import ToolContext, tool
from arcade.sdk.auth import OAuth2

from arcade_salesforce.enums import SalesforceObject
from arcade_salesforce.models import SalesforceClient
from arcade_salesforce.utils import clean_account_data


@tool(
    requires_auth=OAuth2(
        id="arcade-salesforce",
        scopes=["read_account"],
    )
)
async def search_accounts(
    context: ToolContext,
    query: Annotated[str, "The query to search for accounts. E.g. 'Acme'"],
    limit: Annotated[int, "The maximum number of accounts to return. Defaults to 10."] = 10,
    page: Annotated[int, "The page number to return. Defaults to 1 (first page of results)."] = 1,
) -> Annotated[dict, "The list of accounts that match the query"]:
    """Searches for accounts in Salesforce that match the query.

    An account is an organization or person involved with the business (such as a customer,
    competitor, or partner).
    """
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
    accounts = response["searchRecords"]
    return {
        "accounts": [
            clean_account_data(account_data)
            for account_data in await asyncio.gather(*[
                client.enrich_account(account_data=account) for account in accounts
            ])
        ]
    }

from typing import Annotated

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import OAuth2
from arcade_tdk.errors import ToolExecutionError

from arcade_salesforce.exceptions import SalesforceToolExecutionError
from arcade_salesforce.models import SalesforceClient


# TODO: Add support for referencing an account by keywords (name, website, etc). We can use the
# get_account_data_by_keywords tool to search for accounts. If more than one is returned, we can
# raise a RetryableToolError providing the matches for the user to choose.
@tool(
    requires_auth=OAuth2(
        id="salesforce",
        scopes=["write_contact"],
    )
)
async def create_contact(
    context: ToolContext,
    account_id: Annotated[str, "The ID of the account to create the contact for."],
    last_name: Annotated[str, "The last name of the contact."],
    first_name: Annotated[str | None, "The first name of the contact."] = None,
    email: Annotated[str | None, "The email of the contact."] = None,
    phone: Annotated[str | None, "The phone number of the contact."] = None,
    mobile_phone: Annotated[str | None, "The mobile phone number of the contact."] = None,
    title: Annotated[
        str | None,
        "The title of the contact. E.g. 'CEO', 'Sales Director', 'CTO', etc.",
    ] = None,
    department: Annotated[
        str | None,
        "The department of the contact. E.g. 'Marketing', 'Sales', 'IT', etc.",
    ] = None,
    description: Annotated[str | None, "The description of the contact."] = None,
) -> Annotated[
    dict,
    "The created contact.",
]:
    """Creates a contact in Salesforce."""
    if not last_name:
        raise ToolExecutionError("Last name is required by Salesforce to create a contact.")

    client = SalesforceClient(context.get_auth_token_or_empty())
    contact = await client.create_contact(
        account_id=account_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        mobile_phone=mobile_phone,
        title=title,
        department=department,
        description=description,
    )

    if not contact.get("success"):
        raise SalesforceToolExecutionError(
            message="Failed to create contact",
            errors=contact.get("errors", []),
        )

    return {"success": True, "contactId": contact.get("id")}

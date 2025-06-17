import logging
from typing import Any, cast

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build

from arcade_google_contacts.constants import DEFAULT_SEARCH_CONTACTS_LIMIT

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def build_people_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a People service object.
    """
    auth_token = auth_token or ""
    return build("people", "v1", credentials=Credentials(auth_token))


def search_contacts(service: Any, query: str, limit: int | None) -> list[dict[str, Any]]:
    """
    Search the user's contacts in Google Contacts.
    """
    response = (
        service.people()
        .searchContacts(
            query=query,
            pageSize=limit or DEFAULT_SEARCH_CONTACTS_LIMIT,
            readMask=",".join([
                "names",
                "nicknames",
                "emailAddresses",
                "phoneNumbers",
                "addresses",
                "organizations",
                "biographies",
                "urls",
                "userDefined",
            ]),
        )
        .execute()
    )

    return cast(list[dict[str, Any]], response.get("results", []))

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build


def build_docs_service(auth_token: str | None) -> Resource:  # type: ignore[no-any-unimported]
    """
    Build a Drive service object.
    """
    auth_token = auth_token or ""
    return build("docs", "v1", credentials=Credentials(auth_token))

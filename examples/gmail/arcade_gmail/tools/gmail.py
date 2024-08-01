import re

from base64 import urlsafe_b64decode
from arcade.core.schema import ToolContext
from arcade.sdk.auth import OAuth2
from bs4 import BeautifulSoup
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from typing import Annotated
from arcade.sdk import tool


@tool(
    requires_auth=OAuth2(
        authority="https://accounts.google.com",
        scope=["https://www.googleapis.com/auth/gmail.readonly"],
    )
)
async def get_emails(
    context: ToolContext,
    n_emails: Annotated[int, "Number of emails to read"] = 5,
) -> dict:
    """Read emails from a Gmail account and extract plain text content, removing any HTML."""

    # Call the Gmail API
    service = build("gmail", "v1", credentials=Credentials(context.authorization.token))

    # Request a list of all the messages
    result = service.users().messages().list(userId="me").execute()
    messages = result.get("messages")

    # If there are no messages, return an empty string
    if not messages:
        return ""

    emails = []

    for msg in messages[:n_emails]:
        txt = service.users().messages().get(userId="me", id=msg["id"]).execute()

        try:
            payload = txt["payload"]
            headers = payload["headers"]

            for d in headers:
                if d["name"] == "From":
                    from_ = d["value"]
                if d["name"] == "Date":
                    date = d["value"]
                if d["name"] == "Subject":
                    subject = d["value"]
                else:
                    subject = "No subject"

            data = None
            parts = payload.get("parts")
            if parts:
                part = parts[0]
                body = part.get("body")
                if body:
                    data = body.get("data")
                    if data:
                        data = urlsafe_b64decode(data).decode()

            email_details = {
                "from": from_,
                "date": date,
                "subject": subject,
                "body": clean_email_body(data) if data else "",
            }
            emails.append(email_details)

        except Exception as e:
            print(f"Error reading email {msg['id']}: {e}", "ERROR")
            continue

    return {"emails": emails}


def clean_email_body(body: str) -> str:
    """Remove HTML tags and non-sentence elements from email body text."""

    # Remove HTML tags using BeautifulSoup
    soup = BeautifulSoup(body, "html.parser")
    text = soup.get_text(separator=" ")

    # Remove any non-sentence elements (e.g., URLs, email addresses, etc.)
    text = re.sub(r"\S*@\S*\s?", "", text)  # Remove emails
    text = re.sub(r"http\S+", "", text)  # Remove URLs
    text = re.sub(r"[^.!?a-zA-Z0-9\s]", "", text)  # Remove non-sentence characters
    text = " ".join(text.split())  # Remove extra whitespace

    return text

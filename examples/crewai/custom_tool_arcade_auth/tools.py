import re
from base64 import urlsafe_b64decode
from typing import Any, Optional

from bs4 import BeautifulSoup
from crewai.tools import BaseTool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel, Field


class GmailWriteDraftToolInput(BaseModel):
    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email")
    recipient: str = Field(..., description="The recipient of the email")


class ListEmailsTool(BaseTool):
    """Tool to list emails for the authenticated Gmail user."""

    name: str = "list_emails_tool"
    description: str = "List emails for the authenticated Gmail user."
    access_token: str = Field(..., description="Gmail API access token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    n_emails: int = Field(default=15, description="Number of emails to list")

    def _run(self) -> dict:
        """ """
        service = build(
            "gmail",
            "v1",
            credentials=Credentials(self.access_token),
        )

        messages = service.users().messages().list(userId="me").execute().get("messages", [])
        if not messages:
            return {"emails": []}

        emails = []
        for msg in messages[: self.n_emails]:
            try:
                email_data = service.users().messages().get(userId="me", id=msg["id"]).execute()
                email_details = self.parse_email(email_data)
                if email_details:
                    emails.append(email_details)
            except Exception as e:
                print(f"Error reading email {msg['id']}: {e}")

        return {"emails": emails}

    def parse_email(self, email_data: dict[str, Any]) -> dict[str, Any]:
        """
        Parse email data and extract relevant information.

        Args:
            email_data (Dict[str, Any]): Raw email data from Gmail API.

        Returns:
            Optional[Dict[str, str]]: Parsed email details or None if parsing fails.
        """
        try:
            payload = email_data.get("payload", {})
            headers = {d["name"].lower(): d["value"] for d in payload.get("headers", [])}

            body_data = self._get_email_body(payload)

            return {
                "id": email_data.get("id", ""),
                "thread_id": email_data.get("threadId", ""),
                "from": headers.get("from", ""),
                "date": headers.get("date", ""),
                "subject": headers.get("subject", ""),
                "body": self._clean_email_body(body_data) if body_data else "",
            }
        except Exception as e:
            print(f"Error parsing email {email_data.get('id', 'unknown')}: {e}")
            return email_data

    def _get_email_body(self, payload: dict[str, Any]) -> Optional[str]:
        """
        Extract email body from payload.

        Args:
            payload (Dict[str, Any]): Email payload data.

        Returns:
            Optional[str]: Decoded email body or None if not found.
        """
        if "body" in payload and payload["body"].get("data"):
            return urlsafe_b64decode(payload["body"]["data"]).decode()

        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain" and "data" in part["body"]:
                return urlsafe_b64decode(part["body"]["data"]).decode()

        return None

    def _clean_email_body(self, body: str) -> str:
        """
        Remove HTML tags and clean up email body text while preserving most content.

        Args:
            body (str): The raw email body text.

        Returns:
            str: Cleaned email body text.
        """
        try:
            # Remove HTML tags using BeautifulSoup
            soup = BeautifulSoup(body, "html.parser")
            text = soup.get_text(separator=" ")

            # Clean up the text
            cleaned_text = self._clean_text(text)

            return cleaned_text.strip()
        except Exception as e:
            print(f"Error cleaning email body: {e}")
            return body

    def _clean_text(self, text: str) -> str:
        """
        Clean up the text while preserving most content.

        Args:
            text (str): The input text.

        Returns:
            str: Cleaned text.
        """
        text = re.sub(r"\n+", "\n", text)
        text = re.sub(r"\s+", " ", text)
        text = "\n".join(line.strip() for line in text.split("\n"))

        return text

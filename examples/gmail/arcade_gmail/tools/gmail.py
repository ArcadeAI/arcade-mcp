import os
import re

from base64 import urlsafe_b64decode
from bs4 import BeautifulSoup
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from typing import Dict, List, Annotated
from arcade.sdk.tool import tool


SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SECRET_FILE = "/Users/spartee/Dropbox/Arcade/gcp/credentials.json"


@tool
async def oauth_read_email(
    n_emails: Annotated[int, "Number of emails to read"] = 5,
) -> List[Dict[str, str]]:
    """Read emails from a Gmail account and extract plain text content, removing any HTML."""

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open("token.json", "w") as token:
                    token.write(creds.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)

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

    return emails


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


DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]


@tool
async def list_drive_files(
    n_files: Annotated[int, "Number of files to search"] = 5,
) -> list[str]:
    """List files from a Google Drive account and return their details."""

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                flow = InstalledAppFlow.from_client_secrets_file(
                    SECRET_FILE, DRIVE_SCOPES
                )
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open("token.json", "w") as token:
                    token.write(creds.to_json())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(SECRET_FILE, DRIVE_SCOPES)
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

    # Call the Drive v3 API
    service = build("drive", "v3", credentials=creds)

    # Request a list of all the files
    results = (
        service.files()
        .list(pageSize=n_files, fields="nextPageToken, files(id, name)")
        .execute()
    )
    items = results.get("files", [])

    if not items:
        print("No files found.")
    else:
        print("Files:")
        for item in items:
            print("{0} ({1})".format(item["name"], item["id"]))

    return items

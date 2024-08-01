import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from typing import Annotated
from arcade.sdk import tool

SECRET_FILE = "/Users/spartee/Dropbox/Arcade/gcp/credentials.json"
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]


@tool
async def list_drive_files(
    n_files: Annotated[int, "Number of files to search"] = 5,
) -> list[str]:
    """List files from a Google Drive account and return their details."""

    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    # TODO: use context.authorization.token like gmail.py
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

"""

This is a simple example of how to use Arcade with CrewAI.
The example authenticates into the user's Gmail account with Arcade.
It then uses a custom CrewAI tool, GmailWriteDraftTool, to write a draft email.

The example assumes the following:
1. You have an Arcade API key and have set the ARCADE_API_KEY environment variable.
2. You have an OpenAI API key and have set the OPENAI_API_KEY environment variable.
3. You have installed the necessary dependencies in the requirements.txt file: `pip install -r requirements.txt`

"""

import base64
import os
from email.mime.text import MIMEText
from textwrap import dedent

from arcadepy import Arcade
from crewai import Agent, Crew, Task
from crewai.llm import LLM
from crewai.tools import BaseTool
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from pydantic import BaseModel, Field


class GmailWriteDraftToolInput(BaseModel):
    """Input schema for the custom CrewAI tool GmailWriteDraftTool."""

    subject: str = Field(..., description="The subject of the email")
    body: str = Field(..., description="The body of the email")
    recipient: str = Field(..., description="The recipient of the email")


class GmailWriteDraftTool(BaseTool):
    """Custom CrewAI tool to write a draft email for the authenticated Gmail user."""

    name: str = "gmail_write_draft_tool"
    description: str = "Write a draft email for the authenticated Gmail user."
    auth_token: str = Field(..., description="Gmail API access token")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    args_schema: type[GmailWriteDraftToolInput] = GmailWriteDraftToolInput

    def _run(self, subject: str, body: str, recipient: str) -> str:
        """
        Compose a new email draft using the Gmail API.
        """
        # Set up the Gmail API client
        service = build(
            "gmail",
            "v1",
            credentials=Credentials(self.auth_token),
        )

        message = MIMEText(body)
        message["to"] = recipient
        message["subject"] = subject

        # Encode the message in base64
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Create the draft
        draft = {"message": {"raw": raw_message}}

        draft_message = service.users().drafts().create(userId="me", body=draft).execute()
        draft_id = draft_message["id"]
        draft_url = f"https://mail.google.com/mail/u/0/#drafts/{draft_id}"

        return f"Successfully created the draft email. You can view it at {draft_url}"


def authenticate(arcade_api_key: str, user_id: str, provider: str, scopes: list[str]):
    """
    Handles Spotify authentication using Arcade.
    Returns the access token if successful.
    """
    client = Arcade(api_key=arcade_api_key)

    auth_response = client.auth.start(
        user_id=user_id,
        provider=provider,
        scopes=scopes,
    )

    if auth_response.status != "completed":
        print(
            "Authorization required. Please complete authorization in your browser:",
            auth_response.url,
        )
        auth_response = client.auth.wait_for_completion(auth_response)

    return auth_response.context.token


def main_agent(llm, tools) -> Agent:
    """Creates the main Agent for CrewAI."""
    return Agent(
        role="Email Draft Writer",
        backstory=dedent("""
            You are an email draft writing expert. Your role is to understand user requirements and compose
            draft emails based on user input.
        """),
        goal=dedent("""
            Your goal is to analyze user requests and write draft emails that meet the user's needs
            using the available tools and provide them with the URL to the draft email that you created.
        """),
        tools=tools,
        allow_delegation=False,
        verbose=True,
        llm=llm,
    )


def create_task(agent):
    return Task(
        description=dedent("""
        # Task
        You are an email draft writing expert tasked with composing draft emails based on the user's requests.

        # Guidelines
        Your responses should be:
        - Clear and specific about the email content
        - Provide accurate and relevant information based on the user's request
        - Ensure the draft is useful and addresses the user's query effectively

        # User Request
        Compose a draft email based on this description: {user_request}
        """),
        expected_output="Draft email composed based on the user's request",
        agent=agent,
        tools=agent.tools,
    )


def main():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    arcade_api_key = os.getenv("ARCADE_API_KEY")
    if not openai_api_key or not arcade_api_key:
        print("Please set OPENAI_API_KEY and ARCADE_API_KEY environment variables")
        return

    print("Welcome to Email Reader!")

    user_id = "user@example.com"
    provider = "google"
    scopes = ["https://www.googleapis.com/auth/gmail.compose"]

    # Authenticate with Arcade
    auth_token = authenticate(
        arcade_api_key=arcade_api_key,
        user_id=user_id,
        provider=provider,
        scopes=scopes,
    )
    if not auth_token:
        print("Authentication failed")
        return

    # Get user input for email reading
    email_topic = input(
        "Describe the Subject, Body, and Recipient of the email that you want the agent to write\n>"
    )

    # Initialize the Gmail tool
    write_draft_tool = GmailWriteDraftTool(auth_token=auth_token)
    agent = main_agent(LLM(model="gpt-4o", api_key=openai_api_key), tools=[write_draft_tool])
    task = create_task(agent)

    # Initialize crew
    crew = Crew(agents=[agent], tasks=[task], verbose=True)

    # Execute crew with user input
    result = crew.kickoff(inputs={"user_request": email_topic})
    print(result)


if __name__ == "__main__":
    main()

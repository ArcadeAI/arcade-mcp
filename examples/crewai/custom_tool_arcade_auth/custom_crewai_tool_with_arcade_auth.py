import os
from textwrap import dedent

from arcadepy import Arcade
from crewai import Agent, Crew, Task
from crewai.llm import LLM
from tools import ListEmailsTool


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
        role="Inbox Reader",
        backstory=dedent("""
            You are an email reading expert. Your role is to understand user requirements and read
            their email inbox to provide the most relevant information.
        """),
        goal=dedent("""
            Your goal is to analyze user requests and read their email inbox to provide the most relevant
            and useful information using the available tools.
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
        You are an email reading expert tasked with reading the user's email inbox and answering any questions they have about it.

        # Guidelines
        Your responses should be:
        - Clear and specific about the email content
        - Provide accurate and relevant information based on the user's request
        - Ensure the information is useful and addresses the user's query effectively

        # User Request
        Read the user's email inbox and provide the most relevant information based on this description: {user_request}
        """),
        expected_output="Relevant information from the user's email inbox",
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
    scopes = ["https://www.googleapis.com/auth/gmail.readonly"]

    access_token = authenticate(
        arcade_api_key=arcade_api_key,
        user_id=user_id,
        provider=provider,
        scopes=scopes,
    )
    if not access_token:
        print("Authentication failed")
        return

    # Get user input for email reading
    email_topic = input("Ask your email inbox a question\n>")

    # Initialize the Gmail tool
    gmail_tool = ListEmailsTool(access_token=access_token)

    agent = main_agent(LLM(model="gpt-4o", api_key=openai_api_key), tools=[gmail_tool])
    task = create_task(agent)

    # Initialize crew
    crew = Crew(agents=[agent], tasks=[task], verbose=True)

    # Execute crew with user input
    crew.kickoff(inputs={"user_request": email_topic})


if __name__ == "__main__":
    main()

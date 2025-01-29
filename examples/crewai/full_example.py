import logging
import os
from datetime import datetime
from textwrap import dedent

from arcadepy import Arcade
from crewai import Agent, Crew, Process, Task
from crewai_arcade.manager import CrewAIToolManager
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Load environment variables and initialize clients
load_dotenv()
arcade_client = Arcade()
user_id = os.getenv("ARCADE_USER_ID")

# Initialize tool manager and get tools
manager = CrewAIToolManager(arcade_client, user_id)
tools = manager.get_tools(toolkits=["github", "slack", "google"])


def main_agent(llm: ChatOpenAI, tools: list[dict]) -> Agent:
    """
    Creates an Agent for handling PR reviews and calendar management.

    Args:
        llm: Language model instance
        tools: List of tools available to the agent

    Returns:
        Agent: Configured agent instance
    """
    return Agent(
        role="Workflow Coordinator",
        backstory=dedent("""
            You are the Code Review Coordinator. Your purpose is to handle multiple tasks including
            monitoring GitHub PRs, coordinating with team members through Slack, and managing
            calendar events efficiently.
        """),
        goal=dedent("""
            Your objectives are to:
            1. Identify open PRs and ensure proper communication through Slack
            2. Create and manage calendar events while handling time zones appropriately
        """),
        allow_delegation=True,
        verbose=True,
        llm=llm,
    )


def workflow_tasks(agent: Agent) -> list[Task]:
    """
    Creates workflow tasks for PR review, calendar management, and notifications.

    Args:
        agent: The agent responsible for executing tasks

    Returns:
        List[Task]: List of configured tasks
    """
    pr_check_task = Task(
        description=dedent("""
            # Task: PR Review Check
            Check for open pull requests in the organization {repository_organization} and repository {repository_name}.

            # Process
            1. Use GitHub tools to search for open PRs, Github_ListPullRequests
            2. Return the PR details if found

            # Expected Format
            - PR check results including PR number, title, and URL

            # User Request
            {user_request}
        """),
        expected_output="A detailed report of found PRs with their details.",
        agent=agent,
        tools=tools,
    )

    calendar_task = Task(
        description=dedent("""
            # Task: Schedule Review Call
            Create a calendar event for the PR review.

            # Process
            1. Use Google Calendar tools to create a 30-minute review event with {reviewer_email}
            2. Include PR details in the event description

            # Expected Format
            - Confirmation of calendar event creation with details
            - Event time, duration, and description

            # Context
            - Today is {today_date}

            # User Request
            {user_request}
        """),
        expected_output="Confirmation of calendar event creation with all relevant details.",
        agent=agent,
        tools=tools,
    )

    notification_task = Task(
        description=dedent("""
            # Task: Slack Notification
            Notify relevant team members about the PR and scheduled review.

            # Process
            1. Use Slack tools to send a notification with the following structure:
               - If sending to a user: Use "Slack.SendDmToUser" with the username

            # Parameters
            - Target: {reviewer_slack_username} (can be username or channel)
            - User Request: {user_request}
        """),
        expected_output=dedent("""
            Confirmation of Slack notification sent including:
            1. Whether sent to user or channel
            2. Message content summary
            3. Delivery status
        """),
        agent=agent,
        tools=tools,
    )

    return [pr_check_task, calendar_task, notification_task]


def main() -> None:
    """Main function to execute the workflow."""
    logger.info("Starting the workflow.")

    # Initialize agent with GPT-4
    agent = main_agent(ChatOpenAI(model_name="gpt-4o"), tools=tools)
    tasks = workflow_tasks(agent)

    # Configure and create crew
    crew = Crew(
        agents=[agent],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    # Define workflow inputs
    inputs = {
        "repository_organization": "",
        "repository_name": "",
        "reviewer_email": "",
        "reviewer_slack_username": "",
        "today_date": datetime.now().strftime("%Y-%m-%d"),
        "user_request": "Check for any open PRs, schedule a review meeting for tomorrow at 10:00 PM - 11:00 PM argentina timezone, and notify by Slack to the user",
    }

    # Execute workflow
    result = crew.kickoff(inputs=inputs)
    logger.info(f"Workflow executed: {result}")


if __name__ == "__main__":
    main()

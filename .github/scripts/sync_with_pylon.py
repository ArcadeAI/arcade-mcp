#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx",
#     "PyGithub",
#     "markdown",
# ]
# ///
"""
GitHub Action script to sync GitHub issues and discussions with Pylon.
Creates Pylon issues for new GitHub issues/discussions and syncs updates.
"""

import json
import os
import re
from enum import Enum
from typing import Any, Optional

import httpx
import markdown
from github import Auth, Github
from github.Repository import Repository

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PYLON_API_TOKEN = os.getenv("PYLON_API_TOKEN")
PYLON_API_BASE = "https://api.usepylon.com"
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME")

# Headers for API requests
PYLON_HEADERS = {
    "Authorization": f"Bearer {PYLON_API_TOKEN}",
    "Content-Type": "application/json",
}

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def handle_http_response(response: httpx.Response) -> None:
    """Handle HTTP response with comprehensive error logging."""
    if response.status_code >= 400:
        print(f"HTTP Error {response.status_code}: {response.reason_phrase}")
        print(f"Response headers: {dict(response.headers)}")
        print(f"Response content: {response.text}")
        try:
            error_data = response.json()
            print(f"Error details: {json.dumps(error_data, indent=2)}")
        except (ValueError, TypeError):
            print("Could not parse error response as JSON")
    else:
        print(f"Success response: {response.json()}")

    response.raise_for_status()


class PylonIssueType(Enum):
    """Pylon issue types."""

    CONVERSATION = "Conversation"
    BUG = "Bug"
    QUESTION = "Question"
    FEATURE_REQUEST = "Feature Request"
    INCIDENT = "Incident"
    TASK = "Task"
    COMPLAINT = "Complaint"
    FEEDBACK = "Feedback"


class PylonIssueState(Enum):
    """Pylon issue states."""

    NEW = "new"
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    RESOLVED = "resolved"


class GitHubAction(Enum):
    """GitHub event actions."""

    # Issue actions
    OPENED = "opened"
    EDITED = "edited"
    REOPENED = "reopened"
    CLOSED = "closed"

    # Discussion actions
    CREATED = "created"
    ANSWERED = "answered"
    LOCKED = "locked"
    UNLOCKED = "unlocked"


class ExternalSource(Enum):
    """External source types for linking issues."""

    GITHUB = "github"
    SLACK = "slack"
    EMAIL = "email"
    WEB = "web"
    API = "api"


class ItemType(Enum):
    """GitHub item types for comment extraction."""

    ISSUE = "issue"
    DISCUSSION = "discussion"


class EventType(Enum):
    """GitHub event types for processing."""

    ISSUE = "issue"
    ISSUE_COMMENT = "issue_comment"
    DISCUSSION = "discussion"
    DISCUSSION_COMMENT = "discussion_comment"
    UNKNOWN = "unknown"


def load_github_event() -> dict[str, Any]:
    """Load the GitHub event payload."""
    with open(GITHUB_EVENT_PATH) as f:
        return json.load(f)


def is_pull_request_url(url: str) -> bool:
    """Check if a URL is for a pull request."""
    return "/pull/" in url if url else False


def extract_or_create_pylon_issue_id_from_body(
    repo: Repository,
    issue_number: int,
    item_type: ItemType = ItemType.ISSUE,
    title: Optional[str] = None,
    body: Optional[str] = None,
    external_url: Optional[str] = None,
    author: Optional[dict] = None,
    issue_type: Optional[PylonIssueType] = None,
) -> Optional[str]:
    """Extract Pylon issue ID from GitHub issue or discussion body, or create one if not found."""
    # Updated pattern to match the actual format: **Pylon Issue ID:** `uuid`
    pylon_id_pattern = r"\*\*Pylon Issue ID:\*\*\s*`([a-zA-Z0-9\-]+)`"

    # Get the issue or discussion body based on item type
    if item_type == ItemType.ISSUE:
        item = repo.get_issue(issue_number)
        current_body = item.body or ""
        current_title = item.title
        current_url = item.html_url
        current_author = item.user
    else:  # ItemType.DISCUSSION
        item = repo.get_discussion(issue_number)
        current_body = item.body or ""
        current_title = item.title
        current_url = item.html_url
        current_author = item.user

    # Use provided values or fall back to current item values
    search_body = body if body is not None else current_body
    item_title = title if title is not None else current_title
    item_url = external_url if external_url is not None else current_url
    item_author = author if author is not None else current_author

    # Search for Pylon issue ID in the body
    match = re.search(pylon_id_pattern, search_body)
    if match:
        return match.group(1)

    # If no Pylon issue ID found and we have the required parameters, create one
    if item_title and item_url and item_author:
        # Set default issue type based on item type
        if issue_type is None:
            issue_type = (
                PylonIssueType.BUG if item_type == ItemType.ISSUE else PylonIssueType.QUESTION
            )

        # Create external ID
        external_id = f"github-{item_type.value}-{issue_number}"

        # Extract requester information
        requester_email, requester_name = extract_requester_info(item_author)

        # Create Pylon issue
        pylon_issue = create_pylon_issue(
            title=item_title,
            body=search_body,
            external_id=external_id,
            external_url=item_url,
            requester_email=requester_email,
            requester_name=requester_name,
            issue_type=issue_type,
        )

        pylon_issue_id = pylon_issue["data"]["id"]
        pylon_issue_url = pylon_issue["data"]["link"]

        # Add Pylon info to GitHub issue/discussion body
        append_pylon_info_to_body(repo, issue_number, pylon_issue_id, pylon_issue_url, item_type)

        print(f"Created Pylon issue {pylon_issue_id} for GitHub {item_type.value} #{issue_number}")
        return pylon_issue_id

    return None


def extract_requester_info(author: dict[str, Any]) -> tuple[str, str]:
    """Extract requester email and name from GitHub author data."""
    requester_name = author["login"]  # GitHub username
    requester_email = author.get("email") or f"{author['login']}@users.noreply.github.com"
    return requester_email, requester_name


def create_pylon_issue(
    title: str,
    body: str,
    external_id: str,
    external_url: str,
    requester_email: str,
    requester_name: str,
    issue_type: PylonIssueType = PylonIssueType.CONVERSATION,
) -> dict[str, Any]:
    """Create a new Pylon issue."""
    url = f"{PYLON_API_BASE}/issues"

    # Convert GitHub markdown to HTML for Pylon
    body_html = convert_markdown_to_html(body)

    data = {
        "title": title,
        "body_html": body_html,
        "external_issues": [
            {
                "external_id": external_id,
                "source": ExternalSource.GITHUB.value,
                "link": external_url,
            }
        ],
        "type": issue_type.value,  # Configurable issue type
        "state": PylonIssueState.NEW.value,  # Initial state
        "requester_email": requester_email,
        "requester_name": requester_name,
    }

    print(f"Creating Pylon issue with data: {data} to url: {url}")

    with httpx.Client() as client:
        response = client.post(url, headers=PYLON_HEADERS, json=data)
        handle_http_response(response)
        return response.json()


def update_pylon_issue(issue_id: str, title: str, body: str) -> dict[str, Any]:
    """Update an existing Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}"

    # Convert GitHub markdown to HTML for Pylon
    body_html = convert_markdown_to_html(body)

    data = {"title": title, "body_html": body_html}

    with httpx.Client() as client:
        response = client.patch(url, headers=PYLON_HEADERS, json=data)
        handle_http_response(response)
        return response.json()


def close_pylon_issue(issue_id: str) -> dict[str, Any]:
    """Close a Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}"

    data = {"state": PylonIssueState.CLOSED.value}

    with httpx.Client() as client:
        response = client.patch(url, headers=PYLON_HEADERS, json=data)
        handle_http_response(response)
        return response.json()


def get_pylon_issue(issue_id: str) -> dict[str, Any]:
    """Get Pylon issue details to extract message_id."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}"

    with httpx.Client() as client:
        response = client.get(url, headers=PYLON_HEADERS)
        handle_http_response(response)
        return response.json()


def get_pylon_issue_threads(issue_id: str) -> dict[str, Any]:
    """Get Pylon issue threads to find internal thread_id."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}/threads"

    with httpx.Client() as client:
        response = client.get(url, headers=PYLON_HEADERS)
        handle_http_response(response)
        return response.json()


def create_pylon_thread(issue_id: str) -> dict[str, Any]:
    """Create a new thread for a Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}/threads"

    data = {
        "type": "internal",  # Assuming internal thread type
        "name": "GitHub Sync Thread",  # Default name for GitHub sync
    }

    print(f"Creating Pylon thread for issue {issue_id} with data: {data}")

    with httpx.Client() as client:
        response = client.post(url, headers=PYLON_HEADERS, json=data)
        handle_http_response(response)
        return response.json()


def post_pylon_note(
    issue_id: str, body_html: str, thread_id: str, message_id: str
) -> dict[str, Any]:
    """Post an internal note to a Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}/note"
    data = {"thread_id": thread_id, "body_html": body_html, "message_id": message_id}

    print(f"Posting internal note to Pylon with data: {data}")

    with httpx.Client() as client:
        response = client.post(url, headers=PYLON_HEADERS, json=data)
        handle_http_response(response)
        return response.json()


def get_pylon_issue_messages(issue_id: str) -> dict[str, Any]:
    """Get Pylon issue messages to find the latest message_id."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}/messages"

    with httpx.Client() as client:
        response = client.get(url, headers=PYLON_HEADERS)
        handle_http_response(response)
        return response.json()


def post_pylon_message(issue_id: str, content: str, author: dict[str, Any]) -> dict[str, Any]:
    """Post an internal note to a Pylon issue using GitHub author info."""
    # Get messages to find the actual message_id
    messages_data = get_pylon_issue_messages(issue_id)

    # Extract the latest message ID
    messages = messages_data.get("data", [])
    if not messages:
        print(f"Warning: No messages found for Pylon issue {issue_id}")
        return {}

    # Get the latest message (assuming they're ordered by creation time)
    latest_message = messages[-1]
    message_id = latest_message.get("id")

    if not message_id:
        print("Warning: Could not extract message_id from latest message")
        return {}

    # Get threads to find internal thread_id
    threads_data = get_pylon_issue_threads(issue_id)

    # Extract the first internal thread ID
    threads = threads_data.get("data", [])
    if not threads:
        print(f"No threads found for Pylon issue {issue_id}, creating one...")
        try:
            thread_response = create_pylon_thread(issue_id)
            thread_id = thread_response["data"]["id"]
            print(f"Created new thread {thread_id} for Pylon issue {issue_id}")
        except Exception as e:
            print(f"Error creating thread for Pylon issue {issue_id}: {e}")
            return {}
    else:
        # Find an internal thread (assuming they have a type field or similar)
        # For now, use the first thread
        thread_id = threads[0].get("id")
        if not thread_id:
            print("Warning: Could not extract thread_id from threads")
            return {}

    body_html = convert_markdown_to_html(content)
    return post_pylon_note(issue_id, body_html, thread_id, message_id)


def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert GitHub markdown to HTML for Pylon using the markdown library."""
    if not markdown_text:
        return ""

    # Configure markdown with GitHub-style extensions
    md = markdown.Markdown(
        extensions=[
            "markdown.extensions.tables",
            "markdown.extensions.fenced_code",
            "markdown.extensions.codehilite",
            "markdown.extensions.toc",
            "markdown.extensions.nl2br",  # Convert newlines to <br>
        ],
        extension_configs={"markdown.extensions.codehilite": {"css_class": "highlight"}},
    )

    return md.convert(markdown_text)


def append_pylon_info_to_body(
    repo: Repository,
    item_number: int,
    pylon_issue_id: str,
    pylon_issue_url: str,
    item_type: ItemType,
) -> None:
    """Append Pylon issue info to GitHub issue/discussion body."""
    pylon_info = f"""
<!---
> #### 🔗 Pylon Integration
>
> **Pylon Issue ID:** `{pylon_issue_id}`
> **Pylon Issue URL:** {pylon_issue_url}
>
> This {item_type.value} has been synced with Pylon for tracking and management. DO NOT REMOVE THIS COMMENT
-->
"""

    if item_type == ItemType.ISSUE:
        issue = repo.get_issue(item_number)
        current_body = issue.body or ""
        updated_body = current_body + pylon_info
        issue.edit(body=updated_body)
    else:  # ItemType.DISCUSSION
        discussion = repo.get_discussion(item_number)
        current_body = discussion.body or ""
        updated_body = current_body + pylon_info
        discussion.edit(body=updated_body)


def handle_github_issue_created(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub issue creation events."""
    issue = event["issue"]
    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_body = issue["body"] or ""
    issue_url = issue["html_url"]

    # Skip if this is actually a pull request
    if is_pull_request_url(issue_url):
        print(f"Skipping issue creation - URL is for a pull request: {issue_url}")
        return

    repo = g.get_repo(GITHUB_REPO)

    # Extract or create Pylon issue
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo,
        issue_number,
        ItemType.ISSUE,
        title=issue_title,
        body=issue_body,
        external_url=issue_url,
        author=issue["user"],
        issue_type=PylonIssueType.BUG,
    )

    if pylon_issue_id:
        print(
            f"Pylon issue {pylon_issue_id} exists or was created for GitHub issue #{issue_number}"
        )
    else:
        print(f"Could not create Pylon issue for GitHub issue #{issue_number}")


def handle_github_issue_updated(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub issue update events (edited, reopened)."""
    issue = event["issue"]
    action = event["action"]
    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_body = issue["body"] or ""
    issue_url = issue["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue exists
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(repo, issue_number, ItemType.ISSUE)

    if pylon_issue_id:
        # Update Pylon issue
        update_pylon_issue(pylon_issue_id, issue_title, issue_body)

        # Post update message
        message = f"""GitHub issue #{issue_number} has been {action}.

**Title:** {issue_title}
**URL:** {issue_url}"""

        post_pylon_message(pylon_issue_id, message, issue["user"])
        print(f"Updated Pylon issue {pylon_issue_id} for GitHub issue #{issue_number}")
    else:
        print(f"No Pylon issue found for GitHub issue #{issue_number}")


def handle_github_issue_closed(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub issue closure events."""
    issue = event["issue"]
    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_url = issue["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue exists
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(repo, issue_number, ItemType.ISSUE)

    if pylon_issue_id:
        # Close Pylon issue
        close_pylon_issue(pylon_issue_id)

        # Post closure message
        message = f"""GitHub issue #{issue_number} has been closed.

**Title:** {issue_title}
**URL:** {issue_url}"""

        post_pylon_message(pylon_issue_id, message, issue["user"])
        print(f"Closed Pylon issue {pylon_issue_id} for GitHub issue #{issue_number}")
    else:
        print(f"No Pylon issue found for GitHub issue #{issue_number}")


def handle_github_issue_comment(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub issue comment events."""
    comment = event["comment"]
    issue = event["issue"]
    issue_number = issue["number"]
    comment_body = comment["body"]
    comment_author = comment["user"]["login"]

    # Skip if this is actually a pull request
    if is_pull_request_url(issue["html_url"]):
        print(f"Skipping issue comment - URL is for a pull request: {issue['html_url']}")
        return

    repo = g.get_repo(GITHUB_REPO)

    # Extract or create Pylon issue
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo,
        issue_number,
        ItemType.ISSUE,
        title=issue["title"],
        body=issue["body"] or "",
        external_url=issue["html_url"],
        author=issue["user"],
        issue_type=PylonIssueType.BUG,
    )

    if pylon_issue_id:
        # Post comment to Pylon issue
        message = f"""New comment on GitHub issue #{issue_number} by @{comment_author}:

{comment_body}

"""

        post_pylon_message(pylon_issue_id, message, comment["user"])
        print(f"Posted comment to Pylon issue {pylon_issue_id} for GitHub issue #{issue_number}")
    else:
        print(f"Could not create or find Pylon issue for GitHub issue #{issue_number}")


def handle_github_issue(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub issue events - routes to specific handlers."""
    action = event["action"]

    if action == GitHubAction.OPENED.value:
        handle_github_issue_created(event, g)
    elif action == GitHubAction.CLOSED.value:
        handle_github_issue_closed(event, g)
    elif action in [GitHubAction.EDITED.value, GitHubAction.REOPENED.value]:
        handle_github_issue_updated(event, g)
    else:
        print(f"Unhandled issue action: {action}")


def handle_github_discussion_created(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion creation events."""
    discussion = event["discussion"]
    discussion_number = discussion["number"]
    discussion_title = discussion["title"]
    discussion_body = discussion["body"] or ""
    discussion_url = discussion["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Extract or create Pylon issue
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo,
        discussion_number,
        ItemType.DISCUSSION,
        title=discussion_title,
        body=discussion_body,
        external_url=discussion_url,
        author=discussion["user"],
        issue_type=PylonIssueType.QUESTION,
    )

    if pylon_issue_id:
        print(
            f"Pylon issue {pylon_issue_id} exists or was created for GitHub discussion #{discussion_number}"
        )
    else:
        print(f"Could not create Pylon issue for GitHub discussion #{discussion_number}")


def handle_github_discussion_updated(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion update events (edited)."""
    discussion = event["discussion"]
    action = event["action"]
    discussion_number = discussion["number"]
    discussion_title = discussion["title"]
    discussion_body = discussion["body"] or ""
    discussion_url = discussion["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue exists
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo, discussion_number, ItemType.DISCUSSION
    )

    if pylon_issue_id:
        # Update Pylon issue
        update_pylon_issue(pylon_issue_id, discussion_title, discussion_body)

        # Post update message
        message = f"""GitHub discussion #{discussion_number} has been {action}.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message, discussion["user"])
        print(f"Updated Pylon issue {pylon_issue_id} for GitHub discussion #{discussion_number}")
    else:
        print(f"No Pylon issue found for GitHub discussion #{discussion_number}")


def handle_github_discussion_answered(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion answered events."""
    discussion = event["discussion"]
    discussion_number = discussion["number"]
    discussion_title = discussion["title"]
    discussion_url = discussion["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue exists
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo, discussion_number, ItemType.DISCUSSION
    )

    if pylon_issue_id:
        # Close Pylon issue when discussion is answered
        close_pylon_issue(pylon_issue_id)

        # Post answered message
        message = f"""GitHub discussion #{discussion_number} has been answered.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message, discussion["user"])
        print(
            f"Closed Pylon issue {pylon_issue_id} for answered GitHub discussion #{discussion_number}"
        )
    else:
        print(f"No Pylon issue found for GitHub discussion #{discussion_number}")


def handle_github_discussion_locked(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion locked events."""
    discussion = event["discussion"]
    discussion_number = discussion["number"]
    discussion_title = discussion["title"]
    discussion_url = discussion["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue exists
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo, discussion_number, ItemType.DISCUSSION
    )

    if pylon_issue_id:
        # Close Pylon issue when discussion is locked
        close_pylon_issue(pylon_issue_id)

        # Post lock message
        message = f"""GitHub discussion #{discussion_number} has been locked.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message, discussion["user"])
        print(
            f"Closed Pylon issue {pylon_issue_id} for locked GitHub discussion #{discussion_number}"
        )
    else:
        print(f"No Pylon issue found for GitHub discussion #{discussion_number}")


def handle_github_discussion_unlocked(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion unlocked events."""
    discussion = event["discussion"]
    discussion_number = discussion["number"]
    discussion_title = discussion["title"]
    discussion_url = discussion["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue exists
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo, discussion_number, ItemType.DISCUSSION
    )

    if pylon_issue_id:
        # Note: Pylon doesn't have a direct "reopen" API, so we'll just post a message
        message = f"""GitHub discussion #{discussion_number} has been unlocked.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message, discussion["user"])
        print(
            f"Posted unlock message to Pylon issue {pylon_issue_id} for unlocked GitHub discussion #{discussion_number}"
        )
    else:
        print(f"No Pylon issue found for GitHub discussion #{discussion_number}")


def handle_github_discussion_comment(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion comment events."""
    comment = event["comment"]
    discussion = event["discussion"]
    discussion_number = discussion["number"]
    comment_body = comment["body"]
    comment_url = comment["html_url"]
    comment_author = comment["user"]["login"]

    repo = g.get_repo(GITHUB_REPO)

    # Extract or create Pylon issue
    pylon_issue_id = extract_or_create_pylon_issue_id_from_body(
        repo,
        discussion_number,
        ItemType.DISCUSSION,
        title=discussion["title"],
        body=discussion["body"] or "",
        external_url=discussion["html_url"],
        author=discussion["user"],
        issue_type=PylonIssueType.QUESTION,
    )

    if pylon_issue_id:
        # Post comment to Pylon issue
        message = f"""New comment on GitHub discussion #{discussion_number} by @{comment_author}:

{comment_body}

**Comment URL:** {comment_url}"""

        post_pylon_message(pylon_issue_id, message, comment["user"])
        print(
            f"Posted comment to Pylon issue {pylon_issue_id} for GitHub discussion #{discussion_number}"
        )
    else:
        print(f"Could not create or find Pylon issue for GitHub discussion #{discussion_number}")


def handle_github_discussion(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion events - routes to specific handlers."""
    action = event["action"]

    if action == GitHubAction.CREATED.value:
        handle_github_discussion_created(event, g)
    elif action == GitHubAction.ANSWERED.value:
        handle_github_discussion_answered(event, g)
    elif action == GitHubAction.LOCKED.value:
        handle_github_discussion_locked(event, g)
    elif action == GitHubAction.UNLOCKED.value:
        handle_github_discussion_unlocked(event, g)
    elif action == GitHubAction.EDITED.value:
        handle_github_discussion_updated(event, g)
    else:
        print(f"Unhandled discussion action: {action}")


def validate_environment() -> int:
    """Validate required environment variables."""
    required_vars = {
        "GITHUB_TOKEN": GITHUB_TOKEN,
        "PYLON_API_TOKEN": PYLON_API_TOKEN,
        "GITHUB_REPO": GITHUB_REPO,
        "GITHUB_EVENT_PATH": GITHUB_EVENT_PATH,
        "GITHUB_EVENT_NAME": GITHUB_EVENT_NAME,
    }

    missing_vars = [var for var, value in required_vars.items() if not value]

    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        return 1

    return 0


def determine_event_type(event: dict[str, Any]) -> EventType:
    """Determine the event type from the GitHub event payload."""
    if "issue" in event and "comment" in event:
        return EventType.ISSUE_COMMENT
    elif "discussion" in event and "comment" in event:
        return EventType.DISCUSSION_COMMENT
    elif "issue" in event:
        return EventType.ISSUE
    elif "discussion" in event:
        return EventType.DISCUSSION
    else:
        return EventType.UNKNOWN


def handle_event_by_type(event: dict[str, Any], event_type: EventType, g: Github) -> int:
    """Handle the GitHub event based on its type."""
    if event_type == EventType.ISSUE:
        handle_github_issue(event, g)
        print("Successfully synced issue with Pylon")
        return 0
    elif event_type == EventType.ISSUE_COMMENT:
        handle_github_issue_comment(event, g)
        print("Successfully synced issue comment with Pylon")
        return 0
    elif event_type == EventType.DISCUSSION:
        handle_github_discussion(event, g)
        print("Successfully synced discussion with Pylon")
        return 0
    elif event_type == EventType.DISCUSSION_COMMENT:
        handle_github_discussion_comment(event, g)
        print("Successfully synced discussion comment with Pylon")
        return 0
    else:
        print(f"Unsupported event type: {event_type.value}")
        return 1


def main():
    """Main function to handle GitHub events and sync with Pylon."""
    if validate_environment() != 0:
        return 1

    # Load GitHub event
    event = load_github_event()

    # Filter out pull requests - check if this is a pull request event
    if "pull_request" in event:
        print("Skipping pull request event - only processing issues and discussions")
        return 0

    g = Github(auth=Auth.Token(GITHUB_TOKEN))

    # Determine event type from the event payload
    event_type = determine_event_type(event)
    if event_type == EventType.UNKNOWN:
        print(f"Unsupported event type. Event keys: {list(event.keys())}")
        return 1

    # Handle the event based on its type
    return handle_event_by_type(event, event_type, g)


if __name__ == "__main__":
    exit(main())

#!/usr/bin/env python3
# /// script
# dependencies = [
#     "httpx",
#     "PyGithub",
# ]
# ///
"""
GitHub Action script to sync GitHub issues and discussions with Pylon.
Creates Pylon issues for new GitHub issues/discussions and syncs updates.
"""

import json
import os
import re
from typing import Any, Optional

import httpx
from github import Github
from github.Repository import Repository

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PYLON_API_TOKEN = os.getenv("PYLON_API_TOKEN")
PYLON_API_BASE = "https://api.usepylon.com"
GITHUB_REPO = os.getenv("GITHUB_REPOSITORY")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_EVENT_NAME = os.getenv("GITHUB_EVENT_NAME")

# Headers for API requests
PYLON_HEADERS = {"Authorization": f"Bearer {PYLON_API_TOKEN}", "Content-Type": "application/json"}

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}


def load_github_event() -> dict[str, Any]:
    """Load the GitHub event payload."""
    with open(GITHUB_EVENT_PATH) as f:
        return json.load(f)


def extract_pylon_issue_id_from_comments(comments) -> Optional[str]:
    """Extract Pylon issue ID from GitHub comments."""
    pylon_id_pattern = r"Pylon Issue ID:\s*([a-zA-Z0-9\-]+)"

    # PyGithub automatically handles pagination when iterating
    # This will iterate through all pages of comments
    for comment in comments:
        match = re.search(pylon_id_pattern, comment.body)
        if match:
            return match.group(1)
    return None


def create_pylon_issue(
    title: str, body: str, external_id: str, external_url: str
) -> dict[str, Any]:
    """Create a new Pylon issue."""
    url = f"{PYLON_API_BASE}/issues"

    # Convert GitHub markdown to HTML for Pylon
    body_html = convert_markdown_to_html(body)

    data = {
        "title": title,
        "body_html": body_html,
        "external_issues": [{"external_id": external_id, "source": "github", "link": external_url}],
    }

    with httpx.Client() as client:
        response = client.post(url, headers=PYLON_HEADERS, json=data)
        response.raise_for_status()
        return response.json()


def update_pylon_issue(issue_id: str, title: str, body: str) -> dict[str, Any]:
    """Update an existing Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}"

    # Convert GitHub markdown to HTML for Pylon
    body_html = convert_markdown_to_html(body)

    data = {"title": title, "body_html": body_html}

    with httpx.Client() as client:
        response = client.patch(url, headers=PYLON_HEADERS, json=data)
        response.raise_for_status()
        return response.json()


def close_pylon_issue(issue_id: str) -> dict[str, Any]:
    """Close a Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}"

    data = {"state": "closed"}

    with httpx.Client() as client:
        response = client.patch(url, headers=PYLON_HEADERS, json=data)
        response.raise_for_status()
        return response.json()


def post_pylon_message(issue_id: str, content: str) -> dict[str, Any]:
    """Post a message to a Pylon issue."""
    url = f"{PYLON_API_BASE}/issues/{issue_id}/messages"

    data = {"content": content}

    with httpx.Client() as client:
        response = client.post(url, headers=PYLON_HEADERS, json=data)
        response.raise_for_status()
        return response.json()


def convert_markdown_to_html(markdown: str) -> str:
    """Convert basic GitHub markdown to HTML for Pylon."""
    if not markdown:
        return ""

    # Basic markdown to HTML conversion
    html = markdown

    # Headers
    html = re.sub(r"^### (.*)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.*)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.*)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)

    # Bold and italic
    html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.*?)\*", r"<em>\1</em>", html)

    # Code blocks
    html = re.sub(r"```(.*?)```", r"<pre><code>\1</code></pre>", html, flags=re.DOTALL)
    html = re.sub(r"`(.*?)`", r"<code>\1</code>", html)

    # Links
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', html)

    # Line breaks
    html = html.replace("\n", "<br>\n")

    return html


def create_github_comment(
    repo: Repository, item_number: int, pylon_issue_id: str, pylon_issue_url: str, item_type: str
) -> None:
    """Create a comment on GitHub issue/discussion with Pylon issue details."""
    comment_body = f"""## 🔗 Pylon Issue Created

**Pylon Issue ID:** `{pylon_issue_id}`
**Pylon Issue URL:** {pylon_issue_url}

This {item_type} has been synced with Pylon for tracking and management.
"""

    if item_type == "issue":
        repo.get_issue(item_number).create_comment(comment_body)
    else:  # discussion
        repo.get_discussion(item_number).create_comment(comment_body)


def handle_github_issue(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub issue events."""
    issue = event["issue"]
    action = event["action"]
    issue_number = issue["number"]
    issue_title = issue["title"]
    issue_body = issue["body"] or ""
    issue_url = issue["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue already exists
    comments = repo.get_issue(issue_number).get_comments()
    pylon_issue_id = extract_pylon_issue_id_from_comments(comments)

    if action == "opened" and not pylon_issue_id:
        # Create new Pylon issue
        external_id = f"github-issue-{issue_number}"
        pylon_issue = create_pylon_issue(
            title=issue_title, body=issue_body, external_id=external_id, external_url=issue_url
        )

        pylon_issue_id = pylon_issue["data"]["id"]
        pylon_issue_url = pylon_issue["data"]["link"]

        # Add comment to GitHub issue
        create_github_comment(repo, issue_number, pylon_issue_id, pylon_issue_url, "issue")

        print(f"Created Pylon issue {pylon_issue_id} for GitHub issue #{issue_number}")

    elif action in ["edited", "reopened"] and pylon_issue_id:
        # Update Pylon issue
        update_pylon_issue(pylon_issue_id, issue_title, issue_body)

        # Post update message
        message = f"""GitHub issue #{issue_number} has been {action}.

**Title:** {issue_title}
**URL:** {issue_url}"""

        post_pylon_message(pylon_issue_id, message)
        print(f"Updated Pylon issue {pylon_issue_id} for GitHub issue #{issue_number}")

    elif action == "closed" and pylon_issue_id:
        # Close Pylon issue
        close_pylon_issue(pylon_issue_id)

        # Post closure message
        message = f"""GitHub issue #{issue_number} has been closed.

**Title:** {issue_title}
**URL:** {issue_url}"""

        post_pylon_message(pylon_issue_id, message)
        print(f"Closed Pylon issue {pylon_issue_id} for GitHub issue #{issue_number}")


def handle_github_discussion(event: dict[str, Any], g: Github) -> None:
    """Handle GitHub discussion events."""
    discussion = event["discussion"]
    action = event["action"]
    discussion_number = discussion["number"]
    discussion_title = discussion["title"]
    discussion_body = discussion["body"] or ""
    discussion_url = discussion["html_url"]

    repo = g.get_repo(GITHUB_REPO)

    # Check if Pylon issue already exists
    comments = repo.get_discussion(discussion_number).get_comments()
    pylon_issue_id = extract_pylon_issue_id_from_comments(comments)

    if action == "created" and not pylon_issue_id:
        # Create new Pylon issue
        external_id = f"github-discussion-{discussion_number}"
        pylon_issue = create_pylon_issue(
            title=discussion_title,
            body=discussion_body,
            external_id=external_id,
            external_url=discussion_url,
        )

        pylon_issue_id = pylon_issue["data"]["id"]
        pylon_issue_url = pylon_issue["data"]["link"]

        # Add comment to GitHub discussion
        create_github_comment(
            repo, discussion_number, pylon_issue_id, pylon_issue_url, "discussion"
        )

        print(f"Created Pylon issue {pylon_issue_id} for GitHub discussion #{discussion_number}")

    elif action in ["edited", "answered"] and pylon_issue_id:
        # Update Pylon issue
        update_pylon_issue(pylon_issue_id, discussion_title, discussion_body)

        # Post update message
        message = f"""GitHub discussion #{discussion_number} has been {action}.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message)
        print(f"Updated Pylon issue {pylon_issue_id} for GitHub discussion #{discussion_number}")

    elif action == "locked" and pylon_issue_id:
        # Close Pylon issue when discussion is locked
        close_pylon_issue(pylon_issue_id)

        # Post lock message
        message = f"""GitHub discussion #{discussion_number} has been locked.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message)
        print(
            f"Closed Pylon issue {pylon_issue_id} for locked GitHub discussion #{discussion_number}"
        )

    elif action == "unlocked" and pylon_issue_id:
        # Reopen Pylon issue when discussion is unlocked
        # Note: Pylon doesn't have a direct "reopen" API, so we'll just post a message
        message = f"""GitHub discussion #{discussion_number} has been unlocked.

**Title:** {discussion_title}
**URL:** {discussion_url}"""

        post_pylon_message(pylon_issue_id, message)
        print(
            f"Posted unlock message to Pylon issue {pylon_issue_id} for unlocked GitHub discussion #{discussion_number}"
        )


def main():
    """Main function to handle GitHub events and sync with Pylon."""
    if not GITHUB_TOKEN or not PYLON_API_TOKEN:
        print("Error: Missing required environment variables (GITHUB_TOKEN, PYLON_API_TOKEN)")
        return 1

    try:
        # Load GitHub event
        event = load_github_event()
        g = Github(GITHUB_TOKEN)

        # Determine event type from the event payload
        if "issue" in event:
            event_type = "issues"
        elif "discussion" in event:
            event_type = "discussion"
        else:
            print(f"Unsupported event type. Event keys: {list(event.keys())}")
            return 1

        # Handle different event types
        if event_type == "issues":
            handle_github_issue(event, g)
            print("Successfully synced with Pylon")
            return 0
        elif event_type == "discussion":
            handle_github_discussion(event, g)
            print("Successfully synced with Pylon")
            return 0
        else:
            print(f"Unsupported event type: {event_type}")
            return 1

    except Exception as e:
        print(f"Error syncing with Pylon: {e!s}")
        return 1


if __name__ == "__main__":
    exit(main())

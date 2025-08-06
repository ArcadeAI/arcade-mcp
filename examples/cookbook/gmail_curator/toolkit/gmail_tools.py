"""
Gmail Curator - Tools for organizing and managing Gmail inbox
"""

from datetime import datetime, timedelta

from arcade_tdk import tool
from arcade_tdk.auth import Google
from arcade_tdk.context import ToolContext
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.labels",
        ]
    )
)
async def analyze_inbox(days_back: int = 7, ctx: ToolContext = None) -> dict[str, any]:
    """
    Analyze Gmail inbox patterns from the last N days.

    Args:
        days_back: Number of days to analyze
        ctx: Tool context with auth token

    Returns:
        Analysis of email patterns including senders, subjects, and labels
    """
    # In production, this would use the real Google token
    token = ctx.get_auth_token_or_empty()

    # Mock response for development
    if token.startswith("mock-"):
        return {
            "total_emails": 156,
            "unread": 23,
            "top_senders": [
                {"email": "noreply@github.com", "count": 45},
                {"email": "updates@linkedin.com", "count": 12},
                {"email": "team@company.com", "count": 8},
            ],
            "categories": {
                "promotions": 67,
                "updates": 34,
                "forums": 23,
                "primary": 32,
            },
            "suggested_filters": [
                "GitHub notifications older than 3 days",
                "LinkedIn updates - batch into weekly digest",
                "Promotional emails with no interaction",
            ],
        }

    # Real implementation would use:
    # creds = Credentials(token=token)
    # service = build('gmail', 'v1', credentials=creds)
    # results = service.users().messages().list(userId='me').execute()

    return {"error": "Real Google token required"}


@tool(
    requires_auth=Google(
        scopes=[
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.labels",
        ]
    )
)
async def create_smart_labels(
    patterns: list[dict[str, str]], ctx: ToolContext = None
) -> dict[str, any]:
    """
    Create Gmail labels based on patterns.

    Args:
        patterns: List of patterns with 'name' and 'criteria'
        ctx: Tool context with auth token

    Returns:
        Created labels and applied message counts
    """
    token = ctx.get_auth_token_or_empty()

    if token.startswith("mock-"):
        created_labels = []
        for pattern in patterns:
            created_labels.append({
                "name": pattern.get("name", "Unknown"),
                "id": f"Label_{pattern.get('name', 'Unknown').replace(' ', '_')}",
                "messages_labeled": 0,  # Mock - would be actual count
            })

        return {"created_labels": created_labels, "total_messages_organized": 0}

    return {"error": "Real Google token required"}


@tool(requires_auth=Google(scopes=["https://www.googleapis.com/auth/gmail.readonly"]))
async def find_unsubscribe_candidates(
    min_emails: int = 5, no_interaction_days: int = 30, ctx: ToolContext = None
) -> list[dict[str, any]]:
    """
    Find email subscriptions that might be good to unsubscribe from.

    Args:
        min_emails: Minimum emails from sender to consider
        no_interaction_days: Days without interaction
        ctx: Tool context with auth token

    Returns:
        List of unsubscribe candidates with details
    """
    token = ctx.get_auth_token_or_empty()

    if token.startswith("mock-"):
        return [
            {
                "sender": "deals@retailer.com",
                "email_count": 47,
                "last_opened": "Never",
                "unsubscribe_link": "https://retailer.com/unsubscribe",
                "recommendation": "High - No engagement in 30+ days",
            },
            {
                "sender": "newsletter@techblog.com",
                "email_count": 12,
                "last_opened": "45 days ago",
                "unsubscribe_link": "https://techblog.com/preferences",
                "recommendation": "Medium - Occasional engagement",
            },
        ]

    return []


@tool
async def generate_filter_rules(
    email_analysis: dict[str, any],
) -> list[dict[str, any]]:
    """
    Generate Gmail filter rules based on email analysis.

    Args:
        email_analysis: Results from analyze_inbox

    Returns:
        Suggested filter rules
    """
    rules = []

    # Check top senders
    if "top_senders" in email_analysis:
        for sender in email_analysis["top_senders"]:
            if sender["count"] > 20:
                rules.append({
                    "criteria": f"from:{sender['email']}",
                    "action": "apply_label",
                    "label": f"Auto/{sender['email'].split('@')[1]}",
                    "reason": f"High volume sender ({sender['count']} emails)",
                })

    # Add rules for categories
    if email_analysis.get("categories", {}).get("promotions", 0) > 50:
        rules.append({
            "criteria": "category:promotions older_than:7d",
            "action": "archive",
            "reason": "Auto-archive old promotional emails",
        })

    return rules

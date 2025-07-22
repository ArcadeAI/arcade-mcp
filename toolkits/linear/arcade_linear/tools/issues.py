from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Linear

from arcade_linear.client import LinearClient
from arcade_linear.utils import clean_issue_data, parse_date_string


@tool(requires_auth=Linear(scopes=["read"]))
async def get_issue(
    context: ToolContext,
    issue_id: Annotated[
        str, "The Linear issue ID or identifier (e.g. 'FE-123', 'API-456') to retrieve."
    ],
    include_comments: Annotated[
        bool, "Whether to include comments in the response. Defaults to True."
    ] = True,
    include_attachments: Annotated[
        bool, "Whether to include attachments in the response. Defaults to True."
    ] = True,
    include_relations: Annotated[
        bool,
        "Whether to include issue relations (blocks, dependencies) in the response. "
        "Defaults to True.",
    ] = True,
    include_children: Annotated[
        bool, "Whether to include sub-issues in the response. Defaults to True."
    ] = True,
) -> Annotated[dict[str, Any], "Complete issue details with related data"]:
    """Get detailed information about a specific Linear issue

    This tool retrieves complete information about a single Linear issue when you have
    its specific ID or identifier. It's purely for reading and viewing data.

    What this tool provides:
    - Complete issue details (title, description, status, assignee, etc.)
    - Comments and discussion history (if requested)
    - File attachments (if requested)
    - Related issues and dependencies (if requested)
    - Sub-issues and hierarchical relationships (if requested)

    When to use this tool:
    - When you need to examine the full details of a specific issue
    - When you want to read issue content, comments, or relationships
    - When you need to analyze or compare issue information
    - When you have an issue ID and need to understand its current state

    When NOT to use this tool:
    - Do NOT use this if you need to change, modify, or update anything
    - Do NOT use this if you're trying to create new issues
    - Do NOT use this if you're searching for multiple issues

    This tool is READ-ONLY - it cannot make any changes to issues.
    """

    client = LinearClient(context.get_auth_token_or_empty())

    # Get issue data
    issue_data = await client.get_issue_by_id(issue_id)

    if not issue_data:
        return {"error": f"Issue not found: {issue_id}"}

    # Clean and format the issue data
    cleaned_issue = clean_issue_data(issue_data)

    # Optionally remove certain fields based on parameters
    if not include_comments:
        cleaned_issue.pop("comments", None)

    if not include_attachments:
        cleaned_issue.pop("attachments", None)

    if not include_relations:
        cleaned_issue.pop("relations", None)

    if not include_children:
        cleaned_issue.pop("children", None)

    # Get current timestamp for retrieval time
    current_time = parse_date_string("now")
    retrieved_at = current_time.isoformat() if current_time else None

    return {
        "issue": cleaned_issue,
        "retrieved_at": retrieved_at,
    }

import logging
from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_jira.client import APIType, JiraClient
from arcade_jira.utils import (
    clean_board_dict,
    create_board_result_dict,
    create_error_entry,
    validate_board_limit,
)

logger = logging.getLogger(__name__)


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:board-scope:jira-software",  # /board/{boardId}, /board
            "read:project:jira",  # project info included in /board responses
            "read:issue-details:jira",  # issue metadata in /board/{boardId}, /board responses
        ]
    )
)
async def get_boards(
    context: ToolContext,
    board_identifiers: Annotated[
        list[str] | None,
        "List of board names or IDs to retrieve. Can contain mixed board identifiers - "
        "both numeric IDs and board names. "
        "If not provided or empty, returns all boards with pagination.",
    ] = None,
    limit: Annotated[
        int,
        "The maximum number of boards to return. Must be between 1 and 100 inclusive. "
        "Controls pagination and determines how many boards are fetched and returned. "
        "Defaults to 50 for improved performance.",
    ] = 50,
    offset: Annotated[
        int,
        "The number of boards to skip before starting to return results. "
        "Used for pagination when you need to retrieve boards beyond the initial set. "
        "For example, offset=50 with limit=50 would return boards 51-100. "
        "Must be 0 or greater. Defaults to 0.",
    ] = 0,
) -> Annotated[
    dict[str, Any],
    "A comprehensive dictionary containing successfully resolved boards in a 'boards' list, "
    "with each board including metadata like ID, name, type, and location information. "
    "Any boards that couldn't be found are listed in an 'errors' array with detailed "
    "error messages. Includes pagination metadata. Duplicate boards are automatically "
    "deduplicated based on board ID.",
]:
    """
    Get Jira boards by their names or IDs, or list all boards with pagination.
    Returns successfully found boards and error details for any boards that couldn't be resolved.
    Automatically deduplicates boards if the same board is requested by both ID and name.
    """
    client = JiraClient(context.get_auth_token_or_empty(), client_type=APIType.AGILE)
    limit = validate_board_limit(limit)

    # If no specific boards requested, get all boards with pagination
    if not board_identifiers:
        return await _get_all_boards_paginated(client, limit, offset)

    # Process specific board identifiers with deduplication
    return await _get_boards_by_identifiers(client, board_identifiers)


async def _get_boards_by_identifiers(
    client: JiraClient,
    board_identifiers: list[str],
) -> dict[str, Any]:
    """
    Get boards by specific identifiers with deduplication logic.

    Args:
        client: JiraClient instance for API calls
        board_identifiers: List of board names or IDs to retrieve

    Returns:
        Dictionary containing deduplicated boards and any errors
    """
    results = {
        "boards": [],
        "errors": [],
    }

    # Track processed identifiers (both IDs and names) to prevent duplicates
    processed_identifiers = set()

    for board_identifier in board_identifiers:
        # Skip if we already processed this identifier or found this board
        if board_identifier in processed_identifiers:
            continue

        try:
            board_result = await _find_board_by_identifier(client, board_identifier)

            if board_result:
                # Add both the board ID and name to processed set to prevent future duplicates
                processed_identifiers.add(str(board_result["id"]))
                processed_identifiers.add(board_result["name"])
                results["boards"].append(board_result)
            else:
                # Board not found, add to errors
                error_entry = create_error_entry(
                    board_identifier,
                    f"Board '{board_identifier}' not found",
                )
                results["errors"].append(error_entry)

        except Exception as e:
            error_entry = create_error_entry(
                board_identifier,
                f"Unexpected error processing board '{board_identifier}': {e!s}",
            )
            results["errors"].append(error_entry)

    return results


async def _find_board_by_identifier(
    client: JiraClient,
    board_identifier: str,
) -> dict[str, Any] | None:
    """
    Find a board by either ID or name.

    Args:
        client: JiraClient instance for API calls
        board_identifier: Board ID or name to search for

    Returns:
        Cleaned board dictionary if found, None otherwise
    """
    # If identifier is numeric, try to get by ID first
    if board_identifier.isdigit():
        board_result = await _find_board_by_id(client, board_identifier)
        if board_result:
            return board_result
        # ID lookup failed, fall back to name lookup
        logger.warning(f"Board ID lookup failed for '{board_identifier}'. Attempting name lookup.")

    # Try by name (for non-numeric identifiers or failed ID lookup)
    return await _find_board_by_name(client, board_identifier)


async def _find_board_by_id(
    client: JiraClient,
    board_id: str,
) -> dict[str, Any] | None:
    """
    Find a board by its ID.

    Args:
        client: JiraClient instance for API calls
        board_id: Board ID to search for

    Returns:
        Cleaned board dictionary if found, None otherwise
    """
    try:
        board = await client.get(f"/board/{board_id}")
        board_result = clean_board_dict(board)
        board_result["found_by"] = "id"
        return board_result
    except Exception:
        return None
    else:
        logger.warning(f"Board ID lookup failed for '{board_id}'. API error.")
        return None


async def _find_board_by_name(
    client: JiraClient,
    board_name: str,
) -> dict[str, Any] | None:
    """
    Find a board by its name using Jira API name filter.

    Args:
        client: JiraClient instance for API calls
        board_name: Board name to search for

    Returns:
        Cleaned board dictionary if found, None otherwise
    """
    try:
        response = await client.get(
            "/board",
            params={
                "name": board_name,
                "startAt": 0,
                "maxResults": 1,
            },
        )

        boards = response.get("values", [])
        if boards:
            board_result = clean_board_dict(boards[0])
            board_result["found_by"] = "name"
            return board_result
    except Exception:
        logger.warning(f"Board name lookup failed for '{board_name}'. API error.")

    return None


async def _get_all_boards_paginated(
    client: JiraClient,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    """
    Get all boards with pagination using Jira API parameters.

    Args:
        client: JiraClient instance for API calls
        limit: Maximum number of boards to return
        offset: Number of boards to skip

    Returns:
        Dictionary containing boards and pagination metadata
    """
    response = await client.get(
        "/board",
        params={
            "startAt": offset,
            "maxResults": limit,
        },
    )

    boards = [clean_board_dict(board) for board in response.get("values", [])]

    return create_board_result_dict(
        boards,
        len(boards),
        response.get("isLast", False),
        offset,
        limit,
    )

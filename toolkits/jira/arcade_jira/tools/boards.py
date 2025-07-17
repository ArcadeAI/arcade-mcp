from typing import Annotated, Any

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian

from arcade_jira.client import JiraClient
from arcade_jira.utils import (
    clean_board_dict,
    create_board_error_message,
    create_board_result_dict,
    create_error_entry,
    find_board_by_name,
    validate_board_limit,
)


@tool(requires_auth=Atlassian(scopes=["read:board-scope:jira-software", "read:project:jira"]))
async def get_boards_by_ids_or_names(
    context: ToolContext,
    board_identifiers: Annotated[
        list[str],
        "List of board names or IDs to retrieve. Can contain mixed board identifiers - "
        "both numeric IDs (e.g., '123') and board names (e.g., 'My Scrum Board'). "
        "Board names are case-sensitive and must match exactly. If a board is not found, "
        "it will be included in the errors list with suggested alternatives. "
        "Example: ['123', 'My Board', '456', 'Another Board Name']",
    ],
) -> Annotated[
    dict[str, Any],
    "A comprehensive dictionary containing successfully resolved boards in a 'boards' list, "
    "with each board including metadata like ID, name, type, and location information. "
    "Any boards that couldn't be found are listed in an 'errors' array with detailed "
    "error messages and suggestions for available boards.",
]:
    """
    Resolve multiple Jira boards by their names or IDs.
    Returns successfully found boards and error details for any boards that couldn't be resolved.
    """
    client = JiraClient(context.get_auth_token_or_empty(), use_agile_api=True)

    results = {
        "boards": [],
        "errors": [],
    }

    # Get all available boards for name matching fallback
    available_boards_response = None

    for board_identifier in board_identifiers:
        try:
            # Try by ID first
            board_found_by_id = False
            try:
                board = await client.get(f"/board/{board_identifier}")
                board_result = clean_board_dict(board)
                board_result["found_by"] = "id"
                results["boards"].append(board_result)
                board_found_by_id = True
            except Exception:
                # Board ID lookup failed, will try by name instead
                board_found_by_id = False

            if board_found_by_id:
                continue

            # Try by name (list all boards and match)
            if available_boards_response is None:
                available_boards_response = await _list_all_boards_simple(
                    context, client, limit=100
                )

            boards = available_boards_response["boards"]
            found_board = find_board_by_name(boards, board_identifier)

            if found_board:
                board_result = clean_board_dict(found_board)
                board_result["found_by"] = "name"
                results["boards"].append(board_result)
                continue

            # If not found, add to errors with available boards
            available_boards = [clean_board_dict(b) for b in boards]
            error_message = create_board_error_message(board_identifier, available_boards)
            error_entry = create_error_entry(board_identifier, error_message)
            results["errors"].append(error_entry)

        except Exception as e:
            error_entry = create_error_entry(
                board_identifier,
                f"Unexpected error processing board '{board_identifier}': {e!s}",
            )
            results["errors"].append(error_entry)

    return results


@tool(requires_auth=Atlassian(scopes=["read:board-scope:jira-software", "read:project:jira"]))
async def list_all_boards(
    context: ToolContext,
    limit: Annotated[
        int,
        "The maximum number of boards to return. Must be between 1 and 100 inclusive. "
        "Controls pagination and determines how many boards are fetched and returned. "
        "Defaults to 50 for optimal performance.",
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
    "A dictionary containing a list of all boards available to the authenticated user, "
    "along with pagination metadata including total count, isLast flag, "
    "and current pagination parameters.",
]:
    """
    List all boards available to the user (paginated fetch).
    """
    client = JiraClient(context.get_auth_token_or_empty(), use_agile_api=True)
    return await _list_all_boards_simple(context, client, limit, offset)


# Private helper functions
async def _get_board_type_from_configuration(client: JiraClient, board_id: int) -> str | None:
    """
    Fetch the board configuration to get the accurate board type.
    """
    try:
        config = await client.get(f"/board/{board_id}/configuration")
    except Exception:
        return None
    else:
        # Extract board type from configuration response
        t = config.get("type")
        if isinstance(t, dict):
            return t.get("type")
        return t


async def _list_all_boards_simple(
    context: ToolContext,
    client: JiraClient,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Simple helper to list all boards without sprint checking.
    """
    boards = []
    start_at = offset
    max_results = validate_board_limit(limit)

    while len(boards) < max_results:
        resp = await client.get(
            "/board",
            params={"startAt": start_at, "maxResults": max_results},
        )
        batch = resp.get("values", [])
        boards.extend(batch)

        if resp.get("isLast") or len(batch) >= max_results:
            break
        start_at += max_results

    # Limit to requested number
    boards = boards[:limit]

    return create_board_result_dict(
        boards, len(boards), bool(resp.get("isLast")), offset, max_results
    )

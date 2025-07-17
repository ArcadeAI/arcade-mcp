from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian
from arcade_tdk.errors import RetryableToolError

from arcade_jira.client import JiraClient
from arcade_jira.tools.boards import get_boards_by_ids_or_names
from arcade_jira.utils import (
    build_sprint_params,
    clean_sprint_dict,
    create_board_result_dict,
    create_error_entry,
    create_sprint_result_dict,
    validate_board_limit,
    validate_sprint_limit,
)


@tool(
    requires_auth=Atlassian(
        scopes=[
            "read:board-scope:jira-software",
            "read:project:jira",
            "read:sprint:jira-software",
            "read:issue-details:jira",
            "read:board-scope.admin:jira-software",
        ]
    )
)
async def list_sprints_for_boards(
    context: ToolContext,
    boards: Annotated[
        list[str] | None,
        "List of board names or IDs to retrieve sprints for. Can contain mixed board identifiers - "
        "both numeric IDs (e.g., '123') and board names (e.g., 'My Scrum Board'). "
        "If not provided or empty, the function will automatically fetch sprints for all boards "
        "that support sprints (Scrum boards only). Example: ['123', 'My Board', '456']",
    ] = None,
    sprints_per_board: Annotated[
        int,
        "The maximum number of sprints to return per board. Must be between 1 and 50 inclusive. "
        "This limit applies individually to each board, so if you specify 10 sprints for 3 boards, "
        "you could get up to 30 total sprints. Defaults to 50 for comprehensive sprint data.",
    ] = 50,
    offset: Annotated[
        int,
        "The number of sprints to skip per board before starting to return results. "
        "Used for pagination when boards have many sprints. Applied individually to each board. "
        "For example, offset=5 would skip the first 5 sprints on each board. "
        "Must be 0 or greater. Defaults to 0 (start from the most recent sprints).",
    ] = 0,
    state: Annotated[
        str | None,
        "Filter sprints by their current state. Valid values are: "
        "'future' (not started), 'active' (currently running), 'closed' (completed). "
        "You can specify multiple states as a comma-separated list (e.g., 'active,future'). "
        "If not provided, returns sprints in all states. Example: 'active' or 'active,future'",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "A comprehensive dictionary containing sprint data for the specified boards. "
    "Includes a 'boards' list with board metadata, 'sprints_by_board' dictionary mapping "
    "board IDs to their sprint collections, and an 'errors' list for any boards that "
    "don't support sprints or couldn't be processed.",
]:
    """
    List sprints for multiple Jira boards by name or ID.
    If no boards are specified, returns sprints for all boards that support sprints.
    Returns valid responses for sprint boards and error messages for non-sprint boards.
    """
    sprints_per_board = validate_sprint_limit(sprints_per_board)
    client = JiraClient(context.get_auth_token_or_empty(), use_agile_api=True)

    # If no boards specified, get all boards with sprints
    if not boards:
        boards_response = await _list_boards_with_sprints(context, client)
        board_identifiers = [str(b["id"]) for b in boards_response["boards"]]
        if not board_identifiers:
            return {
                "message": "No boards that support sprints found.",
                "boards": [],
                "sprints_by_board": {},
                "errors": [],
            }
    else:
        board_identifiers = boards

    results = {
        "boards": [],
        "sprints_by_board": {},
        "errors": [],
    }

    # Process each board
    for board_identifier in board_identifiers:
        try:
            # Resolve board by ID or name using the new tool
            board_response = await get_boards_by_ids_or_names(context, [board_identifier])

            # Check if board was found
            if board_response["boards"]:
                board_info = board_response["boards"][0]  # Get the first (and only) board
                board_id = board_info["id"]
            elif board_response["errors"]:
                # Board not found, add the error to our results
                results["errors"].extend(board_response["errors"])
                continue
            else:
                # Unexpected case - no boards and no errors
                error_entry = create_error_entry(
                    board_identifier,
                    f"Board '{board_identifier}' could not be resolved",
                )
                results["errors"].append(error_entry)
                continue

            # Check if board supports sprints and get final type, fetch sprints in one call
            params = build_sprint_params(offset, sprints_per_board, state)
            supports_sprints, final_type, response = await _try_fetch_sprints_and_determine_type(
                client, board_info, cast(dict[str, Any], params)
            )

            if not supports_sprints:
                error_entry = create_error_entry(
                    board_identifier,
                    f"Board '{board_info.get('name', board_identifier)}' does not support sprints "
                    f"(type: {board_info.get('type', 'unknown')})",
                    board_info.get("name", "Unknown"),
                    board_id,
                )
                results["errors"].append(error_entry)
                continue

            # Update board type if it changed (simple -> scrum)
            board_info["type"] = final_type

            # Process the sprints we already fetched
            if response is None:
                # This should not happen if supports_sprints is True, but handle it gracefully
                error_entry = create_error_entry(
                    board_identifier,
                    f"Unexpected error: No sprint data received for board "
                    f"'{board_info.get('name', board_identifier)}'",
                    board_info.get("name", "Unknown"),
                    board_id,
                )
                results["errors"].append(error_entry)
                continue

            sprints = [clean_sprint_dict(s) for s in response.get("values", [])]

            results["boards"].append(board_info)
            results["sprints_by_board"][board_id] = create_sprint_result_dict(
                board_info, sprints, response
            )

        except RetryableToolError as e:
            error_entry = create_error_entry(board_identifier, str(e))
            results["errors"].append(error_entry)
        except Exception as e:
            error_entry = create_error_entry(
                board_identifier,
                f"Unexpected error processing board '{board_identifier}': {e!s}",
            )
            results["errors"].append(error_entry)

    return results


async def _try_fetch_sprints_and_determine_type(
    client: JiraClient, board: dict, params: dict
) -> tuple[bool, str, dict | None]:
    """
    Try to fetch sprints for a board and determine if it supports sprints.
    For 'simple' boards that support sprints, update their type to 'scrum'.
    Returns (supports_sprints, final_board_type, sprint_response_or_none).
    """
    board_type = board.get("type", "unknown")
    board_id = board["id"]

    # For clearly non-scrum boards, don't even try
    if board_type in ["kanban", "next-gen"]:
        return False, board_type, None

    # For all other boards (scrum, simple, unknown), try the sprint endpoint
    try:
        response = await client.get(f"/board/{board_id}/sprint", params=params)
    except Exception:
        return False, board_type, None
    else:
        # If successful and it was a simple board, update type to scrum
        final_type = "scrum" if board_type == "simple" else board_type
        return True, final_type, response


async def _list_boards_with_sprints(
    context: ToolContext,
    client: JiraClient,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """
    List all boards that support sprints (e.g., type 'scrum').
    For 'simple' boards, tries the sprint endpoint to check if they support sprints.
    """
    boards = []
    start_at = offset
    max_results = validate_board_limit(limit)

    while len(boards) < limit:
        remaining = min(max_results, limit - len(boards))
        resp = await client.get(
            "/board",
            params={"startAt": start_at, "maxResults": remaining},
        )
        batch = resp.get("values", [])

        # For each board, check if it supports sprints
        for b in batch:
            b["type"] = b.get("type")

            # Check if board supports sprints and get final type
            supports_sprints, final_type, _ = await _try_fetch_sprints_and_determine_type(
                client, b, {"maxResults": 1}
            )

            if supports_sprints:
                b["type"] = final_type  # Update type if it changed (simple -> scrum)
                boards.append(b)

            if len(boards) >= max_results:
                break

        if resp.get("isLast") or len(boards) >= max_results:
            break
        start_at += len(batch)

    # Limit to requested number
    boards = boards[:limit]
    return create_board_result_dict(
        boards, len(boards), bool(resp.get("isLast")), offset, max_results
    )

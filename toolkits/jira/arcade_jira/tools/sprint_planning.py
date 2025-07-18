import logging
from datetime import datetime
from typing import Annotated, Any, cast

from arcade_tdk import ToolContext, tool
from arcade_tdk.auth import Atlassian
from arcade_tdk.errors import ToolExecutionError

from arcade_jira.client import JiraClient
from arcade_jira.constants import BOARD_TYPES_WITH_SPRINTS
from arcade_jira.tools.boards import get_boards
from arcade_jira.utils import (
    build_sprint_params,
    clean_sprint_dict,
    create_error_entry,
    create_sprint_result_dict,
    validate_sprint_limit,
)

logger = logging.getLogger(__name__)

# Error message constants
BOARD_IDS_REQUIRED_ERROR = (
    "Board IDs are required. You must specify scrum boards to fetch sprint data."
)
CONFLICTING_DATE_PARAMS_ERROR = (
    "Cannot use 'specific_date' together with 'start_date' or 'end_date' parameters. "
    "Please use either specific_date alone or start_date/end_date for date range filtering."
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
    board_ids: Annotated[
        list[str],
        "Required list of board names or IDs to retrieve sprints for. "
        "Can contain mixed board identifiers - "
        "both numeric IDs (e.g., '123') and board names (e.g., 'My Scrum Board'). "
        "Example: ['123', 'My Board', '456']",
    ],
    sprints_per_board: Annotated[
        int,
        "The maximum number of sprints to return per board. Must be between 1 and 50 inclusive. "
        "Defaults to 50 for comprehensive sprint data. "
        "Sprints are returned with the latest ones first.",
    ] = 50,
    offset: Annotated[
        int,
        "The number of sprints to skip before starting to return results for each board. "
        "Used for pagination when boards have many sprints. Applied to each board individually. "
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
    start_date: Annotated[
        str | None,
        "Optional start date filter for sprints in YYYY-MM-DD format. "
        "Filters sprints that overlap with or occur after this date. "
        "Can be used together with end_date to create a date range. "
        "Example: '2024-01-01'",
    ] = None,
    end_date: Annotated[
        str | None,
        "Optional end date filter for sprints in YYYY-MM-DD format. "
        "Filters sprints that overlap with or occur before this date. "
        "Can be used together with start_date to create a date range. "
        "Example: '2024-03-31'",
    ] = None,
    specific_date: Annotated[
        str | None,
        "Optional specific date in YYYY-MM-DD format to get sprints that are active on that date. "
        "Returns sprints where the specific date falls between their start and end dates. "
        "Cannot be used together with start_date or end_date. Example: '2024-02-15'",
    ] = None,
) -> Annotated[
    dict[str, Any],
    "A comprehensive dictionary containing sprint data for the specified boards. "
    "Includes a 'boards' list with board metadata, 'sprints_by_board' dictionary mapping "
    "board IDs to their sprint data, and an 'errors' list for any boards that "
    "don't support sprints or couldn't be processed. Sprints are sorted with latest first.",
]:
    """
    List sprints for Jira boards by name or ID with advanced filtering and pagination.
    Requires a list of board identifiers and supports date-based filtering.
    Returns valid responses for sprint boards and error messages for non-sprint boards.
    """
    _validate_parameters(board_ids, specific_date, start_date, end_date)

    sprints_per_board = validate_sprint_limit(sprints_per_board)
    client = JiraClient(context.get_auth_token_or_empty(), use_agile_api=True)

    results = {
        "boards": [],
        "sprints_by_board": {},
        "errors": [],
    }

    # Process each board ID
    for board_id in board_ids:
        await _process_single_board(
            context,
            client,
            board_id,
            offset,
            sprints_per_board,
            state,
            start_date,
            end_date,
            specific_date,
            results,
        )

    return results


def _validate_parameters(
    board_ids: list[str], specific_date: str | None, start_date: str | None, end_date: str | None
) -> None:
    """Validate input parameters."""
    if not board_ids:
        raise ToolExecutionError(BOARD_IDS_REQUIRED_ERROR)

    if specific_date and (start_date or end_date):
        raise ToolExecutionError(CONFLICTING_DATE_PARAMS_ERROR)


async def _process_single_board(
    context: ToolContext,
    client: JiraClient,
    board_id: str,
    offset: int,
    sprints_per_board: int,
    state: str | None,
    start_date: str | None,
    end_date: str | None,
    specific_date: str | None,
    results: dict[str, Any],
) -> None:
    """Process a single board and add results to the results dictionary."""
    try:
        # Resolve board by ID or name using the boards tool
        board_response = await get_boards(context, [board_id])

        # Check if board was found
        if board_response["boards"]:
            board_info = board_response["boards"][0]  # Get the first (and only) board
            board_id_resolved = board_info["id"]
        elif board_response["errors"]:
            # Board not found, add the error to our results
            results["errors"].extend(board_response["errors"])
            return
        else:
            # Unexpected case - no boards and no errors
            error_entry = create_error_entry(
                board_id,
                f"Board '{board_id}' could not be resolved",
            )
            results["errors"].append(error_entry)
            return

        # Check if board supports sprints and get final type, fetch sprints in one call
        params = build_sprint_params(offset, sprints_per_board, state)
        supports_sprints, final_type, response = await _try_fetch_sprints_and_determine_type(
            client, board_info, cast(dict[str, Any], params)
        )

        if not supports_sprints:
            error_entry = create_error_entry(
                board_id,
                f"Board '{board_info.get('name', board_id)}' does not support sprints "
                f"(type: {board_info.get('type', 'unknown')}). "
                f"Only Scrum boards support sprints.",
                board_info.get("name", "Unknown"),
                board_id_resolved,
            )
            results["errors"].append(error_entry)
            return

        # Update board type if it changed (simple -> scrum)
        board_info["type"] = final_type

        # Process the sprints we already fetched
        if response is None:
            # This should not happen if supports_sprints is True, but handle it gracefully
            error_entry = create_error_entry(
                board_id,
                f"Unexpected error: No sprint data received for board "
                f"'{board_info.get('name', board_id)}'",
                board_info.get("name", "Unknown"),
                board_id_resolved,
            )
            results["errors"].append(error_entry)
            return

        sprints = [clean_sprint_dict(s) for s in response.get("values", [])]

        # Apply date filtering if specified
        if start_date or end_date or specific_date:
            sprints = _filter_sprints_by_date(sprints, start_date, end_date, specific_date)

        # Sort sprints with latest first (by end date, then start date, then ID)
        sprints = _sort_sprints_latest_first(sprints)

        results["boards"].append(board_info)
        results["sprints_by_board"][board_id_resolved] = create_sprint_result_dict(
            board_info, sprints, response
        )

    except ToolExecutionError:
        # Re-raise ToolExecutionErrors as-is
        raise
    except Exception as e:
        error_entry = create_error_entry(
            board_id,
            f"Unexpected error processing board '{board_id}': {e!s}",
        )
        results["errors"].append(error_entry)


async def _try_fetch_sprints_and_determine_type(
    client: JiraClient, board_info: dict[str, Any], params: dict[str, Any]
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Try to fetch sprints for a board and determine if it supports sprints.
    Returns (supports_sprints, final_board_type, response).
    """
    board_id = board_info["id"]
    board_type = board_info.get("type", "").lower()

    # If already known to support sprints, fetch directly
    if board_type in BOARD_TYPES_WITH_SPRINTS:
        try:
            response = await client.get(f"/board/{board_id}/sprint", params=params)
        except Exception:
            return False, board_type, None
        else:
            return True, board_type, response

    # For 'simple' boards or unknown types, try fetching to see if it works
    try:
        response = await client.get(f"/board/{board_id}/sprint", params=params)
    except Exception:
        # Board doesn't support sprints
        return False, board_type, None
    else:
        # If successful, it's actually a scrum board
        return True, "scrum", response


def _filter_sprints_by_date(
    sprints: list[dict], start_date: str | None, end_date: str | None, specific_date: str | None
) -> list[dict]:
    """
    Filter sprints by date range or specific date.

    Args:
        sprints: List of sprint dictionaries
        start_date: Start date string in YYYY-MM-DD format
        end_date: End date string in YYYY-MM-DD format
        specific_date: Specific date string in YYYY-MM-DD format

    Returns:
        Filtered list of sprints
    """
    if not sprints:
        return sprints

    if specific_date:
        return _filter_sprints_by_specific_date(sprints, specific_date)
    elif start_date or end_date:
        return _filter_sprints_by_date_range(sprints, start_date, end_date)

    return sprints


def _filter_sprints_by_specific_date(sprints: list[dict], target_date: str) -> list[dict]:
    """Filter sprints that are active on a specific date."""
    try:
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        # If date parsing fails, return all sprints
        return sprints

    filtered_sprints = []
    for sprint in sprints:
        start_date_str = sprint.get("startDate")
        end_date_str = sprint.get("endDate")

        # Skip sprints without dates
        if not start_date_str or not end_date_str:
            continue

        try:
            # Parse Jira date format (ISO format with timezone)
            start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00")).date()
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00")).date()

            # Check if target date is within sprint dates
            if start_date <= target <= end_date:
                filtered_sprints.append(sprint)
        except (ValueError, AttributeError):
            # If date parsing fails, include the sprint
            filtered_sprints.append(sprint)

    return filtered_sprints


def _filter_sprints_by_date_range(
    sprints: list[dict], start_date: str | None, end_date: str | None
) -> list[dict]:
    """Filter sprints that overlap with the specified date range."""
    try:
        filter_start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
        filter_end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None
    except ValueError:
        # If date parsing fails, return all sprints
        return sprints

    filtered_sprints = []
    for sprint in sprints:
        start_date_str = sprint.get("startDate")
        end_date_str = sprint.get("endDate")

        # Skip sprints without dates if we have date filters
        if (filter_start or filter_end) and (not start_date_str or not end_date_str):
            continue

        try:
            # Parse Jira date format (ISO format with timezone)
            sprint_start = (
                datetime.fromisoformat(start_date_str.replace("Z", "+00:00")).date()
                if start_date_str
                else None
            )
            sprint_end = (
                datetime.fromisoformat(end_date_str.replace("Z", "+00:00")).date()
                if end_date_str
                else None
            )

            # Check if sprint overlaps with filter range
            overlap = True

            if filter_start and sprint_end and sprint_end < filter_start:
                overlap = False

            if filter_end and sprint_start and sprint_start > filter_end:
                overlap = False

            if overlap:
                filtered_sprints.append(sprint)

        except (ValueError, AttributeError):
            # If date parsing fails, include the sprint
            filtered_sprints.append(sprint)

    return filtered_sprints


def _sort_sprints_latest_first(sprints: list[dict]) -> list[dict]:
    """Sort sprints with latest first (by end date, start date, then ID)."""
    from datetime import date as min_date

    def sort_key(sprint: dict) -> tuple:
        end_date_str = sprint.get("endDate")
        start_date_str = sprint.get("startDate")
        sprint_id = sprint.get("id")

        try:
            end_date = (
                datetime.fromisoformat(end_date_str.replace("Z", "+00:00")).date()
                if end_date_str
                else min_date.min
            )
        except (ValueError, AttributeError):
            end_date = min_date.min

        try:
            start_date = (
                datetime.fromisoformat(start_date_str.replace("Z", "+00:00")).date()
                if start_date_str
                else min_date.min
            )
        except (ValueError, AttributeError):
            start_date = min_date.min

        return (
            -end_date.toordinal() if end_date != min_date.min else float("inf"),
            -start_date.toordinal() if start_date != min_date.min else float("inf"),
            -int(sprint_id) if isinstance(sprint_id, int | str) and str(sprint_id).isdigit() else 0,
        )

    return sorted(sprints, key=sort_key)

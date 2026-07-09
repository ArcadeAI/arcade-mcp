from typing import Annotated

import httpx
from arcade_mcp_server import Context, tool
from arcade_mcp_server.auth import OAuth2

# ServiceNow incident state codes
_STATE_MAP: dict[str, str] = {
    "new": "1",
    "in_progress": "2",
    "in progress": "2",
    "on_hold": "3",
    "on hold": "3",
    "resolved": "4",
    "closed": "6",
    "cancelled": "7",
}

# ServiceNow urgency/impact codes (shared scale)
_LEVEL_MAP: dict[str, str] = {"high": "1", "medium": "2", "low": "3"}

# ServiceNow priority codes
_PRIORITY_MAP: dict[str, str] = {
    "critical": "1",
    "high": "2",
    "moderate": "3",
    "low": "4",
    "planning": "5",
}

_DEFAULT_FIELDS = (
    "sys_id,number,short_description,description,state,priority,"
    "urgency,impact,category,assigned_to,caller_id,opened_at,sys_updated_on"
)

# ServiceNow OAuth scopes are instance-specific and configured by the enterprise
# admin. Omitting scopes here requests the default access level — adjust in your
# Arcade dashboard if your instance requires explicit scope declarations.
_SERVICENOW_AUTH = OAuth2(id="servicenow")


def _headers(oauth_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {oauth_token}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _raise_for_status(response: httpx.Response, resource_hint: str = "") -> None:
    """Translate ServiceNow HTTP errors into descriptive ValueErrors."""
    if response.is_success:
        return
    code = response.status_code
    if code == 401:
        raise ValueError("ServiceNow authentication failed — your OAuth token may have expired.")
    if code == 403:
        raise ValueError(
            "Permission denied — your ServiceNow account lacks access to this resource."
        )
    if code == 404:
        hint = f": {resource_hint}" if resource_hint else ""
        raise ValueError(f"Incident not found{hint}.")
    raise ValueError(f"ServiceNow API error {code}: {response.text}")


async def _resolve_sys_id(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    instance_url: str,
    sys_id_or_number: str,
) -> str:
    """Return sys_id unchanged, or resolve an INC-prefixed number to its sys_id."""
    if not sys_id_or_number.upper().startswith("INC"):
        return sys_id_or_number

    response = await client.get(
        f"{instance_url}/api/now/table/incident",
        headers=headers,
        params={
            "sysparm_query": f"number={sys_id_or_number.upper()}",
            "sysparm_fields": "sys_id",
            "sysparm_limit": 1,
        },
    )
    _raise_for_status(response, sys_id_or_number)
    results = response.json().get("result", [])
    if not results:
        raise ValueError(f"Incident '{sys_id_or_number}' not found.")
    return results[0]["sys_id"]


@tool(
    requires_auth=_SERVICENOW_AUTH,
    requires_secrets=["SERVICENOW_INSTANCE_URL"],
)
async def create_incident(
    context: Context,
    short_description: Annotated[str, "One-line summary of the incident"],
    description: Annotated[str | None, "Detailed description of the incident"] = None,
    urgency: Annotated[
        str | None, "How quickly the incident must be resolved: 'high', 'medium', or 'low'"
    ] = None,
    impact: Annotated[
        str | None, "Business impact of the incident: 'high', 'medium', or 'low'"
    ] = None,
    category: Annotated[
        str | None, "Incident category (e.g. 'network', 'hardware', 'software', 'database')"
    ] = None,
    caller_id: Annotated[
        str | None, "ServiceNow username of the person reporting the incident"
    ] = None,
) -> dict:
    """
    Create a new ServiceNow incident.

    Returns the created incident record including its sys_id and incident number (INC...).
    """
    instance_url = context.get_secret("SERVICENOW_INSTANCE_URL").rstrip("/")
    oauth_token = context.get_auth_token_or_empty()

    payload: dict[str, str] = {"short_description": short_description}
    if description is not None:
        payload["description"] = description
    if urgency is not None:
        payload["urgency"] = _LEVEL_MAP.get(urgency.lower(), urgency)
    if impact is not None:
        payload["impact"] = _LEVEL_MAP.get(impact.lower(), impact)
    if category is not None:
        payload["category"] = category
    if caller_id is not None:
        payload["caller_id"] = caller_id

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{instance_url}/api/now/table/incident",
            headers=_headers(oauth_token),
            json=payload,
        )
        _raise_for_status(response)
        return response.json().get("result", {})


@tool(
    requires_auth=_SERVICENOW_AUTH,
    requires_secrets=["SERVICENOW_INSTANCE_URL"],
)
async def update_incident(
    context: Context,
    sys_id_or_number: Annotated[str, "The sys_id or incident number (e.g. INC0001234) to update"],
    short_description: Annotated[str | None, "New one-line summary"] = None,
    description: Annotated[str | None, "New detailed description"] = None,
    urgency: Annotated[str | None, "New urgency: 'high', 'medium', or 'low'"] = None,
    impact: Annotated[str | None, "New impact: 'high', 'medium', or 'low'"] = None,
    category: Annotated[str | None, "New category (e.g. 'network', 'hardware', 'software')"] = None,
    assigned_to: Annotated[str | None, "ServiceNow username to assign the incident to"] = None,
) -> dict:
    """
    Update one or more fields on an existing ServiceNow incident.

    Returns the full updated incident record.
    """
    instance_url = context.get_secret("SERVICENOW_INSTANCE_URL").rstrip("/")
    oauth_token = context.get_auth_token_or_empty()
    hdrs = _headers(oauth_token)

    payload: dict[str, str] = {}
    if short_description is not None:
        payload["short_description"] = short_description
    if description is not None:
        payload["description"] = description
    if urgency is not None:
        payload["urgency"] = _LEVEL_MAP.get(urgency.lower(), urgency)
    if impact is not None:
        payload["impact"] = _LEVEL_MAP.get(impact.lower(), impact)
    if category is not None:
        payload["category"] = category
    if assigned_to is not None:
        payload["assigned_to"] = assigned_to

    async with httpx.AsyncClient() as client:
        sys_id = await _resolve_sys_id(client, hdrs, instance_url, sys_id_or_number)
        response = await client.patch(
            f"{instance_url}/api/now/table/incident/{sys_id}",
            headers=hdrs,
            json=payload,
        )
        _raise_for_status(response, sys_id_or_number)
        return response.json().get("result", {})


@tool(
    requires_auth=_SERVICENOW_AUTH,
    requires_secrets=["SERVICENOW_INSTANCE_URL"],
)
async def search_incidents(
    context: Context,
    query: Annotated[
        str | None,
        "Raw ServiceNow sysparm_query string (e.g. 'priority=1^state=1'). "
        "When provided, the individual filter parameters below are ignored.",
    ] = None,
    short_description_contains: Annotated[
        str | None, "Filter to incidents whose short description contains this text"
    ] = None,
    state: Annotated[
        str | None,
        "Filter by state: 'new', 'in_progress', 'on_hold', 'resolved', 'closed', 'cancelled'",
    ] = None,
    priority: Annotated[
        str | None,
        "Filter by priority: 'critical', 'high', 'moderate', 'low', 'planning'",
    ] = None,
    assigned_to: Annotated[str | None, "Filter by assigned ServiceNow username"] = None,
    limit: Annotated[int, "Maximum number of results to return (1-100)"] = 20,
    offset: Annotated[int, "Number of results to skip for pagination (default 0)"] = 0,
) -> list[dict]:
    """
    Search or filter ServiceNow incidents.

    Supports a raw sysparm_query string for advanced filtering, or individual
    convenience filters for the most common fields. Results are ordered by most
    recently updated first.

    To paginate, increment offset by the limit value on each subsequent call
    (e.g. offset=0, offset=20, offset=40, ...).
    """
    instance_url = context.get_secret("SERVICENOW_INSTANCE_URL").rstrip("/")
    oauth_token = context.get_auth_token_or_empty()

    if query is None:
        parts: list[str] = []
        if short_description_contains:
            parts.append(f"short_descriptionLIKE{short_description_contains}")
        if state:
            parts.append(f"state={_STATE_MAP.get(state.lower(), state)}")
        if priority:
            parts.append(f"priority={_PRIORITY_MAP.get(priority.lower(), priority)}")
        if assigned_to:
            parts.append(f"assigned_to.user_name={assigned_to}")
        query = "^".join(parts) if parts else "active=true"

    params: dict[str, str | int] = {
        "sysparm_query": f"{query}^ORDERBYDESCsys_updated_on",
        "sysparm_limit": min(max(1, limit), 100),
        "sysparm_offset": max(0, offset),
        "sysparm_display_value": "true",
        "sysparm_fields": _DEFAULT_FIELDS,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{instance_url}/api/now/table/incident",
            headers=_headers(oauth_token),
            params=params,
        )
        _raise_for_status(response)
        return response.json().get("result", [])


@tool(
    requires_auth=_SERVICENOW_AUTH,
    requires_secrets=["SERVICENOW_INSTANCE_URL"],
)
async def add_comment(
    context: Context,
    sys_id_or_number: Annotated[
        str, "The sys_id or incident number (e.g. INC0001234) to comment on"
    ],
    comment: Annotated[str, "The text of the comment to add"],
    is_work_note: Annotated[
        bool,
        "If True, post as an internal work note (visible to agents only). "
        "If False, post as a customer-visible comment.",
    ] = False,
) -> dict:
    """
    Add a comment or work note to an existing ServiceNow incident.

    Work notes are internal and visible only to support agents.
    Regular comments are visible to the end user who reported the incident.
    Returns the updated incident record.
    """
    instance_url = context.get_secret("SERVICENOW_INSTANCE_URL").rstrip("/")
    oauth_token = context.get_auth_token_or_empty()
    hdrs = _headers(oauth_token)

    field = "work_notes" if is_work_note else "comments"

    async with httpx.AsyncClient() as client:
        sys_id = await _resolve_sys_id(client, hdrs, instance_url, sys_id_or_number)
        response = await client.patch(
            f"{instance_url}/api/now/table/incident/{sys_id}",
            headers=hdrs,
            json={field: comment},
        )
        _raise_for_status(response, sys_id_or_number)
        return response.json().get("result", {})


@tool(
    requires_auth=_SERVICENOW_AUTH,
    requires_secrets=["SERVICENOW_INSTANCE_URL"],
)
async def list_my_incidents(
    context: Context,
    state: Annotated[
        str | None,
        "Filter by state: 'new', 'in_progress', 'on_hold', 'resolved', 'closed', 'cancelled'",
    ] = None,
    limit: Annotated[int, "Maximum number of incidents to return (1-100)"] = 20,
    offset: Annotated[int, "Number of results to skip for pagination (default 0)"] = 0,
) -> list[dict]:
    """
    List incidents assigned to the authenticated user.

    Uses the Arcade session's user identity to filter incidents. Results are
    ordered by most recently updated first.

    To paginate, increment offset by the limit value on each subsequent call
    (e.g. offset=0, offset=20, offset=40, ...).
    """
    instance_url = context.get_secret("SERVICENOW_INSTANCE_URL").rstrip("/")
    oauth_token = context.get_auth_token_or_empty()

    # context.user_id is the Arcade user identity, used here as the ServiceNow username.
    # In deployments where identities differ, override via the search_incidents tool.
    query_parts = [f"assigned_to.user_name={context.user_id}"]
    if state:
        query_parts.append(f"state={_STATE_MAP.get(state.lower(), state)}")

    params: dict[str, str | int] = {
        "sysparm_query": "^".join(query_parts) + "^ORDERBYDESCsys_updated_on",
        "sysparm_limit": min(max(1, limit), 100),
        "sysparm_offset": max(0, offset),
        "sysparm_display_value": "true",
        "sysparm_fields": _DEFAULT_FIELDS,
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{instance_url}/api/now/table/incident",
            headers=_headers(oauth_token),
            params=params,
        )
        _raise_for_status(response)
        return response.json().get("result", [])


@tool(
    requires_auth=_SERVICENOW_AUTH,
    requires_secrets=["SERVICENOW_INSTANCE_URL"],
)
async def change_state(
    context: Context,
    sys_id_or_number: Annotated[
        str, "The sys_id or incident number (e.g. INC0001234) to transition"
    ],
    state: Annotated[
        str,
        "Target state: 'new', 'in_progress', 'on_hold', 'resolved', 'closed', or 'cancelled'",
    ],
    close_notes: Annotated[
        str | None,
        "Resolution notes describing how the incident was resolved. "
        "Required when transitioning to 'resolved' or 'closed'.",
    ] = None,
    close_code: Annotated[
        str | None,
        "Resolution code (e.g. 'Solved (Permanently)', 'Not Solved (Too Costly)'). "
        "Required by some ServiceNow configurations when closing an incident.",
    ] = None,
) -> dict:
    """
    Transition a ServiceNow incident to a new state.

    When resolving or closing an incident, provide close_notes to document the
    resolution. Returns the updated incident record.
    """
    instance_url = context.get_secret("SERVICENOW_INSTANCE_URL").rstrip("/")
    oauth_token = context.get_auth_token_or_empty()
    hdrs = _headers(oauth_token)

    payload: dict[str, str] = {"state": _STATE_MAP.get(state.lower(), state)}
    if close_notes is not None:
        payload["close_notes"] = close_notes
    if close_code is not None:
        payload["close_code"] = close_code

    async with httpx.AsyncClient() as client:
        sys_id = await _resolve_sys_id(client, hdrs, instance_url, sys_id_or_number)
        response = await client.patch(
            f"{instance_url}/api/now/table/incident/{sys_id}",
            headers=hdrs,
            json=payload,
        )
        _raise_for_status(response, sys_id_or_number)
        return response.json().get("result", {})

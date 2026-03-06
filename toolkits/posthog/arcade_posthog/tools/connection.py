"""Connection verification tool."""

from typing import Any

import httpx
from arcade_mcp_server import Context, tool

from arcade_posthog._helpers import POSTHOG_SECRETS, _classify_error, _get_project_id


@tool(requires_secrets=POSTHOG_SECRETS)
async def check_connection(context: Context) -> dict[str, Any]:
    """Verify the PostHog connection is working and show the active project. Call this first to confirm credentials before using other tools."""
    try:
        base_url = context.get_secret("POSTHOG_SERVER_URL").rstrip("/")
        api_key = context.get_secret("POSTHOG_PERSONAL_API_KEY")
        project_id = _get_project_id(context)
    except Exception as exc:
        return {"error": f"Missing configuration: {exc}", "retryable": False, "error_type": "auth"}

    url = f"{base_url}/api/projects/{project_id}/"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
    except Exception as exc:
        return _classify_error(exc)

    data = resp.json()
    return {
        "status": "connected",
        "project_id": project_id,
        "project_name": data.get("name"),
        "organization": data.get("organization", {}).get("name"),
        "posthog_url": f"{base_url}/project/{project_id}",
    }

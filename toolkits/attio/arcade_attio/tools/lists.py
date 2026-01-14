"""Attio list operations - list, get entries, add, and remove."""

from typing import Annotated

from arcade_tdk import ToolContext, tool

from arcade_attio.tools.records import _attio_request


@tool(requires_secrets=["ATTIO_API_KEY"])
async def list_lists(
    context: ToolContext,
) -> Annotated[dict, "All lists in the workspace"]:
    """
    Get all lists in the Attio workspace.

    Returns list metadata including ID, name, and parent object type.
    """
    response = await _attio_request("GET", "/lists")

    lists = []
    for lst in response.get("data", []):
        lists.append({
            "list_id": lst.get("id", {}).get("list_id", ""),
            "name": lst.get("name", ""),
            "parent_object": lst.get("parent_object", ""),
        })

    return {"lists": lists}


@tool(requires_secrets=["ATTIO_API_KEY"])
async def get_list_entries(
    context: ToolContext,
    list_id: Annotated[str, "List UUID"],
    limit: Annotated[int, "Max entries to return"] = 100,
) -> Annotated[dict, "List entries with flattened values"]:
    """
    Get entries from an Attio list.

    Returns entries with their record IDs and flattened list-specific values.
    """
    response = await _attio_request("POST", f"/lists/{list_id}/entries/query", {"limit": limit})
    entries = response.get("data", [])

    flat_entries = []
    for e in entries:
        flat = {
            "entry_id": e.get("id", {}).get("entry_id", ""),
            "record_id": e.get("record_id", ""),
        }
        for attr, val in e.get("values", {}).items():
            if val and len(val) > 0:
                first_val = val[0]
                if isinstance(first_val, dict):
                    flat[attr] = first_val.get("value", str(first_val))
                else:
                    flat[attr] = first_val
        flat_entries.append(flat)

    return {
        "total": len(flat_entries),
        "entries": flat_entries,
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def add_to_list(
    context: ToolContext,
    list_id: Annotated[str, "List UUID"],
    record_id: Annotated[str, "Record UUID to add to the list"],
    entry_values: Annotated[dict | None, "Optional list-specific attribute values"] = None,
) -> Annotated[dict, "Created entry info"]:
    """
    Add a record to an Attio list.

    Optionally set list-specific attribute values for the entry.
    """
    body: dict = {"data": {"record_id": record_id}}
    if entry_values:
        body["data"]["values"] = entry_values

    response = await _attio_request("POST", f"/lists/{list_id}/entries", body)
    entry = response.get("data", {})

    return {
        "entry_id": entry.get("id", {}).get("entry_id", ""),
        "status": "added",
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def remove_from_list(
    context: ToolContext,
    list_id: Annotated[str, "List UUID"],
    entry_id: Annotated[str, "Entry UUID (not record ID)"],
) -> Annotated[dict, "Removal confirmation"]:
    """
    Remove a record from an Attio list.

    Note: Use the entry_id, not the record_id. Get entry_id from get_list_entries.
    """
    await _attio_request("DELETE", f"/lists/{list_id}/entries/{entry_id}")
    return {"status": "removed"}

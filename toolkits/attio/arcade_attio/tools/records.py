"""Attio record operations - query, get, assert (upsert), and search."""

import json
import os
from typing import Annotated, Any

import httpx
from arcade_tdk import ToolContext, tool

ATTIO_BASE_URL = "https://api.attio.com/v2"


def _get_api_key() -> str:
    """Get Attio API key from environment."""
    key = os.environ.get("ATTIO_API_KEY", "")
    if not key:
        raise ValueError("ATTIO_API_KEY environment variable not set")
    return key


async def _attio_request(
    method: str,
    endpoint: str,
    json_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make authenticated request to Attio API."""
    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method,
            url=f"{ATTIO_BASE_URL}{endpoint}",
            headers=headers,
            json=json_data,
            timeout=30.0,
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result


def _flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    """Flatten Attio record values for easier consumption."""
    flat = {"record_id": record.get("id", {}).get("record_id", "")}
    for attr, val in record.get("values", {}).items():
        if val and len(val) > 0:
            first_val = val[0]
            if isinstance(first_val, dict):
                flat[attr] = first_val.get(
                    "value",
                    first_val.get("email_address", first_val.get("domain", str(first_val))),
                )
            else:
                flat[attr] = first_val
    return flat


@tool(requires_secrets=["ATTIO_API_KEY"])
async def query_records(
    context: ToolContext,
    object_type: Annotated[str, "Object slug: 'people', 'companies', 'deals', or custom"],
    filter_json: Annotated[
        list[str] | None,
        'Filter strings: {"attribute": "x", "operator": "equals", "value": "y"}',
    ] = None,
    limit: Annotated[int, "Max records to return (1-500)"] = 100,
    sort_by: Annotated[str | None, "Attribute to sort by"] = None,
    sort_direction: Annotated[str, "'asc' or 'desc'"] = "desc",
) -> Annotated[dict, "Query results with total count and flattened records"]:
    """
    Query Attio records with optional filtering and sorting.

    Returns flattened records with their values extracted for easy consumption.
    """
    body: dict = {"limit": min(limit, 500)}
    if filter_json:
        body["filter"] = {"filters": [json.loads(f) for f in filter_json]}
    if sort_by:
        body["sorts"] = [{"attribute": sort_by, "direction": sort_direction}]

    response = await _attio_request("POST", f"/objects/{object_type}/records/query", body)
    records = response.get("data", [])

    flat_records = [_flatten_record(r) for r in records]

    return {
        "total": len(flat_records),
        "records": flat_records,
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def get_record(
    context: ToolContext,
    object_type: Annotated[str, "Object slug: 'people', 'companies', 'deals', or custom"],
    record_id: Annotated[str, "Record UUID"],
) -> Annotated[dict, "Single record with flattened values"]:
    """
    Get a single Attio record by ID.

    Returns the record with flattened values and a direct web URL.
    """
    response = await _attio_request("GET", f"/objects/{object_type}/records/{record_id}")
    record = response.get("data", {})

    return {
        "record_id": record.get("id", {}).get("record_id", ""),
        "web_url": f"https://app.attio.com/{object_type}/{record_id}",
        "values": _flatten_record(record),
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def assert_record(
    context: ToolContext,
    object_type: Annotated[str, "Object slug: 'people', 'companies', 'deals', or custom"],
    matching_attribute: Annotated[
        str,
        "Attribute for upsert match (e.g., 'email_addresses', 'domains')",
    ],
    values: Annotated[dict, "Attribute values to set on the record"],
) -> Annotated[dict, "Created or updated record info"]:
    """
    Create or update (upsert) a record using Attio's assert endpoint.

    This is idempotent - safe to retry. If a record matching the attribute exists,
    it will be updated. Otherwise, a new record is created.
    """
    headers = {
        "Authorization": f"Bearer {_get_api_key()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{ATTIO_BASE_URL}/objects/{object_type}/records",
            headers=headers,
            params={"matching_attribute": matching_attribute},
            json={"data": {"values": values}},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

    record = data.get("data", {})
    record_id = record.get("id", {}).get("record_id", "")

    return {
        "record_id": record_id,
        "matched_on": matching_attribute,
        "web_url": f"https://app.attio.com/{object_type}/{record_id}",
    }


@tool(requires_secrets=["ATTIO_API_KEY"])
async def search_records(
    context: ToolContext,
    query: Annotated[str, "Search query to match against record names"],
    object_type: Annotated[str, "Object to search: 'people', 'companies', 'deals'"] = "companies",
    limit: Annotated[int, "Max results to return"] = 10,
) -> Annotated[dict, "Search results with matching records"]:
    """
    Search Attio records by name.

    Queries records and filters by name match. Returns matching records
    with their object type and basic info.
    """
    body = {"limit": min(limit * 3, 100)}  # Fetch more to filter
    response = await _attio_request("POST", f"/objects/{object_type}/records/query", body)

    query_lower = query.lower()
    results = []
    for r in response.get("data", []):
        flat = _flatten_record(r)
        flat["object"] = object_type
        name = str(flat.get("name", "")).lower()
        if query_lower in name:
            results.append(flat)
            if len(results) >= limit:
                break

    return {"total": len(results), "results": results}

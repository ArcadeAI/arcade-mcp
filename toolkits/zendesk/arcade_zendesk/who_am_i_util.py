from typing import Any, TypedDict

import httpx
from arcade_tdk import ToolContext


class WhoAmIResponse(TypedDict, total=False):
    user_id: int
    name: str
    email: str
    role: str
    active: bool
    verified: bool
    locale: str
    time_zone: str
    organization_id: int
    organization_name: str
    organization_domains: list[str]
    zendesk_access: bool


async def build_who_am_i_response(context: ToolContext) -> WhoAmIResponse:
    """Build comprehensive who am I response for Zendesk."""
    user_info = await _get_current_user(context)
    organization_info = await _get_organization_info(context, user_info.get("organization_id"))

    response_data = {}
    response_data.update(_extract_user_info(user_info))
    response_data.update(_extract_organization_info(organization_info))
    response_data["zendesk_access"] = True

    return response_data  # type: ignore[return-value]


async def _get_current_user(context: ToolContext) -> dict[str, Any]:
    """Get current user information from Zendesk API."""
    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")
    base_url = f"https://{subdomain}.zendesk.com"

    headers = {
        "Authorization": f"Bearer {context.get_auth_token_or_empty()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/api/v2/users/me", headers=headers)
        response.raise_for_status()
        return response.json().get("user", {})  # type: ignore[no-any-return]


async def _get_organization_info(
    context: ToolContext, organization_id: int | None
) -> dict[str, Any]:
    """Get organization information from Zendesk API."""
    if not organization_id:
        return {}

    subdomain = context.get_secret("ZENDESK_SUBDOMAIN")
    base_url = f"https://{subdomain}.zendesk.com"

    headers = {
        "Authorization": f"Bearer {context.get_auth_token_or_empty()}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{base_url}/api/v2/organizations/{organization_id}", headers=headers
        )
        response.raise_for_status()
        return response.json().get("organization", {})  # type: ignore[no-any-return]


def _extract_user_info(user_info: dict[str, Any]) -> dict[str, Any]:
    """Extract user information from Zendesk user response."""
    extracted = {}

    if user_info.get("id"):
        extracted["user_id"] = user_info["id"]

    if user_info.get("name"):
        extracted["name"] = user_info["name"]

    if user_info.get("email"):
        extracted["email"] = user_info["email"]

    if user_info.get("role"):
        extracted["role"] = user_info["role"]

    if "active" in user_info:
        extracted["active"] = user_info["active"]

    if "verified" in user_info:
        extracted["verified"] = user_info["verified"]

    if user_info.get("locale"):
        extracted["locale"] = user_info["locale"]

    if user_info.get("time_zone"):
        extracted["time_zone"] = user_info["time_zone"]

    if user_info.get("organization_id"):
        extracted["organization_id"] = user_info["organization_id"]

    return extracted


def _extract_organization_info(organization_info: dict[str, Any]) -> dict[str, Any]:
    """Extract organization information from Zendesk organization response."""
    extracted = {}

    if organization_info.get("name"):
        extracted["organization_name"] = organization_info["name"]

    if organization_info.get("domain_names"):
        domains = organization_info["domain_names"]
        if domains:
            extracted["organization_domains"] = domains

    return extracted

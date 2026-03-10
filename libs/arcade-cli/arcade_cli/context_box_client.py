"""HTTP client for Context Box REST API."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import httpx


class ContextBoxError(Exception):
    """Error from Context Box API."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Context Box API error ({status_code}): {message}")


class ContextBoxClient:
    """HTTP client for Context Box REST API."""

    def __init__(self, base_url: str, headers: dict[str, str]) -> None:
        self.client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Shared request handler with error mapping."""
        response = self.client.request(method, path, **kwargs)
        if response.status_code >= 400:
            try:
                body = response.json()
                error_msg = body.get("error", body.get("message", "Unknown error"))
            except Exception:
                error_msg = response.text or "Unknown error"
            raise ContextBoxError(response.status_code, error_msg)
        return response.json()

    # -- Box CRUD --

    def create_box(
        self,
        name: str,
        description: str = "",
        classification: str = "PRIVATE",
        status: str = "active",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/context-boxes",
            json={
                "name": name,
                "description": description,
                "classification": classification,
                "status": status,
            },
        )

    def get_box(self, box_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/context-boxes/{box_id}")

    def list_boxes(self, limit: int = 50, offset: int = 0) -> dict[str, Any]:
        return self._request(
            "GET", "/v1/context-boxes", params={"limit": limit, "offset": offset}
        )

    def resolve_urn(self, urn: str) -> dict[str, Any]:
        return self._request("GET", "/v1/context-boxes/resolve", params={"urn": urn})

    def transition_box(self, box_id: str, status: str) -> dict[str, Any]:
        return self._request(
            "POST", f"/v1/context-boxes/{box_id}/transition", json={"status": status}
        )

    # -- Knowledge --

    def add_knowledge(
        self,
        box_id: str,
        uri: str,
        content: str,
        mime_type: str = "text/plain",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/context-boxes/{box_id}/knowledge",
            json={"uri": uri, "content": content, "mime_type": mime_type},
        )

    def list_knowledge(self, box_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/context-boxes/{box_id}/knowledge")

    def get_knowledge(self, box_id: str, knowledge_id: str) -> dict[str, Any]:
        return self._request(
            "GET", f"/v1/context-boxes/{box_id}/knowledge/{knowledge_id}"
        )

    def delete_knowledge(self, box_id: str, knowledge_id: str) -> dict[str, Any]:
        return self._request(
            "DELETE", f"/v1/context-boxes/{box_id}/knowledge/{knowledge_id}"
        )

    def upload_knowledge(self, box_id: str, file_path: Path) -> dict[str, Any]:
        with open(file_path, "rb") as f:
            return self._request(
                "POST",
                f"/v1/context-boxes/{box_id}/knowledge/upload",
                files={"file": (file_path.name, f)},
            )

    # -- Memory --

    def get_memory(self, box_id: str, key: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/context-boxes/{box_id}/memory/{key}")

    def set_memory(self, box_id: str, key: str, value: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/v1/context-boxes/{box_id}/memory",
            json={"key": key, "value": value},
        )

    def list_memory(self, box_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/context-boxes/{box_id}/memory")

    def delete_memory(self, box_id: str, key: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/context-boxes/{box_id}/memory/{key}")

    # -- Skills --

    def add_skill(
        self,
        box_id: str,
        name: str,
        template: str,
        required_tools: list[str] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"name": name, "template": template}
        if required_tools:
            payload["required_tools"] = required_tools
        return self._request(
            "POST", f"/v1/context-boxes/{box_id}/skills", json=payload
        )

    def list_skills(self, box_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/context-boxes/{box_id}/skills")

    def delete_skill(self, box_id: str, skill_id: str) -> dict[str, Any]:
        return self._request(
            "DELETE", f"/v1/context-boxes/{box_id}/skills/{skill_id}"
        )

    # -- Tool Refs --

    def list_tool_refs(self, box_id: str) -> dict[str, Any]:
        return self._request("GET", f"/v1/context-boxes/{box_id}/tools")

    # -- Resolution Log --

    def list_resolution_log(
        self, box_id: str, limit: int = 50
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            f"/v1/context-boxes/{box_id}/resolution-log",
            params={"limit": limit},
        )

    # -- Templates --

    def list_templates(self) -> dict[str, Any]:
        return self._request("GET", "/v1/context-box-templates")

    def create_template(self, name: str, template: str) -> dict[str, Any]:
        return self._request(
            "POST",
            "/v1/context-box-templates",
            json={"name": name, "template": template},
        )

    def delete_template(self, template_id: str) -> dict[str, Any]:
        return self._request("DELETE", f"/v1/context-box-templates/{template_id}")


def get_engine_url() -> str:
    """Get engine URL from env or default."""
    return os.environ.get("ARCADE_ENGINE_URL", "http://localhost:9099")

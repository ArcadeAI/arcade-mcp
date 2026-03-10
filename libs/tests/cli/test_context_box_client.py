"""Tests for ContextBoxClient HTTP wrapper."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from arcade_cli.context_box_client import ContextBoxClient, ContextBoxError


def _make_client(handler):
    """Create a ContextBoxClient with a mock transport."""
    client = ContextBoxClient("http://test", {"Authorization": "Bearer test-key"})
    client.client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
        headers={"Authorization": "Bearer test-key"},
    )
    return client


class TestCreateBox:
    def test_create_box(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes"
            assert request.method == "POST"
            import json

            body = json.loads(request.content)
            assert body["name"] == "test/box"
            assert body["classification"] == "PRIVATE"
            return httpx.Response(
                201,
                json={"id": "abc123", "urn": "urn:arcade:ctx:test/box", "name": "test/box"},
            )

        client = _make_client(handler)
        result = client.create_box("test/box")
        assert result["id"] == "abc123"
        assert result["urn"] == "urn:arcade:ctx:test/box"


class TestListBoxes:
    def test_list_boxes(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes"
            assert request.url.params["limit"] == "50"
            assert request.url.params["offset"] == "0"
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "abc", "name": "test"}],
                    "total": 1,
                    "limit": 50,
                    "offset": 0,
                },
            )

        client = _make_client(handler)
        result = client.list_boxes()
        assert result["total"] == 1
        assert len(result["items"]) == 1


class TestResolveURN:
    def test_resolve_urn(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/resolve"
            assert request.url.params["urn"] == "urn:arcade:ctx:test/box"
            return httpx.Response(200, json={"id": "abc123", "name": "test/box"})

        client = _make_client(handler)
        result = client.resolve_urn("urn:arcade:ctx:test/box")
        assert result["id"] == "abc123"


class TestUploadKnowledge:
    def test_upload_knowledge(self, tmp_path: Path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Hello World")

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/knowledge/upload"
            assert request.method == "POST"
            assert b"test.md" in request.content
            return httpx.Response(
                201, json={"id": "k1", "uri": "test.md", "mime_type": "text/markdown"}
            )

        client = _make_client(handler)
        result = client.upload_knowledge("box1", test_file)
        assert result["id"] == "k1"


class TestErrorHandling:
    def test_404_raises_context_box_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "Box not found"})

        client = _make_client(handler)
        with pytest.raises(ContextBoxError) as exc_info:
            client.get_box("nonexistent")
        assert exc_info.value.status_code == 404
        assert "Box not found" in exc_info.value.message

    def test_500_raises_context_box_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = _make_client(handler)
        with pytest.raises(ContextBoxError) as exc_info:
            client.list_boxes()
        assert exc_info.value.status_code == 500


class TestMemory:
    def test_set_memory(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/memory"
            import json

            body = json.loads(request.content)
            assert body["key"] == "lang"
            assert body["value"] == "Go"
            return httpx.Response(200, json={"key": "lang", "value": "Go"})

        client = _make_client(handler)
        result = client.set_memory("box1", "lang", "Go")
        assert result["key"] == "lang"

    def test_get_memory(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/memory/lang"
            return httpx.Response(200, json={"key": "lang", "value": "Go"})

        client = _make_client(handler)
        result = client.get_memory("box1", "lang")
        assert result["value"] == "Go"

    def test_list_memory(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/memory"
            return httpx.Response(
                200, json={"items": [{"key": "lang", "value": "Go"}], "total": 1}
            )

        client = _make_client(handler)
        result = client.list_memory("box1")
        assert result["total"] == 1

    def test_delete_memory(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/memory/lang"
            assert request.method == "DELETE"
            return httpx.Response(200, json={"deleted": True})

        client = _make_client(handler)
        result = client.delete_memory("box1", "lang")
        assert result["deleted"] is True


class TestSkills:
    def test_add_skill(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/skills"
            import json

            body = json.loads(request.content)
            assert body["name"] == "review"
            assert body["template"] == "Review {{.Code}}"
            return httpx.Response(201, json={"id": "s1", "name": "review"})

        client = _make_client(handler)
        result = client.add_skill("box1", "review", "Review {{.Code}}")
        assert result["id"] == "s1"

    def test_list_skills(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"items": [{"id": "s1", "name": "review"}], "total": 1}
            )

        client = _make_client(handler)
        result = client.list_skills("box1")
        assert result["total"] == 1


class TestToolRefs:
    def test_list_tool_refs(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/tools"
            return httpx.Response(
                200, json={"items": [{"tool_name": "github.com/acme/deploy"}], "total": 1}
            )

        client = _make_client(handler)
        result = client.list_tool_refs("box1")
        assert result["total"] == 1


class TestResolutionLog:
    def test_list_resolution_log(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-boxes/box1/resolution-log"
            assert request.url.params["limit"] == "50"
            return httpx.Response(200, json={"items": [], "total": 0})

        client = _make_client(handler)
        result = client.list_resolution_log("box1")
        assert result["total"] == 0


class TestTemplates:
    def test_list_templates(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-box-templates"
            assert request.method == "GET"
            return httpx.Response(
                200, json={"items": [{"id": "t1", "name": "default"}], "total": 1}
            )

        client = _make_client(handler)
        result = client.list_templates()
        assert result["total"] == 1

    def test_create_template(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-box-templates"
            assert request.method == "POST"
            import json

            body = json.loads(request.content)
            assert body["name"] == "my-tmpl"
            assert body["template"] == "content here"
            return httpx.Response(201, json={"id": "t2", "name": "my-tmpl"})

        client = _make_client(handler)
        result = client.create_template("my-tmpl", "content here")
        assert result["id"] == "t2"

    def test_delete_template(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/context-box-templates/t1"
            assert request.method == "DELETE"
            return httpx.Response(200, json={"deleted": True})

        client = _make_client(handler)
        result = client.delete_template("t1")
        assert result["deleted"] is True

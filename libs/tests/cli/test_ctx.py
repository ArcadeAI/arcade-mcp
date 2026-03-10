"""Tests for arcade ctx CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from arcade_cli.context_box_client import ContextBoxClient, ContextBoxError

runner = CliRunner()


def _mock_client(handler) -> ContextBoxClient:
    """Create a ContextBoxClient with a mock transport."""
    client = ContextBoxClient("http://test", {"Authorization": "Bearer test-key"})
    client.client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test",
        headers={"Authorization": "Bearer test-key"},
    )
    return client


@pytest.fixture
def mock_get_client():
    """Patch _get_client in ctx module to return a mock."""
    with patch("arcade_cli.ctx._get_client") as mock:
        yield mock


# =====================================================================
# Task 1.2: arcade ctx create
# =====================================================================


class TestCtxCreate:
    def test_ctx_create_basic(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/context-boxes":
                return httpx.Response(
                    201,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:acme-team/eng-standards",
                        "name": "acme-team/eng-standards",
                        "status": "active",
                        "classification": "PRIVATE",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["create", "acme-team/eng-standards"])
        assert result.exit_code == 0
        assert "urn:arcade:ctx:acme-team/eng-standards" in result.output

    def test_ctx_create_with_import(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        test_file = tmp_path / "CLAUDE.md"
        test_file.write_text("# Test")

        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            if request.url.path == "/v1/context-boxes" and request.method == "POST":
                if "multipart" in request.headers.get("content-type", ""):
                    call_count += 1
                    return httpx.Response(
                        201,
                        json={"id": "k1", "uri": "CLAUDE.md", "mime_type": "text/markdown"},
                    )
                return httpx.Response(
                    201,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:test/box",
                        "name": "test/box",
                        "status": "active",
                        "classification": "PRIVATE",
                    },
                )
            if "/knowledge/upload" in request.url.path:
                call_count += 1
                return httpx.Response(
                    201,
                    json={"id": "k1", "uri": "CLAUDE.md", "mime_type": "text/markdown"},
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["create", "test/box", "--import", str(test_file)]
        )
        assert result.exit_code == 0
        assert "CLAUDE.md" in result.output

    def test_ctx_create_draft(self, mock_get_client):
        from arcade_cli.ctx import app

        created_status = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal created_status
            if request.url.path == "/v1/context-boxes":
                body = json.loads(request.content)
                created_status = body.get("status")
                return httpx.Response(
                    201,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:test/box",
                        "name": "test/box",
                        "status": "draft",
                        "classification": "PRIVATE",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["create", "test/box", "--draft"])
        assert result.exit_code == 0
        assert created_status == "draft"

    def test_ctx_create_missing_name(self):
        from arcade_cli.ctx import app

        result = runner.invoke(app, ["create"])
        assert result.exit_code != 0


# =====================================================================
# Task 1.3: arcade ctx connect
# =====================================================================


class TestCtxConnect:
    def test_ctx_connect_claude(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:acme/standards",
                        "name": "acme/standards",
                        "status": "active",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        config_path = tmp_path / ".mcp.json"

        result = runner.invoke(
            app,
            [
                "connect",
                "urn:arcade:ctx:acme/standards",
                "--agent",
                "claude",
                "--config-path",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert "mcpServers" in config
        assert "context-box-acme-standards" in config["mcpServers"]

    def test_ctx_connect_cursor(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:acme/standards",
                        "name": "acme/standards",
                        "status": "active",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        config_path = tmp_path / "mcp.json"

        result = runner.invoke(
            app,
            [
                "connect",
                "urn:arcade:ctx:acme/standards",
                "--agent",
                "cursor",
                "--config-path",
                str(config_path),
            ],
        )
        assert result.exit_code == 0
        assert config_path.exists()
        config = json.loads(config_path.read_text())
        assert "mcpServers" in config

    def test_ctx_connect_explicit_agent(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:acme/standards",
                        "name": "acme/standards",
                        "status": "active",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        config_path = tmp_path / "mcp.json"

        result = runner.invoke(
            app,
            [
                "connect",
                "urn:arcade:ctx:acme/standards",
                "--agent",
                "cursor",
                "--config-path",
                str(config_path),
            ],
        )
        assert result.exit_code == 0

    def test_ctx_connect_box_not_found(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "Box not found"})

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            [
                "connect",
                "urn:arcade:ctx:nope/nope",
                "--agent",
                "claude",
                "--config-path",
                "/tmp/test.json",
            ],
        )
        assert result.exit_code != 0 or "Error" in result.output

    def test_ctx_connect_no_agent(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "abc123",
                        "urn": "urn:arcade:ctx:acme/standards",
                        "name": "acme/standards",
                        "status": "active",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)

        # Without --agent and no agent detected, should error
        with patch("arcade_cli.ctx._detect_agent", return_value=None):
            result = runner.invoke(
                app,
                ["connect", "urn:arcade:ctx:acme/standards"],
            )
            assert "Error" in result.output or result.exit_code != 0


# =====================================================================
# Task 1.4: arcade ctx list + arcade ctx status
# =====================================================================


class TestCtxList:
    def test_ctx_list_table(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "items": [
                        {
                            "id": "abc",
                            "name": "acme-team/eng-standards",
                            "urn": "urn:arcade:ctx:acme-team/eng-standards",
                            "status": "active",
                        }
                    ],
                    "total": 1,
                    "limit": 50,
                    "offset": 0,
                },
            )

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "acme-team/eng-standards" in result.output

    def test_ctx_list_json(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "items": [{"id": "abc", "name": "test"}],
                    "total": 1,
                    "limit": 50,
                    "offset": 0,
                },
            )

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["list", "--format", "json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["total"] == 1

    def test_ctx_list_empty(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"items": [], "total": 0, "limit": 50, "offset": 0},
            )

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No context boxes found" in result.output


class TestCtxStatus:
    def test_ctx_status(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "abc123",
                        "name": "acme/standards",
                        "urn": "urn:arcade:ctx:acme/standards",
                        "status": "active",
                        "classification": "PRIVATE",
                        "description": "Engineering standards",
                        "created_at": "2026-03-07T10:00:00Z",
                    },
                )
            if "/knowledge" in request.url.path:
                return httpx.Response(
                    200, json={"items": [{"uri": "CLAUDE.md"}], "total": 1}
                )
            if "/memory" in request.url.path:
                return httpx.Response(
                    200, json={"items": [{"key": "lang", "value": "Go"}], "total": 1}
                )
            if "/skills" in request.url.path:
                return httpx.Response(
                    200, json={"items": [{"name": "review"}], "total": 1}
                )
            if "/tools" in request.url.path:
                return httpx.Response(
                    200, json={"items": [{"tool_name": "deploy"}], "total": 1}
                )
            return httpx.Response(200, json={})

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["status", "urn:arcade:ctx:acme/standards"])
        assert result.exit_code == 0
        assert "acme/standards" in result.output
        assert "active" in result.output

    def test_ctx_status_not_found(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"error": "Not found"})

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["status", "urn:arcade:ctx:nope/nope"])
        assert "Error" in result.output or result.exit_code != 0


# =====================================================================
# Task 1.5: arcade ctx push + arcade ctx pull
# =====================================================================


class TestCtxPush:
    def test_ctx_push_single(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        test_file = tmp_path / "README.md"
        test_file.write_text("# Hello")

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={"id": "box1", "urn": "urn:arcade:ctx:test/box"},
                )
            if "/knowledge/upload" in request.url.path:
                return httpx.Response(
                    201,
                    json={"id": "k1", "uri": "README.md", "mime_type": "text/markdown"},
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["push", "urn:arcade:ctx:test/box", str(test_file)]
        )
        assert result.exit_code == 0
        assert "README.md" in result.output

    def test_ctx_push_multiple(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        f1 = tmp_path / "a.md"
        f1.write_text("# A")
        f2 = tmp_path / "b.md"
        f2.write_text("# B")

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={"id": "box1", "urn": "urn:arcade:ctx:test/box"},
                )
            if "/knowledge/upload" in request.url.path:
                return httpx.Response(
                    201,
                    json={"id": "k1", "uri": "file.md", "mime_type": "text/markdown"},
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["push", "urn:arcade:ctx:test/box", str(f1), str(f2)]
        )
        assert result.exit_code == 0
        assert "2 files" in result.output


class TestCtxPull:
    def test_ctx_pull(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={"id": "box1", "urn": "urn:arcade:ctx:test/box"},
                )
            if "/knowledge" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {"id": "k1", "uri": "CLAUDE.md", "content": "# Hello", "content_url": ""},
                        ],
                        "total": 1,
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["pull", "urn:arcade:ctx:test/box", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / "CLAUDE.md").read_text() == "# Hello"

    def test_ctx_pull_output_dir(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        out_dir = tmp_path / "output"

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={"id": "box1", "urn": "urn:arcade:ctx:test/box"},
                )
            if "/knowledge" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {"id": "k1", "uri": "test.txt", "content": "hello", "content_url": ""},
                        ],
                        "total": 1,
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["pull", "urn:arcade:ctx:test/box", "--output-dir", str(out_dir)]
        )
        assert result.exit_code == 0
        assert (out_dir / "test.txt").exists()


# =====================================================================
# Task 2.1: arcade ctx transition
# =====================================================================


class TestCtxTransition:
    def test_ctx_transition_active_to_archived(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200,
                    json={"id": "box1", "urn": "urn:arcade:ctx:test/box"},
                )
            if "/transition" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "id": "box1",
                        "status": "archived",
                        "urn": "urn:arcade:ctx:test/box",
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["transition", "urn:arcade:ctx:test/box", "archived"]
        )
        assert result.exit_code == 0
        assert "archived" in result.output

    def test_ctx_transition_invalid_status(self):
        from arcade_cli.ctx import app

        result = runner.invoke(
            app, ["transition", "urn:arcade:ctx:test/box", "bogus"]
        )
        assert result.exit_code != 0 or "Invalid status" in result.output


# =====================================================================
# Task 2.2: arcade ctx memory
# =====================================================================


class TestCtxMemory:
    def test_ctx_memory_list(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/memory" in request.url.path and request.method == "GET":
                return httpx.Response(
                    200,
                    json={
                        "items": [{"key": "lang", "value": "Go"}],
                        "total": 1,
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["memory", "urn:arcade:ctx:test/box", "list"]
        )
        assert result.exit_code == 0
        assert "lang" in result.output

    def test_ctx_memory_set_get(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/memory" in request.url.path:
                if request.method == "POST":
                    return httpx.Response(
                        200, json={"key": "lang", "value": "Go"}
                    )
                if request.method == "GET":
                    return httpx.Response(
                        200, json={"key": "lang", "value": "Go"}
                    )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["memory", "urn:arcade:ctx:test/box", "set", "lang", "Go"]
        )
        assert result.exit_code == 0
        assert "lang" in result.output

    def test_ctx_memory_delete(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/memory/" in request.url.path and request.method == "DELETE":
                return httpx.Response(200, json={"deleted": True})
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["memory", "urn:arcade:ctx:test/box", "delete", "lang"]
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output

    def test_ctx_memory_get_not_found(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            return httpx.Response(404, json={"error": "Not found"})

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["memory", "urn:arcade:ctx:test/box", "get", "nope"]
        )
        assert "Error" in result.output or result.exit_code != 0


# =====================================================================
# Task 2.3: arcade ctx skills
# =====================================================================


class TestCtxSkills:
    def test_ctx_skills_list(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/skills" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "items": [{"id": "s1", "name": "review"}],
                        "total": 1,
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["skills", "urn:arcade:ctx:test/box", "list"]
        )
        assert result.exit_code == 0
        assert "review" in result.output

    def test_ctx_skills_add(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        tmpl = tmp_path / "template.txt"
        tmpl.write_text("Review {{.Code}}")

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/skills" in request.url.path and request.method == "POST":
                return httpx.Response(
                    201, json={"id": "s1", "name": "review"}
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            [
                "skills",
                "urn:arcade:ctx:test/box",
                "add",
                "--name",
                "review",
                "--template",
                str(tmpl),
            ],
        )
        assert result.exit_code == 0
        assert "review" in result.output

    def test_ctx_skills_delete(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/skills/" in request.url.path and request.method == "DELETE":
                return httpx.Response(200, json={"deleted": True})
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            ["skills", "urn:arcade:ctx:test/box", "delete", "s1"],
        )
        assert result.exit_code == 0
        assert "Deleted" in result.output


# =====================================================================
# Task 2.4: arcade ctx logs
# =====================================================================


class TestCtxLogs:
    def test_ctx_logs(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/resolution-log" in request.url.path:
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {
                                "id": "l1",
                                "facets_requested": "knowledge,memory",
                                "facets_returned": "knowledge,memory",
                                "created_at": "2026-03-07T10:00:00Z",
                            }
                        ],
                        "total": 1,
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["logs", "urn:arcade:ctx:test/box"])
        assert result.exit_code == 0

    def test_ctx_logs_limit(self, mock_get_client):
        from arcade_cli.ctx import app

        captured_limit = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_limit
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/resolution-log" in request.url.path:
                captured_limit = request.url.params.get("limit")
                return httpx.Response(
                    200, json={"items": [], "total": 0}
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app, ["logs", "urn:arcade:ctx:test/box", "--limit", "5"]
        )
        assert result.exit_code == 0
        assert captured_limit == "5"


# =====================================================================
# Task 2.5: arcade ctx template
# =====================================================================


class TestCtxTemplate:
    def test_ctx_template_list(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/context-box-templates":
                return httpx.Response(
                    200,
                    json={
                        "items": [{"id": "t1", "name": "onboarding"}],
                        "total": 1,
                    },
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["template", "list"])
        assert result.exit_code == 0
        assert "onboarding" in result.output

    def test_ctx_template_create(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        tmpl = tmp_path / "template.yaml"
        tmpl.write_text("name: onboarding\nknowledge:\n  - CLAUDE.md\n")

        def handler(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/v1/context-box-templates" and request.method == "POST":
                return httpx.Response(
                    201, json={"id": "t1", "name": "onboarding"}
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            ["template", "create", "--name", "onboarding", "--file", str(tmpl)],
        )
        assert result.exit_code == 0
        assert "onboarding" in result.output

    def test_ctx_template_delete(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "/context-box-templates/" in request.url.path and request.method == "DELETE":
                return httpx.Response(200, json={"deleted": True})
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(app, ["template", "delete", "t1"])
        assert result.exit_code == 0
        assert "Deleted" in result.output

"""Tests for arcade ctx CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

from arcade_cli.context_box_client import ContextBoxClient, ContextBoxError
from arcade_cli.ctx import (
    AGENT_PROFILES,
    CollectedFile,
    _collect_files,
    _detect_agent_profiles,
    _encode_project_path,
)

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
            app, ["memory", "list", "urn:arcade:ctx:test/box"]
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
            app, ["memory", "set", "urn:arcade:ctx:test/box", "lang", "Go"]
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
            app, ["memory", "delete", "urn:arcade:ctx:test/box", "lang"]
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
            app, ["memory", "get", "urn:arcade:ctx:test/box", "nope"]
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
            app, ["skills", "list", "urn:arcade:ctx:test/box"]
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
                "add",
                "urn:arcade:ctx:test/box",
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
            ["skills", "delete", "urn:arcade:ctx:test/box", "s1"],
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


# =====================================================================
# Agent filesystem detection
# =====================================================================


class TestDetectAgentProfiles:
    def test_detect_claude(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        profiles = _detect_agent_profiles(tmp_path)
        assert len(profiles) == 1
        assert profiles[0].name == "claude"

    def test_claude_md_alone_does_not_trigger(self, tmp_path: Path):
        """CLAUDE.md alone should NOT detect claude — only .claude/ dir does."""
        (tmp_path / "CLAUDE.md").write_text("# Instructions")
        profiles = _detect_agent_profiles(tmp_path)
        assert profiles == []

    def test_detect_cursor(self, tmp_path: Path):
        (tmp_path / ".cursor").mkdir()
        profiles = _detect_agent_profiles(tmp_path)
        assert len(profiles) == 1
        assert profiles[0].name == "cursor"

    def test_cursorrules_alone_does_not_trigger(self, tmp_path: Path):
        """.cursorrules file alone should NOT detect cursor — only .cursor/ dir does."""
        (tmp_path / ".cursorrules").write_text("rules")
        profiles = _detect_agent_profiles(tmp_path)
        assert profiles == []

    def test_detect_codex(self, tmp_path: Path):
        (tmp_path / ".codex").mkdir()
        profiles = _detect_agent_profiles(tmp_path)
        assert len(profiles) == 1
        assert profiles[0].name == "codex"

    def test_detect_multiple(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".cursor").mkdir()
        profiles = _detect_agent_profiles(tmp_path)
        names = {p.name for p in profiles}
        assert "claude" in names
        assert "cursor" in names

    def test_detect_none(self, tmp_path: Path):
        profiles = _detect_agent_profiles(tmp_path)
        assert profiles == []

    def test_unsupported_agent_not_detected(self, tmp_path: Path):
        """Windsurf, openclaw, cadecoder are not supported yet."""
        (tmp_path / ".windsurf").mkdir()
        profiles = _detect_agent_profiles(tmp_path)
        assert profiles == []


class TestCollectFiles:
    def test_collect_claude_project_files(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("{}")
        (tmp_path / "CLAUDE.md").write_text("# Instructions")
        (tmp_path / "AGENTS.md").write_text("# Agents")

        profiles = _detect_agent_profiles(tmp_path)
        files = _collect_files(tmp_path, profiles, include_home=False)
        names = {cf.path.name for cf in files}
        assert "CLAUDE.md" in names
        assert "AGENTS.md" in names
        assert "settings.json" in names

    def test_collect_cursor_project_files(self, tmp_path: Path):
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursor" / "mcp.json").write_text("{}")
        rules_dir = tmp_path / ".cursor" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "style.md").write_text("# Style rules")
        (tmp_path / ".cursorrules").write_text("rules here")

        profiles = _detect_agent_profiles(tmp_path)
        files = _collect_files(tmp_path, profiles, include_home=False)
        names = {cf.path.name for cf in files}
        assert "mcp.json" in names
        assert "style.md" in names
        assert ".cursorrules" in names

    def test_collect_cursor_home_skills(self, tmp_path: Path):
        """Cursor skills live at ~/.cursor/skills/, not project level."""
        (tmp_path / ".cursor").mkdir()

        fake_home = tmp_path / "fakehome"
        skills_dir = fake_home / ".cursor" / "skills" / "review"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("# Review skill")
        (fake_home / ".cursor" / "mcp.json").write_text("{}")

        profiles = _detect_agent_profiles(tmp_path)
        with patch("arcade_cli.ctx.Path.home", return_value=fake_home):
            files = _collect_files(tmp_path, profiles, include_home=True)
        names = {cf.path.name for cf in files}
        assert "SKILL.md" in names
        assert "mcp.json" in names

    def test_collect_skips_large_files(self, tmp_path: Path):
        (tmp_path / ".claude").mkdir()
        big_file = tmp_path / "CLAUDE.md"
        big_file.write_text("x" * (512 * 1024 + 1))  # Over 512KB

        profiles = _detect_agent_profiles(tmp_path)
        files = _collect_files(tmp_path, profiles, include_home=False)
        paths = {cf.path for cf in files}
        assert big_file not in paths

    def test_collect_home_memory_files(self, tmp_path: Path):
        """Simulate home-level memory files for the project."""
        (tmp_path / ".claude").mkdir()

        # Create a fake home dir with project memory
        fake_home = tmp_path / "fakehome"
        encoded = _encode_project_path(tmp_path)
        mem_dir = fake_home / ".claude" / "projects" / encoded / "memory"
        mem_dir.mkdir(parents=True)
        (mem_dir / "MEMORY.md").write_text("# Notes")

        profiles = _detect_agent_profiles(tmp_path)
        with patch("arcade_cli.ctx.Path.home", return_value=fake_home):
            files = _collect_files(tmp_path, profiles, include_home=True)
        names = {cf.path.name for cf in files}
        assert "MEMORY.md" in names

    def test_collect_home_global_files(self, tmp_path: Path):
        """Simulate home-level global settings."""
        (tmp_path / ".claude").mkdir()

        fake_home = tmp_path / "fakehome"
        (fake_home / ".claude").mkdir(parents=True)
        (fake_home / ".claude" / "settings.json").write_text('{"global": true}')

        profiles = _detect_agent_profiles(tmp_path)
        with patch("arcade_cli.ctx.Path.home", return_value=fake_home):
            files = _collect_files(tmp_path, profiles, include_home=True)
        # Should have both project and home settings.json
        settings_files = [cf for cf in files if cf.path.name == "settings.json"]
        assert len(settings_files) >= 1

    def test_collect_codex_files(self, tmp_path: Path):
        (tmp_path / ".codex").mkdir()
        (tmp_path / ".codex" / "instructions.md").write_text("# Codex")
        (tmp_path / ".codex" / "config.json").write_text("{}")

        profiles = _detect_agent_profiles(tmp_path)
        files = _collect_files(tmp_path, profiles, include_home=False)
        names = {cf.path.name for cf in files}
        assert "instructions.md" in names
        assert "config.json" in names

    def test_collected_file_has_uri_prefix(self, tmp_path: Path):
        """Home-level files should have a uri_prefix, project files should not."""
        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Test")

        fake_home = tmp_path / "fakehome"
        (fake_home / ".claude").mkdir(parents=True)
        (fake_home / ".claude" / "settings.json").write_text("{}")

        profiles = _detect_agent_profiles(tmp_path)
        with patch("arcade_cli.ctx.Path.home", return_value=fake_home):
            files = _collect_files(tmp_path, profiles, include_home=True)

        project_files = [cf for cf in files if not cf.uri_prefix]
        home_files = [cf for cf in files if cf.uri_prefix]
        assert any(cf.path.name == "CLAUDE.md" for cf in project_files)
        assert any(cf.path.name == "settings.json" for cf in home_files)


class TestEncodeProjectPath:
    def test_encode_simple(self):
        assert _encode_project_path(Path("/Users/shub/myproject")) == "Users-shub-myproject"

    def test_encode_nested(self):
        result = _encode_project_path(Path("/Users/shub/Documents/GitHub/monorepo"))
        assert result == "Users-shub-Documents-GitHub-monorepo"


# =====================================================================
# arcade ctx sync
# =====================================================================


class TestCtxSync:
    def test_sync_detects_and_uploads(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        # Set up a project with .claude and CLAUDE.md
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text('{"key": "val"}')
        (tmp_path / "CLAUDE.md").write_text("# My project instructions")

        uploaded_uris: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/knowledge" in request.url.path and request.method == "POST":
                body = json.loads(request.content)
                uploaded_uris.append(body.get("uri", ""))
                return httpx.Response(
                    201, json={"id": "k1", "uri": body.get("uri", "")}
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            ["sync", "urn:arcade:ctx:test/box", "--root", str(tmp_path), "--no-home"],
        )
        assert result.exit_code == 0
        assert "claude" in result.output.lower()
        assert "CLAUDE.md" in result.output
        assert len(uploaded_uris) >= 2

    def test_sync_dry_run(self, tmp_path: Path):
        from arcade_cli.ctx import app

        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Test")

        result = runner.invoke(
            app,
            ["sync", "--root", str(tmp_path), "--dry-run", "--no-home"],
        )
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "CLAUDE.md" in result.output

    def test_sync_no_agent_detected(self, tmp_path: Path):
        from arcade_cli.ctx import app

        result = runner.invoke(
            app,
            ["sync", "--root", str(tmp_path)],
        )
        assert result.exit_code != 0
        assert "No agent config detected" in result.output

    def test_sync_auto_creates_box(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Test")

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(404, json={"error": "Not found"})
            if request.url.path == "/v1/context-boxes" and request.method == "POST":
                body = json.loads(request.content)
                return httpx.Response(
                    201,
                    json={
                        "id": "new-box",
                        "urn": f"urn:arcade:ctx:{body['name']}",
                        "name": body["name"],
                        "status": "active",
                    },
                )
            if "/knowledge" in request.url.path and request.method == "POST":
                return httpx.Response(201, json={"id": "k1"})
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            ["sync", "--root", str(tmp_path), "--no-home"],
        )
        assert result.exit_code == 0
        assert "Creating new box" in result.output

    def test_sync_multiple_agents(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# Claude")
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".cursor" / "mcp.json").write_text("{}")

        uploaded_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal uploaded_count
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/knowledge" in request.url.path and request.method == "POST":
                uploaded_count += 1
                return httpx.Response(201, json={"id": "k1"})
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            ["sync", "urn:arcade:ctx:test/box", "--root", str(tmp_path), "--no-home"],
        )
        assert result.exit_code == 0
        assert "claude" in result.output.lower()
        assert "cursor" in result.output.lower()
        assert uploaded_count >= 2


# =====================================================================
# arcade ctx push --auto
# =====================================================================


class TestCtxPushAuto:
    def test_push_auto_detects_and_uploads(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        (tmp_path / ".claude").mkdir()
        (tmp_path / "CLAUDE.md").write_text("# My project")

        uploaded_uris: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            if "/knowledge" in request.url.path and request.method == "POST":
                body = json.loads(request.content)
                uploaded_uris.append(body.get("uri", ""))
                return httpx.Response(201, json={"id": "k1"})
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)

        # We need to patch cwd since push --auto uses Path.cwd()
        with patch("arcade_cli.ctx.Path.cwd", return_value=tmp_path):
            result = runner.invoke(
                app,
                ["push", "urn:arcade:ctx:test/box", "--auto"],
            )
        assert result.exit_code == 0
        assert "CLAUDE.md" in " ".join(uploaded_uris)

    def test_push_auto_no_agents(self, mock_get_client, tmp_path: Path):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        with patch("arcade_cli.ctx.Path.cwd", return_value=tmp_path):
            result = runner.invoke(
                app,
                ["push", "urn:arcade:ctx:test/box", "--auto"],
            )
        assert result.exit_code != 0
        assert "No agent config detected" in result.output

    def test_push_no_files_no_auto(self, mock_get_client):
        from arcade_cli.ctx import app

        def handler(request: httpx.Request) -> httpx.Response:
            if "resolve" in request.url.path:
                return httpx.Response(
                    200, json={"id": "box1", "urn": "urn:arcade:ctx:test/box"}
                )
            return httpx.Response(404)

        mock_get_client.return_value = _mock_client(handler)
        result = runner.invoke(
            app,
            ["push", "urn:arcade:ctx:test/box"],
        )
        assert result.exit_code != 0
        assert "Provide files" in result.output or "auto" in result.output

"""Checking the Engine hosts MCP servers before an MCP deploy uploads anything."""

from typing import Any
from unittest.mock import patch

import httpx
import pytest
from arcade_cli.context import DiscoveryDocument
from arcade_cli.deploy import DeployRefusedError, check_mcp_deployments

ENGINE = "https://engine.acme.internal"


def discovery(status_code: int = 200, body: Any = None) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=body,
        request=httpx.Request("GET", f"{ENGINE}/.well-known/arcade"),
    )


def deployments(**fields: Any) -> dict[str, Any]:
    return {"engine": ENGINE, "deployments": {"enabled": True, "provider": "kubernetes", **fields}}


PYTHON_RUNNER = {"language": "python", "version": "3.12", "platform": "musllinux_1_2"}


class TestDiscoveryDocument:
    def test_protocols_and_runners_are_read(self) -> None:
        doc = DiscoveryDocument.model_validate(
            deployments(protocols=["arcade", "mcp"], runners=[PYTHON_RUNNER])
        )

        assert doc.deployments.protocols == ["arcade", "mcp"]
        assert doc.deployments.runners[0].version == "3.12"
        assert doc.deployments.runners[0].platform == "musllinux_1_2"

    def test_an_older_engine_reports_neither(self) -> None:
        doc = DiscoveryDocument.model_validate(deployments())

        assert doc.deployments.protocols == []
        assert doc.deployments.runners == []

    @pytest.mark.parametrize("field", ["protocols", "runners"])
    def test_a_null_list_reads_as_empty(self, field: str) -> None:
        doc = DiscoveryDocument.model_validate(deployments(**{field: None}))

        assert getattr(doc.deployments, field) == []

    def test_a_runner_entry_that_cant_be_read_is_skipped(self) -> None:
        doc = DiscoveryDocument.model_validate(
            deployments(runners=[{"language": "python"}, "python3.12", PYTHON_RUNNER])
        )

        assert [r.version for r in doc.deployments.runners] == ["3.12"]

    def test_an_unexpected_capabilities_shape_still_parses_the_document(self) -> None:
        # Discovery also drives `arcade login`; a newer capabilities shape must not break it.
        doc = DiscoveryDocument.model_validate(deployments(protocols="mcp", runners={"a": 1}))

        assert doc.deployments.enabled is True
        assert doc.deployments.protocols == []
        assert doc.deployments.runners == []

    def test_an_unknown_runner_field_is_ignored(self) -> None:
        doc = DiscoveryDocument.model_validate(
            deployments(runners=[{**PYTHON_RUNNER, "architectures": ["x86_64"]}])
        )

        assert doc.deployments.runners[0].language == "python"


class TestCheckMCPDeployments:
    def check(self, response: httpx.Response) -> Any:
        with patch("arcade_cli.context.httpx.get", return_value=response) as get:
            result = check_mcp_deployments(ENGINE)
        get.assert_called_once()
        assert get.call_args.args[0] == f"{ENGINE}/.well-known/arcade"
        return result

    def test_an_engine_with_mcp_returns_its_python_runners(self) -> None:
        other = {"language": "node", "version": "22", "platform": "linux"}
        runners = self.check(
            discovery(body=deployments(protocols=["arcade", "mcp"], runners=[PYTHON_RUNNER, other]))
        )

        assert [(r.language, r.version) for r in runners] == [("python", "3.12")]

    def test_an_engine_without_mcp_is_refused(self) -> None:
        with pytest.raises(DeployRefusedError, match="doesn't host MCP servers yet"):
            self.check(discovery(body=deployments(protocols=["arcade"], runners=[PYTHON_RUNNER])))

    def test_an_engine_that_reports_no_protocols_is_refused(self) -> None:
        with pytest.raises(DeployRefusedError, match="doesn't host MCP servers yet"):
            self.check(discovery(body=deployments()))

    def test_disabled_deployments_are_refused_with_the_reason(self) -> None:
        body = {"deployments": {"enabled": False, "reason": "no deployment provider is configured"}}

        with pytest.raises(DeployRefusedError, match="no deployment provider is configured"):
            self.check(discovery(body=body))

    def test_an_engine_without_discovery_is_refused(self) -> None:
        with pytest.raises(DeployRefusedError, match="predates MCP server deploys"):
            self.check(discovery(404))

    def test_an_unreachable_discovery_document_is_refused(self) -> None:
        with (
            patch("arcade_cli.context.httpx.get", side_effect=httpx.ConnectError("refused")),
            pytest.raises(DeployRefusedError, match="Couldn't check whether"),
        ):
            check_mcp_deployments(ENGINE)

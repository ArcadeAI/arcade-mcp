from arcade_cli.deploy import (
    CreateDeploymentRequest,
    DeploymentToolkits,
    OAuthClientSettings,
    ToolkitBundle,
    UpdateDeploymentRequest,
)


def _request(provider: str | None = None) -> CreateDeploymentRequest:
    return CreateDeploymentRequest(
        name="echo",
        description="",
        toolkits=DeploymentToolkits(bundles=[]),
        provider=provider,
    )


def _arcade_bundle() -> ToolkitBundle:
    return ToolkitBundle(
        name="echo", version="1.0.0", bytes="dGFy", type="mcp", entrypoint="server.py"
    )


class TestCreateDeploymentRequest:
    def test_an_unnamed_provider_is_left_out_entirely(self) -> None:
        assert "provider" not in _request().model_dump()

    def test_a_named_provider_is_sent(self) -> None:
        assert _request("kubernetes").model_dump()["provider"] == "kubernetes"

    def test_an_explicit_exclude_none_is_respected(self) -> None:
        assert _request().model_dump(exclude_none=False)["provider"] is None


class TestArcadeDeployPayloadsAreUnchanged:
    """An Arcade-framework deploy sends exactly what it sent before MCP server deploys."""

    def test_create(self) -> None:
        request = CreateDeploymentRequest(
            name="echo",
            description="MCP Server deployed via CLI",
            toolkits=DeploymentToolkits(bundles=[_arcade_bundle()]),
        )

        assert request.model_dump() == {
            "name": "echo",
            "description": "MCP Server deployed via CLI",
            "toolkits": {
                "bundles": [
                    {
                        "name": "echo",
                        "version": "1.0.0",
                        "bytes": "dGFy",
                        "type": "mcp",
                        "entrypoint": "server.py",
                    }
                ],
                "packages": [],
            },
        }

    def test_update(self) -> None:
        request = UpdateDeploymentRequest(
            description="MCP Server deployed via CLI",
            toolkits=DeploymentToolkits(bundles=[_arcade_bundle()]),
        )

        assert request.model_dump() == {
            "description": "MCP Server deployed via CLI",
            "toolkits": {
                "bundles": [
                    {
                        "name": "echo",
                        "version": "1.0.0",
                        "bytes": "dGFy",
                        "type": "mcp",
                        "entrypoint": "server.py",
                    }
                ],
                "packages": [],
            },
        }


class TestMCPServerPayloads:
    def test_an_mcp_bundle_carries_its_protocol_and_command_and_no_entrypoint(self) -> None:
        bundle = ToolkitBundle.mcp_server(
            name="expense-tools", version="1.0.0", archive="dGFy", command="fastmcp run server.py:mcp"
        )

        assert bundle.model_dump(exclude_none=True) == {
            "name": "expense-tools",
            "version": "1.0.0",
            "bytes": "dGFy",
            "protocol": "mcp",
            "command": "fastmcp run server.py:mcp",
        }

    def test_create_sends_the_declared_values_and_oauth_client(self) -> None:
        request = CreateDeploymentRequest(
            name="expense-tools",
            description="MCP server deployed via CLI",
            toolkits=DeploymentToolkits(
                bundles=[ToolkitBundle.mcp_server("expense-tools", "1.0.0", "dGFy", "python app.py")]
            ),
            environment={"LOG_LEVEL": "info"},
            secrets={"OPENAI_API_KEY": "sk-1"},
            oauth_client=OAuthClientSettings(client_id="abc", client_secret="shh"),  # noqa: S106
        )

        payload = request.model_dump()

        assert payload["environment"] == {"LOG_LEVEL": "info"}
        assert payload["secrets"] == {"OPENAI_API_KEY": "sk-1"}
        assert payload["oauth_client"] == {"client_id": "abc", "client_secret": "shh"}
        assert "type" not in payload["toolkits"]["bundles"][0]

    def test_update_sends_empty_maps_so_removed_values_are_removed(self) -> None:
        request = UpdateDeploymentRequest(
            description="MCP server deployed via CLI",
            toolkits=DeploymentToolkits(
                bundles=[ToolkitBundle.mcp_server("expense-tools", "1.0.0", "dGFy", "python app.py")]
            ),
            environment={},
            secrets={},
        )

        payload = request.model_dump()

        assert payload["environment"] == {}
        assert payload["secrets"] == {}
        assert "oauth_client" not in payload

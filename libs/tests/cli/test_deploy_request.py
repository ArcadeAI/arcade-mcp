from arcade_cli.deploy import CreateDeploymentRequest, DeploymentToolkits


def _request(provider: str | None = None) -> CreateDeploymentRequest:
    return CreateDeploymentRequest(
        name="echo",
        description="",
        toolkits=DeploymentToolkits(bundles=[]),
        provider=provider,
    )


class TestCreateDeploymentRequest:
    def test_an_unnamed_provider_is_left_out_entirely(self) -> None:
        assert "provider" not in _request().model_dump()

    def test_a_named_provider_is_sent(self) -> None:
        assert _request("kubernetes").model_dump()["provider"] == "kubernetes"

    def test_an_explicit_exclude_none_is_respected(self) -> None:
        assert _request().model_dump(exclude_none=False)["provider"] is None

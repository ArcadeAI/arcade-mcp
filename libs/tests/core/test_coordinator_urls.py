import pytest
from arcade_core.auth_tokens import coordinator_api, coordinator_origin


class TestCoordinatorOrigin:
    @pytest.mark.parametrize(
        ("configured", "expected"),
        [
            ("https://cloud.arcade.dev", "https://cloud.arcade.dev"),
            ("https://cloud.arcade.dev/", "https://cloud.arcade.dev"),
            ("https://cloud.bosslevel.dev/api/v1", "https://cloud.bosslevel.dev"),
            ("https://cloud.bosslevel.dev/api/v1/", "https://cloud.bosslevel.dev"),
            ("https://coord.acme.internal:8443/api/v1", "https://coord.acme.internal:8443"),
        ],
    )
    def test_strips_a_trailing_api_path(self, configured: str, expected: str) -> None:
        assert coordinator_origin(configured) == expected

    def test_keeps_a_path_that_merely_contains_the_api_segment(self) -> None:
        assert (
            coordinator_origin("https://acme.internal/api/v1/tenant")
            == "https://acme.internal/api/v1/tenant"
        )


class TestCoordinatorApi:
    @pytest.mark.parametrize(
        "configured",
        [
            "https://cloud.bosslevel.dev",
            "https://cloud.bosslevel.dev/",
            "https://cloud.bosslevel.dev/api/v1",
            "https://cloud.bosslevel.dev/api/v1/",
        ],
    )
    def test_reaches_one_endpoint_however_the_address_was_supplied(self, configured: str) -> None:
        assert coordinator_api(configured) == "https://cloud.bosslevel.dev/api/v1"

    def test_is_idempotent(self) -> None:
        once = coordinator_api("https://cloud.bosslevel.dev/api/v1")
        assert coordinator_api(once) == once

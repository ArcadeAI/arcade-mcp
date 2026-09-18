from arcade_core.usage.identity import _active_context_credentials

NAMED = {
    "active_context": "bosslevel",
    "contexts": {
        "default": {
            "coordinator_url": "https://cloud.arcade.dev",
            "auth": {"access_token": "cloud-token"},
        },
        "bosslevel": {
            "coordinator_url": "https://cloud.bosslevel.dev/api/v1",
            "auth": {"access_token": "bosslevel-token"},
        },
    },
}

LEGACY = {
    "coordinator_url": "https://cloud.arcade.dev",
    "auth": {"access_token": "cloud-token"},
}


class TestActiveContextCredentials:
    def test_reads_the_context_the_user_signed_in_to(self) -> None:
        chosen = _active_context_credentials(NAMED)
        assert chosen["coordinator_url"] == "https://cloud.bosslevel.dev/api/v1"
        assert chosen["auth"]["access_token"] == "bosslevel-token"

    def test_a_config_written_before_contexts_still_reads(self) -> None:
        assert _active_context_credentials(LEGACY) == LEGACY

    def test_a_single_context_is_used_when_none_is_marked_active(self) -> None:
        only = {"contexts": {"bosslevel": NAMED["contexts"]["bosslevel"]}}
        assert _active_context_credentials(only)["auth"]["access_token"] == "bosslevel-token"

    def test_an_unresolvable_active_name_falls_back_rather_than_failing(self) -> None:
        missing = {"active_context": "gone", "contexts": NAMED["contexts"]}
        assert _active_context_credentials(missing) == missing

    def test_an_empty_config_yields_no_credentials(self) -> None:
        assert _active_context_credentials({}) == {}

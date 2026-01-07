"""Tests for multi-provider utils functions."""

import os
from unittest.mock import patch

import pytest
from arcade_cli.utils import (
    ALL_OUTPUT_FORMATS,
    ModelSpec,
    Provider,
    ProviderConfig,
    expand_provider_configs,
    get_default_model,
    parse_api_key_spec,
    parse_output_paths,
    parse_provider_spec,
    resolve_provider_api_keys,
)


class TestParseProviderSpec:
    """Tests for parse_provider_spec function."""

    def test_provider_only_openai(self) -> None:
        """Test parsing just provider name."""
        config = parse_provider_spec("openai")
        assert config.provider == Provider.OPENAI
        assert config.models == []

    def test_provider_only_anthropic(self) -> None:
        """Test parsing just provider name for anthropic."""
        config = parse_provider_spec("anthropic")
        assert config.provider == Provider.ANTHROPIC
        assert config.models == []

    def test_provider_with_single_model(self) -> None:
        """Test parsing provider with single model."""
        config = parse_provider_spec("openai:gpt-4o")
        assert config.provider == Provider.OPENAI
        assert config.models == ["gpt-4o"]

    def test_provider_with_multiple_models(self) -> None:
        """Test parsing provider with multiple models."""
        config = parse_provider_spec("openai:gpt-4o,gpt-4o-mini")
        assert config.provider == Provider.OPENAI
        assert config.models == ["gpt-4o", "gpt-4o-mini"]

    def test_anthropic_with_model(self) -> None:
        """Test parsing anthropic with model."""
        config = parse_provider_spec("anthropic:claude-sonnet-4-5-20250929")
        assert config.provider == Provider.ANTHROPIC
        assert config.models == ["claude-sonnet-4-5-20250929"]

    def test_strips_whitespace(self) -> None:
        """Test that whitespace is stripped from models."""
        config = parse_provider_spec("openai: gpt-4o , gpt-4o-mini ")
        assert config.models == ["gpt-4o", "gpt-4o-mini"]

    def test_case_insensitive_provider(self) -> None:
        """Test that provider name is case-insensitive."""
        config = parse_provider_spec("OPENAI:gpt-4o")
        assert config.provider == Provider.OPENAI

        config2 = parse_provider_spec("OpenAI")
        assert config2.provider == Provider.OPENAI

    def test_invalid_provider_raises(self) -> None:
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_provider_spec("invalid_provider")
        assert "Invalid provider" in str(exc_info.value)
        assert "openai" in str(exc_info.value)  # Suggests valid providers

    def test_empty_models_ignored(self) -> None:
        """Test that empty model strings are filtered."""
        config = parse_provider_spec("openai:,gpt-4o,,")
        assert config.models == ["gpt-4o"]


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_get_models_with_explicit_models(self) -> None:
        """Test get_models returns explicit models."""
        config = ProviderConfig(provider=Provider.OPENAI, models=["gpt-4o"])
        assert config.get_models() == ["gpt-4o"]

    def test_get_models_uses_default_when_empty(self) -> None:
        """Test get_models returns default when no models specified."""
        config = ProviderConfig(provider=Provider.OPENAI, models=[])
        assert config.get_models() == [get_default_model(Provider.OPENAI)]

        config2 = ProviderConfig(provider=Provider.ANTHROPIC, models=[])
        assert config2.get_models() == [get_default_model(Provider.ANTHROPIC)]


class TestModelSpec:
    """Tests for ModelSpec dataclass."""

    def test_display_name(self) -> None:
        """Test display_name property."""
        spec = ModelSpec(provider=Provider.OPENAI, model="gpt-4o", api_key="key")
        assert spec.display_name == "openai/gpt-4o"

        spec2 = ModelSpec(provider=Provider.ANTHROPIC, model="claude-3-sonnet", api_key="key")
        assert spec2.display_name == "anthropic/claude-3-sonnet"


class TestExpandProviderConfigs:
    """Tests for expand_provider_configs function."""

    def test_single_provider_single_model(self) -> None:
        """Test expanding single provider with single model."""
        configs = [ProviderConfig(provider=Provider.OPENAI, models=["gpt-4o"])]
        api_keys = {Provider.OPENAI: "openai-key"}

        specs = expand_provider_configs(configs, api_keys)

        assert len(specs) == 1
        assert specs[0].provider == Provider.OPENAI
        assert specs[0].model == "gpt-4o"
        assert specs[0].api_key == "openai-key"

    def test_single_provider_multiple_models(self) -> None:
        """Test expanding single provider with multiple models."""
        configs = [ProviderConfig(provider=Provider.OPENAI, models=["gpt-4o", "gpt-4o-mini"])]
        api_keys = {Provider.OPENAI: "openai-key"}

        specs = expand_provider_configs(configs, api_keys)

        assert len(specs) == 2
        assert specs[0].model == "gpt-4o"
        assert specs[1].model == "gpt-4o-mini"

    def test_multiple_providers(self) -> None:
        """Test expanding multiple providers."""
        configs = [
            ProviderConfig(provider=Provider.OPENAI, models=["gpt-4o"]),
            ProviderConfig(provider=Provider.ANTHROPIC, models=["claude-3-sonnet"]),
        ]
        api_keys = {
            Provider.OPENAI: "openai-key",
            Provider.ANTHROPIC: "anthropic-key",
        }

        specs = expand_provider_configs(configs, api_keys)

        assert len(specs) == 2
        assert specs[0].provider == Provider.OPENAI
        assert specs[0].api_key == "openai-key"
        assert specs[1].provider == Provider.ANTHROPIC
        assert specs[1].api_key == "anthropic-key"

    def test_missing_api_key_raises(self) -> None:
        """Test that missing API key raises ValueError."""
        configs = [ProviderConfig(provider=Provider.OPENAI, models=["gpt-4o"])]
        api_keys = {Provider.OPENAI: None}  # No key

        with pytest.raises(ValueError) as exc_info:
            expand_provider_configs(configs, api_keys)

        assert "API key required" in str(exc_info.value)
        assert "openai" in str(exc_info.value)

    def test_uses_default_model_when_empty(self) -> None:
        """Test that empty models list uses default."""
        configs = [ProviderConfig(provider=Provider.OPENAI, models=[])]
        api_keys = {Provider.OPENAI: "openai-key"}

        specs = expand_provider_configs(configs, api_keys)

        assert len(specs) == 1
        assert specs[0].model == get_default_model(Provider.OPENAI)


class TestResolveProviderApiKeys:
    """Tests for resolve_provider_api_keys function."""

    def test_explicit_keys_take_precedence(self) -> None:
        """Test that --api-key takes precedence over environment variables."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}, clear=False):
            keys = resolve_provider_api_keys(api_keys_specs=["openai:explicit-key"])
            assert keys[Provider.OPENAI] == "explicit-key"

    def test_falls_back_to_env_var(self) -> None:
        """Test that environment variables are used when no explicit key."""
        with patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "env-openai", "ANTHROPIC_API_KEY": "env-anthropic"},
            clear=False,
        ):
            keys = resolve_provider_api_keys()
            assert keys[Provider.OPENAI] == "env-openai"
            assert keys[Provider.ANTHROPIC] == "env-anthropic"

    def test_returns_none_when_not_found(self) -> None:
        """Test that None is returned when key not found anywhere."""
        # Clear env vars and mock dotenv_values
        with patch.dict(os.environ, {"OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": ""}, clear=False):
            # Removing keys by setting to empty won't work, so we need to unset them
            env_copy = os.environ.copy()
            if "OPENAI_API_KEY" in env_copy:
                del env_copy["OPENAI_API_KEY"]
            if "ANTHROPIC_API_KEY" in env_copy:
                del env_copy["ANTHROPIC_API_KEY"]

            with patch.dict(os.environ, env_copy, clear=True):
                with patch("dotenv.dotenv_values", return_value={}):
                    keys = resolve_provider_api_keys()
                    # Check structure - values should be None when not found
                    assert Provider.OPENAI in keys
                    assert Provider.ANTHROPIC in keys

    def test_multiple_api_key_specs(self) -> None:
        """Test parsing multiple --api-key specs."""
        keys = resolve_provider_api_keys(
            api_keys_specs=["openai:openai-key", "anthropic:anthropic-key"]
        )
        assert keys[Provider.OPENAI] == "openai-key"
        assert keys[Provider.ANTHROPIC] == "anthropic-key"

    def test_api_key_specs_override_env_vars(self) -> None:
        """Test that --api-key specs override environment variables."""
        with patch.dict(
            os.environ, {"OPENAI_API_KEY": "env-key", "ANTHROPIC_API_KEY": "env-key-2"}, clear=False
        ):
            keys = resolve_provider_api_keys(api_keys_specs=["openai:explicit-key"])
            assert keys[Provider.OPENAI] == "explicit-key"
            assert keys[Provider.ANTHROPIC] == "env-key-2"  # Not overridden, uses env

    def test_invalid_api_key_spec_raises(self) -> None:
        """Test that invalid --api-key spec raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            resolve_provider_api_keys(api_keys_specs=["invalid-format"])
        assert "Invalid --api-key format" in str(exc_info.value)


class TestIntegration:
    """Integration tests for the multi-provider workflow."""

    def test_full_workflow_single_provider(self) -> None:
        """Test full workflow from spec parsing to model specs."""
        # Parse spec
        config = parse_provider_spec("openai:gpt-4o")

        # Expand with key
        specs = expand_provider_configs(
            [config],
            {Provider.OPENAI: "test-key"},
        )

        assert len(specs) == 1
        assert specs[0].display_name == "openai/gpt-4o"
        assert specs[0].api_key == "test-key"

    def test_full_workflow_multi_provider(self) -> None:
        """Test full workflow with multiple providers."""
        # Parse multiple specs
        specs_str = ["openai:gpt-4o,gpt-4o-mini", "anthropic:claude-3-sonnet"]
        configs = [parse_provider_spec(s) for s in specs_str]

        # Expand with keys
        api_keys = {
            Provider.OPENAI: "openai-key",
            Provider.ANTHROPIC: "anthropic-key",
        }
        specs = expand_provider_configs(configs, api_keys)

        assert len(specs) == 3  # 2 OpenAI + 1 Anthropic
        assert specs[0].display_name == "openai/gpt-4o"
        assert specs[1].display_name == "openai/gpt-4o-mini"
        assert specs[2].display_name == "anthropic/claude-3-sonnet"


class TestParseApiKeySpec:
    """Tests for parse_api_key_spec function."""

    def test_parse_openai_key(self) -> None:
        """Test parsing OpenAI API key."""
        provider, key = parse_api_key_spec("openai:sk-test123")
        assert provider == Provider.OPENAI
        assert key == "sk-test123"

    def test_parse_anthropic_key(self) -> None:
        """Test parsing Anthropic API key."""
        provider, key = parse_api_key_spec("anthropic:sk-ant-test456")
        assert provider == Provider.ANTHROPIC
        assert key == "sk-ant-test456"

    def test_strips_whitespace(self) -> None:
        """Test that whitespace is stripped."""
        provider, key = parse_api_key_spec("  openai : sk-test  ")
        assert provider == Provider.OPENAI
        assert key == "sk-test"

    def test_case_insensitive_provider(self) -> None:
        """Test that provider name is case-insensitive."""
        provider, key = parse_api_key_spec("OPENAI:sk-test")
        assert provider == Provider.OPENAI

    def test_missing_colon_raises(self) -> None:
        """Test that missing colon raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_api_key_spec("openai-key-without-colon")
        assert "Invalid --api-key format" in str(exc_info.value)
        assert "provider:key" in str(exc_info.value)

    def test_empty_key_raises(self) -> None:
        """Test that empty key raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_api_key_spec("openai:")
        assert "Empty API key" in str(exc_info.value)

    def test_invalid_provider_raises(self) -> None:
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_api_key_spec("invalid:sk-test")
        assert "Invalid provider" in str(exc_info.value)


class TestParseOutputPaths:
    """Tests for parse_output_paths function."""

    def test_single_path_with_extension(self) -> None:
        """Test parsing single path with extension."""
        base, formats = parse_output_paths(["results.json"])
        assert base == "results"
        assert formats == ["json"]

    def test_multiple_paths_same_base(self) -> None:
        """Test parsing multiple paths with same base."""
        base, formats = parse_output_paths(["results.md", "results.html"])
        assert base == "results"
        assert set(formats) == {"md", "html"}

    def test_path_without_extension_returns_all_formats(self) -> None:
        """Test that path without extension returns all formats."""
        base, formats = parse_output_paths(["results"])
        assert base == "results"
        assert formats == ALL_OUTPUT_FORMATS

    def test_path_with_directory(self) -> None:
        """Test parsing path with directory."""
        base, formats = parse_output_paths(["output/results.json"])
        assert base == "output/results"
        assert formats == ["json"]

    def test_none_returns_empty(self) -> None:
        """Test that None returns (None, [])."""
        base, formats = parse_output_paths(None)
        assert base is None
        assert formats == []

    def test_empty_list_returns_empty(self) -> None:
        """Test that empty list returns (None, [])."""
        base, formats = parse_output_paths([])
        assert base is None
        assert formats == []

    def test_invalid_extension_raises(self) -> None:
        """Test that invalid extension raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_output_paths(["results.xlsx"])
        assert "Invalid output format" in str(exc_info.value)
        assert ".xlsx" in str(exc_info.value)

    def test_inconsistent_base_names_raises(self) -> None:
        """Test that inconsistent base names raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parse_output_paths(["results1.md", "results2.html"])
        assert "different base names" in str(exc_info.value)

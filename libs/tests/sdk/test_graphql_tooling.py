from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from arcade_core.errors import ToolRuntimeError

LIBS_DIR = Path(__file__).resolve().parents[2]
TDK_SRC = LIBS_DIR / "arcade-tdk"
if str(TDK_SRC) not in sys.path:
    sys.path.insert(0, str(TDK_SRC))

import arcade_tdk.error_adapters as error_adapters  # noqa: E402
import arcade_tdk.providers.graphql as graphql_provider  # noqa: E402
from arcade_tdk.providers.graphql import GraphQLErrorAdapter  # noqa: E402
from arcade_tdk.providers.http import HTTPErrorAdapter  # noqa: E402

tool_module = importlib.import_module("arcade_tdk.tool")


class DummyAdapter:
    slug = "_dummy"

    def from_exception(self, exc: Exception) -> ToolRuntimeError | None:
        return None  # pragma: no cover - trivial


def test_graphql_adapter_is_exported() -> None:
    assert "GraphQLErrorAdapter" in graphql_provider.__all__
    assert graphql_provider.GraphQLErrorAdapter is GraphQLErrorAdapter
    assert "GraphQLErrorAdapter" in error_adapters.__all__


def test_adapter_chain_appends_graphql_before_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool_module, "get_adapter_for_auth_provider", lambda auth: None)
    chain = tool_module._build_adapter_chain([], auth_provider=None)

    assert isinstance(chain[-2], GraphQLErrorAdapter)
    assert isinstance(chain[-1], HTTPErrorAdapter)


def test_adapter_chain_deduplicates_graphql_and_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool_module, "get_adapter_for_auth_provider", lambda auth: None)
    chain = tool_module._build_adapter_chain(
        [GraphQLErrorAdapter(), HTTPErrorAdapter()], auth_provider=None
    )

    types = [type(adapter) for adapter in chain]
    assert types.count(GraphQLErrorAdapter) == 1
    assert types.count(HTTPErrorAdapter) == 1


def test_adapter_chain_includes_auth_adapter_before_graphql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dummy_auth = DummyAdapter()
    monkeypatch.setattr(tool_module, "get_adapter_for_auth_provider", lambda auth: dummy_auth)
    chain = tool_module._build_adapter_chain([], auth_provider=object())

    assert chain[0] is dummy_auth
    assert isinstance(chain[1], GraphQLErrorAdapter)

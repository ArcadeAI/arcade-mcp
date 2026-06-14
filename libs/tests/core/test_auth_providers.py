"""Every OAuth2 provider class in ``arcade_core.auth`` must construct and carry its metadata.

This walks the provider classes dynamically rather than naming them, so a newly added
provider is covered the moment it lands, with no per-provider test edit. Each subclass's
``__init__`` (its ``super().__init__`` call) only runs on instantiation, so constructing
every provider here is also what exercises those lines under coverage.
"""

import inspect

import pytest
from arcade_core import auth as auth_module
from arcade_core.auth import AuthProviderType, OAuth2


def _provider_classes() -> list[type[OAuth2]]:
    """Concrete OAuth2 provider classes defined in ``arcade_core.auth`` (OAuth2 itself excluded)."""
    return [
        obj
        for _, obj in inspect.getmembers(auth_module, inspect.isclass)
        if issubclass(obj, OAuth2)
        and obj is not OAuth2
        and obj.__module__ == auth_module.__name__
    ]


def test_provider_classes_are_discovered():
    # Guards the parametrized tests below from silently collecting zero cases.
    assert _provider_classes(), "no OAuth2 provider classes found in arcade_core.auth"


@pytest.mark.parametrize("provider_cls", _provider_classes(), ids=lambda c: c.__name__)
def test_provider_constructs_with_default_metadata(provider_cls: type[OAuth2]):
    provider = provider_cls()
    assert isinstance(provider.provider_id, str)
    assert provider.provider_id
    assert provider.provider_type == AuthProviderType.oauth2
    assert provider.id is None
    assert provider.scopes is None


@pytest.mark.parametrize("provider_cls", _provider_classes(), ids=lambda c: c.__name__)
def test_provider_accepts_id_and_scopes(provider_cls: type[OAuth2]):
    provider = provider_cls(id="custom-provider-id", scopes=["scope.read", "scope.write"])
    assert provider.id == "custom-provider-id"
    assert provider.scopes == ["scope.read", "scope.write"]
    # provider_id is the fixed well-known key and is not displaced by a custom id.
    assert provider.provider_id == provider_cls().provider_id


def test_provider_ids_are_unique():
    # A copy-paste codegen slip that reused another provider's id would collide here.
    ids = [cls().provider_id for cls in _provider_classes()]
    assert len(ids) == len(set(ids)), f"duplicate provider_id values: {sorted(ids)}"

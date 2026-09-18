from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from arcade_core.config_model import Config, ContextKind
from arcade_core.constants import PROD_COORDINATOR_HOST, PROD_ENGINE_HOST
from pydantic import BaseModel, model_validator

DISCOVERY_PATH = "/.well-known/arcade"

ARCADE_URL_ENV = "ARCADE_URL"
ARCADE_API_KEY_ENV = "ARCADE_API_KEY"


class DiscoveryError(Exception):
    pass


class DiscoveryNotFoundError(DiscoveryError):
    pass


class NoCloudGuardError(Exception):
    pass


class DeploymentsDiscovery(BaseModel):
    enabled: bool = False
    reason: str = ""


class DiscoveryDocument(BaseModel):
    engine: str = ""
    coordinator: str = ""
    dashboard: str = ""
    version: str = ""
    deployments: DeploymentsDiscovery = DeploymentsDiscovery()

    @model_validator(mode="before")
    @classmethod
    def _accept_nested_urls(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        nested = data.get("urls")
        if not isinstance(nested, dict):
            return data
        merged = dict(data)
        for field in ("engine", "coordinator", "dashboard"):
            if not merged.get(field) and nested.get(field):
                merged[field] = nested[field]
        return merged


def _normalize_install_url(install_url: str) -> str:
    url = install_url.strip()
    if not urlparse(url).scheme:
        url = f"https://{url}"
    return url.rstrip("/")


def fetch_discovery(install_url: str) -> DiscoveryDocument:
    base = _normalize_install_url(install_url)
    url = f"{base}{DISCOVERY_PATH}"

    predates_message = (
        f"No Arcade discovery document was found at {url}. This installation predates "
        "discovery. Re-run 'arcade login' with the engine API URL, for example "
        "'arcade login --url https://engine.your-company.internal'."
    )

    try:
        response = httpx.get(url, timeout=30, follow_redirects=True)
    except httpx.HTTPError as e:
        raise DiscoveryError(f"Could not reach {url}: {e}") from e

    if response.status_code == 404:
        raise DiscoveryNotFoundError(predates_message)

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise DiscoveryError(
            f"Discovery request to {url} failed with HTTP {response.status_code}."
        ) from e

    try:
        return DiscoveryDocument.model_validate(response.json())
    except Exception as e:
        raise DiscoveryNotFoundError(predates_message) from e


def _hostname(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url if urlparse(url).scheme else f"//{url}", scheme="")
    return (parsed.hostname or "").lower() or None


def is_cloud_host(host: str | None) -> bool:
    if not host:
        return False
    host = host.lower()
    if host in {PROD_ENGINE_HOST, PROD_COORDINATOR_HOST}:
        return True
    return host.endswith(".arcade.dev")


def kind_for_urls(*urls: str | None) -> ContextKind:
    for url in urls:
        if is_cloud_host(_hostname(url)):
            return "cloud"
    return "self_hosted"


@dataclass
class ResolvedContext:
    name: str
    kind: ContextKind
    engine_url: str | None
    coordinator_url: str | None
    dashboard_url: str | None
    api_key: str | None
    is_ci: bool

    @property
    def is_self_hosted(self) -> bool:
        return self.kind == "self_hosted"


_pinned_ci_environment: dict[str, str | None] | None = None


def pin_ci_environment() -> None:
    global _pinned_ci_environment
    _pinned_ci_environment = {
        ARCADE_URL_ENV: os.environ.get(ARCADE_URL_ENV),
        ARCADE_API_KEY_ENV: os.environ.get(ARCADE_API_KEY_ENV),
    }


def _ci_environment_value(name: str) -> str | None:
    if _pinned_ci_environment is not None:
        return _pinned_ci_environment.get(name)
    return os.environ.get(name)


def resolve_ci_context() -> ResolvedContext | None:
    url = _ci_environment_value(ARCADE_URL_ENV)
    api_key = _ci_environment_value(ARCADE_API_KEY_ENV)
    if not url or not api_key:
        return None

    engine_url = _normalize_install_url(url)
    return ResolvedContext(
        name="env",
        kind=kind_for_urls(engine_url),
        engine_url=engine_url,
        coordinator_url=None,
        dashboard_url=None,
        api_key=api_key,
        is_ci=True,
    )


def resolve_active_context() -> ResolvedContext:
    ci = resolve_ci_context()
    if ci is not None:
        return ci

    config = Config.load_from_file()
    name = config.active_context or "default"
    return ResolvedContext(
        name=name,
        kind=config.kind,
        engine_url=config.engine_url,
        coordinator_url=config.coordinator_url,
        dashboard_url=config.dashboard_url,
        api_key=config.api_key,
        is_ci=False,
    )


def try_resolve_active_context() -> ResolvedContext | None:
    try:
        return resolve_active_context()
    except FileNotFoundError:
        return None
    except Exception:
        return None


def guard_no_cloud(url: str) -> None:
    ctx = try_resolve_active_context()
    if ctx is None or not ctx.is_self_hosted:
        return
    if is_cloud_host(_hostname(url)):
        raise NoCloudGuardError(
            f"Refusing to contact the Arcade Cloud host '{_hostname(url)}' while the "
            f"self-hosted context '{ctx.name}' is active. Artifacts and requests stay inside "
            "your environment. Switch contexts with 'arcade context use <name>' if you meant "
            "to target Arcade Cloud."
        )

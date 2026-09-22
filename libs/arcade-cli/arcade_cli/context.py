from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
from arcade_core.config_model import Config, ContextKind
from arcade_core.constants import PROD_COORDINATOR_HOST, PROD_ENGINE_HOST
from pydantic import BaseModel, model_validator

from arcade_cli import _startup_environment

DISCOVERY_PATH = "/.well-known/arcade"

ARCADE_URL_ENV = "ARCADE_URL"
ARCADE_API_KEY_ENV = "ARCADE_API_KEY"
ARCADE_CONTEXT_ENV = "ARCADE_CONTEXT"

# Set by a --context flag for the length of one command. Takes precedence over
# ARCADE_CONTEXT, which in turn takes precedence over the saved active context.
_context_override: str | None = None


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
    # urlparse reads "engine.internal:8443" as scheme "engine.internal", so a
    # host and port would be left without one and called as a bare string.
    if "://" not in url:
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


def resolve_ci_context() -> ResolvedContext | None:
    url = _startup_environment.value(ARCADE_URL_ENV)
    api_key = _startup_environment.value(ARCADE_API_KEY_ENV)
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


def override_context(name: str | None) -> None:
    """Choose the context for this invocation, ahead of the saved active one."""
    global _context_override
    _context_override = name


def selected_context_name() -> str | None:
    """The context a flag or the environment asked for, if either did."""
    from arcade_cli import _startup_environment

    return _context_override or _startup_environment.value(ARCADE_CONTEXT_ENV)


def resolve_active_context() -> ResolvedContext:
    ci = resolve_ci_context()
    if ci is not None:
        return ci

    config = Config.load_from_file()

    selected = selected_context_name()
    if selected is not None:
        # An explicit choice that does not exist is a mistake worth reporting,
        # not something to silently paper over with the active context.
        config.use_context(selected)

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
    try:
        ctx: ResolvedContext | None = resolve_active_context()
    except FileNotFoundError:
        # No credentials at all. Nothing has claimed to be self-hosted, so there
        # is nothing to protect -- a first `arcade login` has to be able to run.
        ctx = None
    except Exception as e:
        # A context file exists but could not be read. Whether it named a
        # self-hosted installation is exactly what we cannot tell, so refuse the
        # Cloud host rather than silently dropping the protection.
        if is_cloud_host(_hostname(url)):
            raise NoCloudGuardError(
                f"Refusing to contact the Arcade Cloud host '{_hostname(url)}' because the "
                f"active context could not be read: {e} Fix the credentials file, or run "
                "'arcade logout' and log in again, to make the target explicit."
            ) from e
        return

    if ctx is None or not ctx.is_self_hosted:
        return
    if is_cloud_host(_hostname(url)):
        raise NoCloudGuardError(
            f"Refusing to contact the Arcade Cloud host '{_hostname(url)}' while the "
            f"self-hosted context '{ctx.name}' is active. Artifacts and requests stay inside "
            "your environment. Switch contexts with 'arcade context set <name>' if you meant "
            "to target Arcade Cloud."
        )

"""Optional bridge to the ``arcade-telemetry`` library.

When ``arcade-telemetry`` is installed alongside ``arcade-serve``, the OTel
tracer/meter/logger providers are set up by ``arcade_telemetry.new_telemetry``
instead of ``OTELHandler``'s built-in OTLP exporters. ``OTELHandler`` still
attaches the FastAPI / HTTPX / aiohttp / Requests auto-instrumentors against
whatever the global providers happen to be, so spans flow through the
arcade-telemetry pipeline.

When ``arcade-telemetry`` is not installed, every helper here is a no-op and
``OTELHandler`` runs its original code path.
"""

from __future__ import annotations

import importlib
from typing import Any

_TELEMETRY_MODULE = "arcade_telemetry"
_STARLETTE_MODULE = "arcade_telemetry.starlette"


def _try_import(module_name: str) -> Any | None:
    try:
        return importlib.import_module(module_name)
    except ImportError:
        return None


def is_available() -> bool:
    """Return True iff ``arcade_telemetry`` can be imported."""
    return _try_import(_TELEMETRY_MODULE) is not None


def init_providers(
    *,
    service_name: str,
    environment: str,
    version: str,
    log_level: int,
) -> Any | None:
    """Initialize global OTel providers via arcade-telemetry, and wire the
    loguru → OTLP bridge if ``arcade_telemetry.loguru`` is importable.

    Returns the arcade-telemetry ``Telemetry`` handle on success, or ``None``
    if arcade-telemetry is not installed. Callers should treat ``None`` as "do
    the OTELHandler in-house setup instead". The return type is intentionally
    ``Any`` so this module doesn't pull arcade-telemetry types into the
    public arcade-serve API.
    """
    module = _try_import(_TELEMETRY_MODULE)
    if module is None:
        return None
    tel = module.new_telemetry(
        service_name=service_name,
        environment=environment,
        version=version,
        log_level=log_level,
    )
    if tel is None:
        # arcade-telemetry opted out (e.g. all signals routed to NONE) — skip
        # the loguru bridge too, otherwise OTELHandler's fallthrough to the
        # in-house OTLP path would attach loguru AND stdlib handlers.
        return None
    loguru_module = _try_import(f"{_TELEMETRY_MODULE}.loguru")
    if loguru_module is not None:
        loguru_module.install_loguru_integration(
            service=service_name,
            environment=environment,
            version=version,
            log_level=log_level,
        )
    return tel


def correlation_middleware_cls() -> type | None:
    """Return arcade-telemetry's ASGI CorrelationMiddleware class, or None."""
    module = _try_import(_STARLETTE_MODULE)
    if module is None:
        return None
    cls = getattr(module, "CorrelationMiddleware", None)
    if not isinstance(cls, type):
        return None
    return cls


def shutdown(handle: Any | None) -> None:
    """Best-effort shutdown of an arcade-telemetry handle."""
    if handle is None:
        return
    shutdown_fn = getattr(handle, "shutdown", None)
    if callable(shutdown_fn):
        shutdown_fn()

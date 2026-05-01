"""Per-request metadata isolation via ``contextvars.ContextVar``.

This module is intentionally neutral -- no imports from ``session.py``,
``server.py``, or ``context.py``. The ``ContextVar`` lives here so both
producers (server.py) and consumers (context.py) can read it without
creating import cycles.

Request metadata (such as ``progressToken``) must be isolated per request.
``asyncio.create_task()`` copies the current ContextVar state, so each
concurrent request and each spawned background task gets its own copy.
"""

from __future__ import annotations

import contextvars
from types import SimpleNamespace
from typing import Any

_current_request_meta: contextvars.ContextVar[SimpleNamespace | None] = contextvars.ContextVar(
    "_current_request_meta", default=None
)


def set_request_meta(meta: dict[str, Any] | None) -> contextvars.Token:
    """Set request metadata for the current async context. Returns a reset token."""
    if meta is None:
        return _current_request_meta.set(None)
    return _current_request_meta.set(SimpleNamespace(**meta))


def get_request_meta() -> SimpleNamespace | None:
    """Return request metadata for the current async context, or None."""
    return _current_request_meta.get()


def reset_request_meta(token: contextvars.Token) -> None:
    """Reset request metadata to prior value."""
    _current_request_meta.reset(token)

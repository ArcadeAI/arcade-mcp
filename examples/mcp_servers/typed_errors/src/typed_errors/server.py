#!/usr/bin/env python3
"""typed_errors MCP server.

Shows the family of typed tool execution errors that tool authors raise to
give the orchestrator structured retry / human-input / upstream-failure
signals. Unhandled exceptions are automatically wrapped into a fatal tool
error by the server — tool bodies should never need to raise that directly.

Typed errors available to tool authors:

- ``RetryableToolError`` — transient failure; orchestrator may retry. Can
  carry ``additional_prompt_content`` and ``retry_after_ms``.
- ``ContextRequiredToolError`` — needs human input before the orchestrator
  retries. ``additional_prompt_content`` is required.
- ``UpstreamError`` — upstream API failure. Auto-maps HTTP status to an
  ``ErrorKind`` and ``can_retry``.
- ``UpstreamRateLimitError`` — 429 with ``retry_after_ms``.

Each error serialises to a structured ``toolExecutionError`` on the wire so
the orchestrator (and any human in the loop) can reason about retry /
escalation / human-input-required without parsing message text.
"""

import random
import sys
from typing import Annotated

from arcade_mcp_server import Context, MCPApp
from arcade_mcp_server.exceptions import (
    ContextRequiredToolError,
    RetryableToolError,
    UpstreamError,
    UpstreamRateLimitError,
)

app = MCPApp(
    name="typed_errors",
    version="1.0.0",
    log_level="DEBUG",
    instructions=(
        "Every tool here deliberately raises a different typed error. Call them in "
        "sequence to see how the wire shape differs (isError, errorKind, retry_after_ms, "
        "additional_prompt_content, ...)."
    ),
)


# -----------------------------------------------------------------------------
# 1. RetryableToolError — transient failure, orchestrator may retry
# -----------------------------------------------------------------------------


@app.tool
def parse_date(
    date_str: Annotated[str, "A date string the tool will try to parse"],
) -> Annotated[str, "An ISO 8601 date"]:
    """Parse a date string. Raises ``RetryableToolError`` when the input isn't
    ISO 8601, hinting the orchestrator to retry with a cleaner format.

    The orchestrator sees:
        - ``can_retry == True``
        - ``errorKind == TOOL_RUNTIME_RETRY``
        - ``additional_prompt_content`` — extra guidance the LLM can use to retry.
    """
    import datetime

    try:
        parsed = datetime.date.fromisoformat(date_str)
    except ValueError as e:
        raise RetryableToolError(
            message=f"Could not parse {date_str!r} as a date.",
            additional_prompt_content=(
                "Please retry with an ISO 8601 date string in YYYY-MM-DD form. "
                "Common valid examples: '2025-01-15', '2026-12-31'."
            ),
            developer_message=f"datetime.date.fromisoformat error: {e!s}",
        )
    return parsed.isoformat()


# -----------------------------------------------------------------------------
# 2. ContextRequiredToolError — needs a human / LLM input before retry
# -----------------------------------------------------------------------------


@app.tool
def lookup_user(
    email: Annotated[str, "User email to look up"],
) -> Annotated[dict, "The user record"]:
    """Look up a user by email. Raises ``ContextRequiredToolError`` when
    the input is ambiguous — the orchestrator MUST NOT blindly retry. The
    ``additional_prompt_content`` tells the orchestrator what's needed.

    The orchestrator sees:
        - ``can_retry == False``
        - ``errorKind == TOOL_RUNTIME_CONTEXT_REQUIRED``
        - ``additional_prompt_content`` — the (required) explanation that the
          orchestrator must surface to a human or to its planning step.
    """
    if "@" not in email or "." not in email.split("@")[-1]:
        raise ContextRequiredToolError(
            message=f"{email!r} doesn't look like a complete email address.",
            additional_prompt_content=(
                "Please ask the user to confirm their full email address, including the domain "
                "(e.g. `alice@example.com`). Do not retry with a guessed domain."
            ),
        )
    return {"email": email, "name": "Alice Example", "id": "u_1"}


# -----------------------------------------------------------------------------
# 3. UpstreamRateLimitError — 429 with retry_after_ms
# -----------------------------------------------------------------------------


@app.tool
def fetch_weather(
    city: Annotated[str, "The city to fetch weather for"],
) -> Annotated[dict, "Current weather (temperature, condition)"]:
    """Pretend to call an upstream weather API. About a third of the time the
    "upstream" rate-limits us; raises ``UpstreamRateLimitError`` with
    ``retry_after_ms`` so the orchestrator backs off correctly.

    The orchestrator sees:
        - ``can_retry == True``
        - ``errorKind == UPSTREAM_RUNTIME_RATE_LIMIT``
        - ``status_code == 429``
        - ``retry_after_ms`` — how long to wait.
    """
    # Fire roughly a third of the time. The previous formulation
    # ``random.random() + len(city) % 3 > 2.0`` was fully deterministic
    # because ``%`` binds tighter than ``+`` -- the ``len(city) % 3`` term
    # shifted the RNG range but the ``> 2.0`` check only fired when
    # ``len(city) % 3 == 2`` (and then essentially every call). Use an
    # explicit probability instead so the example actually demonstrates
    # the probabilistic retry-loop behavior its docstring advertises.
    if random.random() < 1 / 3:
        raise UpstreamRateLimitError(
            message="The weather provider rate-limited this request.",
            retry_after_ms=2000,
            developer_message=f"upstream=/api/weather?city={city} returned 429",
        )
    return {"city": city, "temperature_c": 18.5, "condition": "partly cloudy"}


# -----------------------------------------------------------------------------
# 4. UpstreamError with auth-failure status
# -----------------------------------------------------------------------------


@app.tool
def call_upstream_with_expired_token() -> Annotated[dict, "Unreachable"]:
    """Pretend an upstream API returned 403 because the token is revoked.
    Raises ``UpstreamError(status_code=403)``; the base class auto-sets
    ``errorKind == UPSTREAM_RUNTIME_AUTH_ERROR`` and ``can_retry == False``.
    """
    raise UpstreamError(
        message="The upstream API rejected the token.",
        status_code=403,
        developer_message="upstream /api/do-thing responded with 403 forbidden",
    )


# -----------------------------------------------------------------------------
# 5. UpstreamError with 5xx — auto-retryable
# -----------------------------------------------------------------------------


@app.tool
def call_flaky_upstream() -> Annotated[str, "Unreachable — always raises"]:
    """Pretend the upstream had a 502. The base ``UpstreamError`` sees a 5xx
    and auto-sets ``can_retry == True`` + ``errorKind ==
    UPSTREAM_RUNTIME_SERVER_ERROR``. No special subclass needed.
    """
    raise UpstreamError(
        message="Upstream returned HTTP 502 Bad Gateway.",
        status_code=502,
    )


# -----------------------------------------------------------------------------
# 6. Unhandled exception — the server wraps this into a fatal tool error
# -----------------------------------------------------------------------------


@app.tool
def mystery_bug(context: Context) -> str:
    """Raise a bare ``RuntimeError`` deliberately. The server's adapter chain
    wraps unhandled exceptions into a fatal tool error — the exception TYPE
    only lands in the agent-facing ``message`` while the full
    ``str(exception)`` is kept in ``developer_message`` (server logs only) to
    avoid leaking user input that tool authors may have interpolated into the
    exception text.
    """
    raise RuntimeError("surprise! this message won't reach the agent, only the logs")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    app.run(transport=transport, host="127.0.0.1", port=8000)

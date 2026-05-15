"""Regression guard: URLElicitationRequiredError (a Pydantic BaseModel) must
not be exported at the arcade_mcp_server top level.

The *Error suffix invites tool authors to ``raise URLElicitationRequiredError(...)``
which would fail at runtime because the class is a Pydantic model, not a
Python exception. The actual raisable type for "URL elicitation required" tool
errors is ``arcade_mcp_server.exceptions.ElicitationModeNotSupportedError``.

Canonical access to the wire-error model is::

    from arcade_mcp_server.types import URLElicitationRequiredError
"""


def test_url_elicitation_required_error_not_in_top_level_attrs():
    import arcade_mcp_server

    assert not hasattr(arcade_mcp_server, "URLElicitationRequiredError")


def test_url_elicitation_required_error_not_in_all():
    import arcade_mcp_server

    assert "URLElicitationRequiredError" not in arcade_mcp_server.__all__


def test_url_elicitation_required_error_still_accessible_via_types():
    from arcade_mcp_server.types import URLElicitationRequiredError

    assert URLElicitationRequiredError is not None
    err = URLElicitationRequiredError(message="x", data={})
    assert err.code == -32042

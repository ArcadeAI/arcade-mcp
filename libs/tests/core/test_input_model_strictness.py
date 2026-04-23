"""
TDD tests for three silent-drop bugs in auto-generated Pydantic input models.

Context (reported by francisco@arcade.dev, 2026-04-22):

  1. create_func_models() does NOT set ConfigDict(extra='forbid'), so Pydantic's
     default extra='ignore' silently drops unknown kwargs. A caller that sends
     `edit_requests` instead of `requests` sees no error — the tool runs with
     the real field missing and returns isError: false.

  2. Required parameters end up with default=None in the generated model because
     extract_python_param_info sets ParamInfo.default = None when the function
     signature has no explicit default, and create_func_models passes that None
     straight into Field(default=...). Pydantic treats the field as optional
     and never raises on missing. The "required" semantics only exist at the
     JSON-schema boundary in the MCP server, not at model-validation time.

  3. _TypedDictBaseModel (used by create_model_from_typeddict for nested
     request dicts) also has no extra='forbid'. So nested typos like
     {"txt": "x"} instead of {"text": "x"} are silently dropped even after
     the top-level extra='forbid' fix.

These tests assert the DESIRED behavior and are expected to FAIL on main
until the fix lands. They are the TDD red step.
"""

from typing import Annotated, Optional, get_args

import pytest
from arcade_core.catalog import ToolCatalog
from arcade_core.errors import ErrorKind
from arcade_core.executor import ToolExecutor
from arcade_core.schema import ToolContext
from arcade_tdk import tool
from pydantic import ValidationError
from typing_extensions import TypedDict


# ---------------------------------------------------------------------------
# Test fixtures: tools that exhibit the bug shapes
# ---------------------------------------------------------------------------


@tool
def required_only_tool(
    document_id: Annotated[str, "Document ID (required)"],
    text: Annotated[str, "Text to insert (required)"],
) -> Annotated[str, "result"]:
    """Tool with two required fields, no optional params, no nested types."""
    return f"{document_id}:{text}"


@tool
def required_and_optional_tool(
    document_id: Annotated[str, "Document ID (required)"],
    reasoning_effort: Annotated[Optional[str], "Reasoning level"] = "medium",
) -> Annotated[str, "result"]:
    """Tool with one required and one optional field."""
    return f"{document_id}:{reasoning_effort}"


class InsertTextRequest(TypedDict):
    """A nested request object — fields are required by default (total=True)."""

    text: str
    location: int


class StyleRequest(TypedDict, total=False):
    """A nested request object with all-optional fields (total=False)."""

    bold: bool
    italic: bool


@tool
def nested_required_tool(
    document_id: Annotated[str, "Document ID"],
    request: Annotated[InsertTextRequest, "An insert request"],
) -> Annotated[str, "result"]:
    """Tool that takes a nested TypedDict with required keys."""
    return "ok"


@tool
def nested_optional_tool(
    document_id: Annotated[str, "Document ID"],
    style: Annotated[StyleRequest, "Style options"],
) -> Annotated[str, "result"]:
    """Tool that takes a nested TypedDict with all-optional keys (total=False)."""
    return "ok"


catalog = ToolCatalog()
for fn in (
    required_only_tool,
    required_and_optional_tool,
    nested_required_tool,
    nested_optional_tool,
):
    catalog.add_tool(fn, "StrictToolkit")


def _materialized(fn):
    td = catalog.find_tool_by_func(fn)
    return catalog.get_tool(td.get_fully_qualified_name())


# ---------------------------------------------------------------------------
# Bug 1: Unknown top-level kwargs must be rejected (extra='forbid')
# ---------------------------------------------------------------------------


class TestUnknownTopLevelKwargsRejected:
    """The generated input model must raise on unknown kwargs."""

    def test_top_level_model_config_has_extra_forbid(self):
        """The generated input model's config must explicitly forbid extras."""
        mt = _materialized(required_only_tool)
        assert mt.input_model.model_config.get("extra") == "forbid"

    def test_unknown_kwarg_raises_validation_error(self):
        """Calling the input model with an unknown kwarg must raise."""
        mt = _materialized(required_only_tool)
        with pytest.raises(ValidationError) as exc_info:
            mt.input_model(document_id="d", text="t", banana=42)
        # At least one error should mention the offending key.
        assert any("banana" in str(err.get("loc", "")) for err in exc_info.value.errors()) or \
            any("banana" in err.get("msg", "") for err in exc_info.value.errors()) or \
            "banana" in str(exc_info.value)

    def test_misspelled_required_kwarg_raises_validation_error(self):
        """The motivating case: caller sent `edit_requests` instead of `text`.
        This must surface as a validation error, not silently drop the typo
        and run with text=None."""
        mt = _materialized(required_only_tool)
        with pytest.raises(ValidationError):
            # `txt` is a typo for `text` — must not be silently dropped.
            mt.input_model(document_id="d", txt="oops")

    def test_misspelled_optional_kwarg_raises_validation_error(self):
        """The most user-visible shape: typo on an optional field.
        Caller sent `reasoning_effort_level="high"` instead of `reasoning_effort`.
        Must raise, not silently run on the default."""
        mt = _materialized(required_and_optional_tool)
        with pytest.raises(ValidationError):
            mt.input_model(document_id="d", reasoning_effort_level="high")

    @pytest.mark.asyncio
    async def test_executor_surfaces_unknown_kwarg_as_tool_input_error(self):
        """End-to-end: ToolExecutor must return a BAD_INPUT_VALUE error, not a
        silent isError: false, when an unknown kwarg is passed."""
        mt = _materialized(required_only_tool)
        td = catalog.find_tool_by_func(required_only_tool)
        output = await ToolExecutor.run(
            func=required_only_tool,
            definition=td,
            input_model=mt.input_model,
            output_model=mt.output_model,
            context=ToolContext(),
            document_id="d",
            text="t",
            banana=42,  # unknown kwarg
        )
        assert output.error is not None, (
            "Unknown kwarg was silently accepted (isError: false). "
            "Expected ToolInputError."
        )
        assert output.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE


# ---------------------------------------------------------------------------
# Bug 2: Required parameters must actually be required at validation time
# ---------------------------------------------------------------------------


class TestRequiredParamsEnforced:
    """A parameter without an explicit default in the Python signature must
    be required at Pydantic validation time — not silently defaulted to None.
    """

    def test_required_field_has_no_default_in_model(self):
        """The Pydantic field metadata for a required param should not declare
        a default value."""
        mt = _materialized(required_only_tool)
        field = mt.input_model.model_fields["document_id"]
        # Pydantic marks fields without a default as `is_required() == True`.
        assert field.is_required(), (
            "document_id has no default in the Python signature but the "
            "generated model treats it as optional (default=None). This is "
            "the root of the silent-None bug."
        )

    def test_missing_required_field_raises_validation_error(self):
        """Instantiating the model without a required field must raise."""
        mt = _materialized(required_only_tool)
        with pytest.raises(ValidationError) as exc_info:
            mt.input_model()  # no args at all
        # Both required fields should be reported as missing.
        errors = exc_info.value.errors()
        missing_locs = {tuple(e["loc"]) for e in errors if e["type"] == "missing"}
        assert ("document_id",) in missing_locs
        assert ("text",) in missing_locs

    def test_partial_required_fields_raises(self):
        """Providing only some required fields must raise for the rest."""
        mt = _materialized(required_only_tool)
        with pytest.raises(ValidationError):
            mt.input_model(document_id="d")  # missing `text`

    def test_optional_field_still_accepts_omission(self):
        """Regression guard: fields with an explicit default must remain
        optional — the fix must not break genuinely optional params."""
        mt = _materialized(required_and_optional_tool)
        obj = mt.input_model(document_id="d")
        assert obj.document_id == "d"
        # `reasoning_effort` has default="medium" in the signature.
        assert obj.reasoning_effort == "medium"

    def test_explicit_none_default_is_not_required(self):
        """Regression for ACR finding: `def f(x: str = None)` has an explicit
        default of None, so it must not be flagged as required — even though
        `default is not None` is False. Uses the has_explicit_default flag."""

        @tool
        def tool_with_none_default(
            doc_id: Annotated[str, "doc id (required)"],
            hint: Annotated[str, "hint with explicit None default"] = None,  # type: ignore[assignment]
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(tool_with_none_default, "NoneDefaultTk")
        td = local_cat.find_tool_by_func(tool_with_none_default)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # hint has an explicit default of None — must be optional in the
        # Pydantic model.
        hint_field = mt_local.input_model.model_fields["hint"]
        assert not hint_field.is_required(), (
            "hint has `= None` in the signature, which is an explicit "
            "default. The model must treat it as optional."
        )

        # Omitting hint must work.
        obj = mt_local.input_model(doc_id="d")
        assert obj.doc_id == "d"
        assert obj.hint is None

        # And the wire schema must agree — `required=False` for hint.
        hint_param = next(p for p in td.input.parameters if p.name == "hint")
        assert hint_param.required is False

    @pytest.mark.asyncio
    async def test_executor_surfaces_missing_required_as_tool_input_error(self):
        """End-to-end: omitting a required field must produce a
        BAD_INPUT_VALUE error, not run the tool with the field as None."""
        mt = _materialized(required_only_tool)
        td = catalog.find_tool_by_func(required_only_tool)
        output = await ToolExecutor.run(
            func=required_only_tool,
            definition=td,
            input_model=mt.input_model,
            output_model=mt.output_model,
            context=ToolContext(),
            document_id="d",
            # `text` omitted
        )
        assert output.error is not None, (
            "Missing required field was silently accepted. "
            "Expected ToolInputError."
        )
        assert output.error.kind == ErrorKind.TOOL_RUNTIME_BAD_INPUT_VALUE
        # Error must mention which field was missing.
        assert "text" in (output.error.message or "")


# ---------------------------------------------------------------------------
# Bug 3: Nested TypedDict models must also forbid extras
# ---------------------------------------------------------------------------


class TestNestedTypedDictStrictness:
    """Unknown keys inside a nested TypedDict must also raise."""

    def test_nested_unknown_key_raises(self):
        """Typos inside a nested TypedDict must not be silently dropped."""
        mt = _materialized(nested_required_tool)
        with pytest.raises(ValidationError):
            # "txt" is a typo for "text" inside the nested TypedDict.
            mt.input_model(
                document_id="d",
                request={"text": "hi", "location": 0, "banana": 99},
            )

    def test_nested_unknown_key_in_total_false_typeddict_raises(self):
        """The most damaging shape: a total=False TypedDict with *only* typos
        currently validates as an empty dict. Must raise instead."""
        mt = _materialized(nested_optional_tool)
        with pytest.raises(ValidationError):
            mt.input_model(
                document_id="d",
                style={"bld": True, "itlc": False},  # both keys typo'd
            )

    def test_total_false_typeddict_does_not_inject_none_for_unset_fields(self):
        """Regression for ACR round 2 #2: before the @model_serializer fix,
        wrapping a total=False TypedDict caused outer model_dump() to emit
        {'italic': None} for fields the caller never provided. Tool functions
        would receive unexpected None values. The serializer must drop unset
        fields so the tool sees only what the caller sent."""

        class Style(TypedDict, total=False):
            bold: bool
            italic: bool

        @tool
        def styled(
            text: Annotated[str, "text"],
            style: Annotated[Style, "style options"],
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(styled, "StyleTk")
        td = local_cat.find_tool_by_func(styled)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # Caller sends only `bold`.
        inst = mt_local.input_model(text="t", style={"bold": True})
        dumped = inst.model_dump()
        # The executor calls outer.model_dump() and passes the result to the
        # tool function as kwargs. `italic` was never set by the caller and
        # must NOT appear in the dump.
        assert dumped == {"text": "t", "style": {"bold": True}}

    def test_same_typeddict_used_twice_produces_distinct_models(self):
        """Regression for ACR round 2 #4: two params of the same TypedDict
        class must produce distinct nested Pydantic models. Using only the
        TypedDict class name collided in Pydantic's $defs."""

        class Opts(TypedDict):
            value: int

        @tool
        def dual(
            first: Annotated[Opts, "first opts"],
            second: Annotated[Opts, "second opts"],
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(dual, "DualTk")
        td = local_cat.find_tool_by_func(dual)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        first_model = mt_local.input_model.model_fields["first"].annotation
        second_model = mt_local.input_model.model_fields["second"].annotation
        # The two generated Pydantic models must be distinct objects; if
        # they share a name, JSON-schema $defs collide and one overwrites
        # the other.
        assert first_model.__name__ != second_model.__name__

    def test_optional_typeddict_param_allows_none_and_rejects_typos(self):
        """Regression for ACR round 2 #1: Optional[TypedDict] with default=None
        must accept None (when omitted) and reject typos when the caller
        provides a dict. Before the Optional re-wrap fix, omission caused a
        ValidationError because the annotation was the unwrapped model type,
        which does not accept None."""

        class Req(TypedDict):
            text: str

        @tool
        def opt_td(
            req: Annotated[Optional[Req], "optional req"] = None,
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(opt_td, "OptTdTk2")
        td = local_cat.find_tool_by_func(opt_td)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # Omission → None (default).
        assert mt_local.input_model().model_dump() == {"req": None}
        # Explicit None must also validate (since annotation is Optional[...]).
        assert mt_local.input_model(req=None).model_dump() == {"req": None}
        # Valid dict works.
        assert mt_local.input_model(req={"text": "x"}).model_dump() == {"req": {"text": "x"}}
        # Typo must still raise.
        with pytest.raises(ValidationError):
            mt_local.input_model(req={"text": "x", "banana": 1})

    def test_optional_typeddict_param_rejects_unknown_keys(self):
        """Regression: Optional[TypedDict] params are unwrapped by
        extract_*_param_info before reaching _wrap_typeddicts_as_models,
        so the is_typeddict branch catches them and extra='forbid' applies."""

        class MyReq(TypedDict):
            text: str

        @tool
        def opt_td_tool(
            req: Annotated[Optional[MyReq], "optional typed dict"] = None,
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(opt_td_tool, "LocalTk")
        td = local_cat.find_tool_by_func(opt_td_tool)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # Omitting is fine (has default=None).
        assert mt_local.input_model().model_dump() == {"req": None}
        # Valid value works.
        assert mt_local.input_model(req={"text": "x"}).model_dump() == {"req": {"text": "x"}}
        # Typo inside the Optional[TypedDict] must raise.
        with pytest.raises(ValidationError):
            mt_local.input_model(req={"text": "x", "banana": 1})

    def test_typeddict_tool_output_allows_extra_keys(self):
        """Regression: output-side TypedDicts must NOT forbid extra keys —
        tools that return dicts from upstream APIs may include fields not
        declared in the TypedDict, and those must serialize without error."""

        class ReturnShape(TypedDict):
            status: str

        @tool
        def returns_td_with_extras() -> Annotated[ReturnShape, "result"]:
            """Returns a dict with an extra key not in the TypedDict schema."""
            return {"status": "ok", "extra_key_from_api": 42}  # type: ignore[typeddict-unknown-key]

        local_cat = ToolCatalog()
        local_cat.add_tool(returns_td_with_extras, "OutputTk")
        td = local_cat.find_tool_by_func(returns_td_with_extras)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # Output model must accept the extra key without raising.
        output = mt_local.output_model(
            result={"status": "ok", "extra_key_from_api": 42}
        )
        # Declared fields must be present.
        dumped = output.model_dump()
        assert dumped["result"]["status"] == "ok"

    def test_wrap_helper_handles_list_of_optional_typeddict(self):
        """Regression for ACR round 3 #1: _wrap_typeddicts_as_models must
        unwrap Optional[TypedDict] when it appears as the inner element of
        a list. (The public catalog currently rejects list[Optional[TD]]
        at wire-type generation, so this guards the helper directly — if
        the outer type ever becomes supported, strictness will already work.)"""
        from arcade_core.catalog import _wrap_typeddicts_as_models

        class Item(TypedDict):
            value: int

        wrapped = _wrap_typeddicts_as_models(list[Optional[Item]], "TestPrefix")
        # Inner element type must have been wrapped to a strict Pydantic model.
        (inner_type,) = get_args(wrapped)
        # Optional[WrappedModel] — pull out the non-None arg.
        non_none_args = [a for a in get_args(inner_type) if a is not type(None)]
        assert len(non_none_args) == 1
        wrapped_model = non_none_args[0]
        assert hasattr(wrapped_model, "model_config")
        assert wrapped_model.model_config.get("extra") == "forbid"
        # Sanity: instantiating with an extra key raises.
        with pytest.raises(ValidationError):
            wrapped_model(value=1, banana=2)

    def test_list_of_typeddict_inside_parent_typeddict_unknown_key_raises(self):
        """Regression for ACR round 3 #5: list[TypedDict] declared as a field
        of a parent TypedDict must also forbid extras in strict mode — the
        strictness must propagate into list fields inside the parent."""

        class Inner(TypedDict):
            text: str

        class Outer(TypedDict):
            items: list[Inner]

        @tool
        def nested_list_td(
            payload: Annotated[Outer, "outer container"],
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(nested_list_td, "NestedListTdTk")
        td = local_cat.find_tool_by_func(nested_list_td)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # Valid call works.
        assert mt_local.input_model(
            payload={"items": [{"text": "hi"}]}
        ).model_dump() == {"payload": {"items": [{"text": "hi"}]}}
        # Typo inside a list element must raise.
        with pytest.raises(ValidationError):
            mt_local.input_model(payload={"items": [{"text": "hi", "banana": 1}]})

    def test_bare_none_default_on_non_optional_annotation_accepts_omission_and_none(
        self,
    ):
        """Regression for ACR round 3 #2: `def f(x: str = None)` is legal
        Python; the Pydantic model must treat it as Optional[str] so both
        omission and explicit None validate cleanly."""

        @tool
        def bare_none_default(
            doc_id: Annotated[str, "doc id"],
            hint: Annotated[str, "hint"] = None,  # type: ignore[assignment]
        ) -> Annotated[str, "r"]:
            """test"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(bare_none_default, "BareNoneTk")
        td = local_cat.find_tool_by_func(bare_none_default)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        # Omission works.
        assert mt_local.input_model(doc_id="d").hint is None
        # Explicit None also validates.
        assert mt_local.input_model(doc_id="d", hint=None).hint is None
        # Real string still works.
        assert mt_local.input_model(doc_id="d", hint="h").hint == "h"

    def test_nested_list_of_typeddict_unknown_key_raises(self):
        """Unknown keys inside a list-of-TypedDict parameter must raise too.
        (This is the exact edit_document / requests: list[EditRequest] shape.)"""

        class EditReq(TypedDict):
            text: str
            location: int

        @tool
        def edit_doc(
            document_id: Annotated[str, "doc id"],
            requests: Annotated[list[EditReq], "edit requests"],
        ) -> Annotated[str, "r"]:
            """edit"""
            return "ok"

        local_cat = ToolCatalog()
        local_cat.add_tool(edit_doc, "LocalToolkit")
        td = local_cat.find_tool_by_func(edit_doc)
        mt_local = local_cat.get_tool(td.get_fully_qualified_name())

        with pytest.raises(ValidationError):
            mt_local.input_model(
                document_id="d",
                requests=[{"text": "x", "location": 0, "banana": 1}],
            )

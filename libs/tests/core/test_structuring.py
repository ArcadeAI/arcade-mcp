"""Tests for arcade_core.structuring — typed response structuring for tool composition."""

import pytest
from pydantic import BaseModel

from arcade_core.errors import ToolResponseExtractionError
from arcade_core.structuring import (
    OnMissing,
    _make_nullable,
    _to_snake_case,
    _try_direct,
    _try_heuristic,
    structure_output,
)


class UserProfile(BaseModel):
    name: str
    email: str
    age: int


class OptionalProfile(BaseModel):
    name: str
    email: str | None = None
    age: int = 0


# ---------- Tier 1: Direct validation ----------


class TestTryDirect:
    def test_exact_match(self) -> None:
        data = {"name": "Alice", "email": "a@b.com", "age": 30}
        result = _try_direct(UserProfile, data)
        assert result is not None
        assert result.name == "Alice"
        assert result.age == 30

    def test_extra_fields_ignored(self) -> None:
        data = {"name": "Alice", "email": "a@b.com", "age": 30, "extra": "ignored"}
        result = _try_direct(UserProfile, data)
        assert result is not None
        assert result.name == "Alice"

    def test_missing_required_field(self) -> None:
        data = {"name": "Alice"}
        result = _try_direct(UserProfile, data)
        assert result is None

    def test_non_dict_input(self) -> None:
        result = _try_direct(UserProfile, "not a dict")
        assert result is None

    def test_type_coercion(self) -> None:
        data = {"name": "Alice", "email": "a@b.com", "age": "30"}
        result = _try_direct(UserProfile, data)
        assert result is not None
        assert result.age == 30


# ---------- Tier 2: Heuristic mapping ----------


class TestTryHeuristic:
    def test_unwrap_result_wrapper(self) -> None:
        data = {"result": {"name": "Alice", "email": "a@b.com", "age": 30}}
        result = _try_heuristic(UserProfile, data)
        assert result is not None
        assert result.name == "Alice"

    def test_camel_case_to_snake_case(self) -> None:
        class CamelModel(BaseModel):
            user_name: str
            email_address: str

        data = {"userName": "Alice", "emailAddress": "a@b.com"}
        result = _try_heuristic(CamelModel, data)
        assert result is not None
        assert result.user_name == "Alice"

    def test_flatten_single_key_nested(self) -> None:
        data = {"data": {"name": "Alice", "email": "a@b.com", "age": 30}}
        result = _try_heuristic(UserProfile, data)
        assert result is not None
        assert result.name == "Alice"

    def test_unwrap_result_then_normalize(self) -> None:
        class SnakeModel(BaseModel):
            user_name: str

        data = {"result": {"UserName": "Alice"}}
        result = _try_heuristic(SnakeModel, data)
        assert result is not None
        assert result.user_name == "Alice"

    def test_no_match(self) -> None:
        data = {"completely": "different", "structure": True}
        result = _try_heuristic(UserProfile, data)
        assert result is None

    def test_non_dict_input(self) -> None:
        result = _try_heuristic(UserProfile, [1, 2, 3])
        assert result is None


# ---------- structure_output (combined tiers) ----------


class TestStructureOutput:
    def test_tier1_direct(self) -> None:
        data = {"name": "Alice", "email": "a@b.com", "age": 30}
        result = structure_output(UserProfile, data)
        assert result.name == "Alice"

    def test_tier2_fallback(self) -> None:
        data = {"result": {"name": "Alice", "email": "a@b.com", "age": 30}}
        result = structure_output(UserProfile, data)
        assert result.name == "Alice"

    def test_raises_on_failure(self) -> None:
        data = {"unrelated": "data"}
        with pytest.raises(ToolResponseExtractionError):
            structure_output(UserProfile, data)

    def test_allow_null_makes_fields_optional(self) -> None:
        data = {"name": "Alice"}  # missing email and age
        result = structure_output(UserProfile, data, on_missing=OnMissing.ALLOW_NULL)
        assert result.name == "Alice"
        assert result.email is None  # type: ignore[comparison-overlap]
        assert result.age is None  # type: ignore[comparison-overlap]

    def test_fail_mode_raises_on_missing_fields(self) -> None:
        data = {"name": "Alice"}
        with pytest.raises(ToolResponseExtractionError):
            structure_output(UserProfile, data, on_missing=OnMissing.FAIL)


# ---------- _make_nullable ----------


class TestMakeNullable:
    def test_required_fields_become_optional(self) -> None:
        NullableProfile = _make_nullable(UserProfile)
        instance = NullableProfile(name="Alice")  # type: ignore[call-arg]
        assert instance.name == "Alice"
        assert instance.email is None  # type: ignore[comparison-overlap]
        assert instance.age is None  # type: ignore[comparison-overlap]

    def test_already_optional_fields_unchanged(self) -> None:
        NullableOptional = _make_nullable(OptionalProfile)
        instance = NullableOptional(name="Alice")
        assert instance.email is None
        assert instance.age == 0  # default preserved for non-required

    def test_caching(self) -> None:
        result1 = _make_nullable(UserProfile)
        result2 = _make_nullable(UserProfile)
        assert result1 is result2


# ---------- _to_snake_case ----------


class TestToSnakeCase:
    def test_camel_case(self) -> None:
        assert _to_snake_case("userName") == "user_name"

    def test_pascal_case(self) -> None:
        assert _to_snake_case("UserName") == "user_name"

    def test_consecutive_caps(self) -> None:
        assert _to_snake_case("HTTPResponse") == "http_response"

    def test_already_snake(self) -> None:
        assert _to_snake_case("user_name") == "user_name"

    def test_single_word(self) -> None:
        assert _to_snake_case("name") == "name"

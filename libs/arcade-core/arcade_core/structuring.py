"""Typed response structuring for tool composition.

Provides a tiered strategy to map arbitrary tool output into a user-defined Pydantic model:
  Tier 1 - Direct Pydantic validation (zero cost)
  Tier 2 - Heuristic field mapping (deterministic, no LLM)

When both tiers fail, callers (e.g. Tools.execute) can fall back to LLM extraction.
"""

import re
from enum import Enum
from typing import Any, TypeVar

from pydantic import BaseModel, Field, ValidationError, create_model

from arcade_core.errors import ToolResponseExtractionError

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

T = TypeVar("T", bound=BaseModel)

# Cache for nullable model variants to avoid re-creating per call
_nullable_model_cache: dict[type[BaseModel], type[BaseModel]] = {}


class OnMissing(str, Enum):
    """Controls behavior when a field can't be mapped from tool response to target model."""

    FAIL = "fail"
    ALLOW_NULL = "allow_null"


class ExecuteOptions(TypedDict, total=False):
    """Options for context.tools.execute()."""

    on_missing: OnMissing
    """What to do when a field can't be mapped (default: FAIL)."""

    timeout_seconds: float
    """Total timeout across all retries (default: 60)."""

    max_retries: int
    """Max retry attempts for transient failures (default: 3)."""

    retry_delay_seconds: float
    """Delay between retries (default: 1.0)."""


EXECUTE_DEFAULTS: ExecuteOptions = {
    "on_missing": OnMissing.FAIL,
    "timeout_seconds": 60.0,
    "max_retries": 3,
    "retry_delay_seconds": 1.0,
}


def structure_output(
    model_class: type[T],
    raw_data: Any,
    on_missing: OnMissing = OnMissing.FAIL,
) -> T:
    """Attempt to structure raw tool output into the target Pydantic model.

    Tries direct validation (Tier 1) then heuristic mapping (Tier 2).
    Raises ToolResponseExtractionError if both tiers fail.
    """
    effective_model = (
        _make_nullable(model_class) if on_missing == OnMissing.ALLOW_NULL else model_class
    )

    # Tier 1: Direct validation
    result = _try_direct(effective_model, raw_data)
    if result is not None:
        return result  # type: ignore[return-value]

    # Tier 2: Heuristic mapping
    result = _try_heuristic(effective_model, raw_data)
    if result is not None:
        return result  # type: ignore[return-value]

    raise ToolResponseExtractionError(
        "Could not structure tool response into target type. "
        f"Target: {model_class.__name__}, Data: {_truncate(raw_data)}",
        developer_message=(
            f"Both direct validation and heuristic mapping failed for "
            f"{model_class.__name__}. Raw data type: {type(raw_data).__name__}."
        ),
    )


def _try_direct(model_class: type[T], data: Any) -> T | None:
    """Tier 1: Attempt direct Pydantic validation."""
    if not isinstance(data, dict):
        return None
    try:
        return model_class.model_validate(data)
    except ValidationError:
        return None


def _try_heuristic(model_class: type[T], data: Any) -> T | None:
    """Tier 2: Attempt heuristic field mapping strategies."""
    if not isinstance(data, dict):
        return None

    candidates: list[dict[str, Any]] = []

    # Strategy 1: Unwrap {"result": ...} wrapper
    if len(data) == 1 and "result" in data and isinstance(data["result"], dict):
        candidates.append(data["result"])

    # Strategy 2: Snake_case key normalization
    normalized = {_to_snake_case(k): v for k, v in data.items()}
    if normalized != data:
        candidates.append(normalized)

    # Strategy 3: Flatten single-key nested dict
    if len(data) == 1:
        sole_value = next(iter(data.values()))
        if isinstance(sole_value, dict):
            candidates.append(sole_value)

    # Strategy 4: Unwrap {"result": ...} then normalize keys
    if len(data) == 1 and "result" in data and isinstance(data["result"], dict):
        inner = data["result"]
        inner_normalized = {_to_snake_case(k): v for k, v in inner.items()}
        if inner_normalized != inner:
            candidates.append(inner_normalized)

    for candidate in candidates:
        try:
            return model_class.model_validate(candidate)
        except ValidationError:
            continue

    return None


def _make_nullable(model_class: type[T]) -> type[T]:
    """Create a variant of model_class where all required fields become Optional with None default.

    Results are cached by model class identity.
    """
    if model_class in _nullable_model_cache:
        return _nullable_model_cache[model_class]  # type: ignore[return-value]

    field_definitions: dict[str, Any] = {}
    for name, field_info in model_class.model_fields.items():
        if field_info.is_required():
            field_definitions[name] = (
                field_info.annotation | None,  # type: ignore[operator]
                Field(default=None, description=field_info.description),
            )
        else:
            field_definitions[name] = (field_info.annotation, field_info)

    nullable_model: type[T] = create_model(  # type: ignore[assignment]
        f"{model_class.__name__}Nullable",
        __base__=model_class,
        **field_definitions,
    )
    _nullable_model_cache[model_class] = nullable_model
    return nullable_model


def _to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    # Insert underscore before uppercase letters that follow lowercase letters or digits
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    # Insert underscore between consecutive uppercase letters followed by lowercase
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()


def _truncate(data: Any, max_len: int = 200) -> str:
    """Truncate data repr for error messages."""
    s = repr(data)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s

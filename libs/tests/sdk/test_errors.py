"""Tests for arcade_evals.errors module."""

import pytest
from arcade_evals.errors import EvalError, WeightError


class TestEvalError:
    """Tests for EvalError base class."""

    def test_eval_error_is_exception(self) -> None:
        """Test that EvalError is an Exception subclass."""
        assert issubclass(EvalError, Exception)

    def test_eval_error_can_be_raised(self) -> None:
        """Test that EvalError can be raised and caught."""
        with pytest.raises(EvalError) as exc_info:
            raise EvalError("test error")
        assert str(exc_info.value) == "test error"

    def test_eval_error_with_no_message(self) -> None:
        """Test that EvalError can be raised without a message."""
        with pytest.raises(EvalError):
            raise EvalError()


class TestWeightError:
    """Tests for WeightError class."""

    def test_weight_error_is_eval_error_subclass(self) -> None:
        """Test that WeightError is a subclass of EvalError."""
        assert issubclass(WeightError, EvalError)

    def test_weight_error_is_exception(self) -> None:
        """Test that WeightError is an Exception subclass."""
        assert issubclass(WeightError, Exception)

    def test_weight_error_can_be_raised(self) -> None:
        """Test that WeightError can be raised and caught."""
        with pytest.raises(WeightError) as exc_info:
            raise WeightError("invalid weight")
        assert str(exc_info.value) == "invalid weight"

    def test_weight_error_caught_as_eval_error(self) -> None:
        """Test that WeightError can be caught as EvalError."""
        with pytest.raises(EvalError):
            raise WeightError("weight constraint violated")

    def test_weight_error_caught_as_exception(self) -> None:
        """Test that WeightError can be caught as generic Exception."""
        with pytest.raises(Exception):
            raise WeightError("test")


class TestErrorImports:
    """Tests for error class imports."""

    def test_import_from_errors_module(self) -> None:
        """Test that errors can be imported from arcade_evals.errors."""
        from arcade_evals.errors import EvalError, WeightError

        assert EvalError is not None
        assert WeightError is not None

    def test_errors_in_module_all(self) -> None:
        """Test that errors are in __all__."""
        from arcade_evals import errors

        assert "EvalError" in errors.__all__
        assert "WeightError" in errors.__all__

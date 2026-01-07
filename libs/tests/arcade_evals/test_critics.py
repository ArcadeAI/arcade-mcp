"""Tests for critic evaluation logic."""

import pytest
from arcade_evals.critic import (
    BinaryCritic,
    NoneCritic,
    NumericCritic,
    SimilarityCritic,
)
from arcade_evals.errors import WeightError
from arcade_evals.weights import FuzzyWeight

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestNoneCritic:
    """Tests for NoneCritic placeholder."""

    def test_none_critic_always_returns_zero_score(self) -> None:
        """Test that NoneCritic always returns score 0."""
        critic = NoneCritic(critic_field="test", weight=0.0)
        result = critic.evaluate("expected", "actual")

        assert result["score"] == 0.0
        assert result["match"] is None
        assert result["is_criticized"] is False

    def test_none_critic_has_marker_attribute(self) -> None:
        """Test that NoneCritic has _is_placeholder marker."""
        critic = NoneCritic(critic_field="test", weight=0.0)
        assert hasattr(critic, "_is_placeholder")
        assert critic._is_placeholder is True


class TestBinaryCritic:
    """Tests for BinaryCritic exact equality comparisons."""

    def test_binary_critic_exact_match_returns_full_weight(self) -> None:
        """Test that exact match returns full weight as score."""
        critic = BinaryCritic(critic_field="name", weight=1.0)
        result = critic.evaluate("Alice", "Alice")

        assert result["match"] is True
        assert result["score"] == 1.0

    def test_binary_critic_mismatch_returns_zero_score(self) -> None:
        """Test that mismatch returns score 0."""
        critic = BinaryCritic(critic_field="name", weight=1.0)
        result = critic.evaluate("Alice", "Bob")

        assert result["match"] is False
        assert result["score"] == 0.0

    def test_binary_critic_partial_weight(self) -> None:
        """Test that partial weight is respected."""
        critic = BinaryCritic(critic_field="name", weight=0.5)
        result = critic.evaluate("Alice", "Alice")

        assert result["match"] is True
        assert result["score"] == 0.5

    def test_binary_critic_cast_actual_to_expected_type(self) -> None:
        """Test that actual value is cast to expected type."""
        critic = BinaryCritic(critic_field="count", weight=1.0)
        # Expect int, get string
        result = critic.evaluate(42, "42")

        assert result["match"] is True
        assert result["score"] == 1.0

    def test_binary_critic_none_handling(self) -> None:
        """Test None value handling."""
        critic = BinaryCritic(critic_field="optional", weight=1.0)

        # None == None
        result = critic.evaluate(None, None)
        assert result["match"] is True

        # None != value
        result = critic.evaluate(None, "value")
        assert result["match"] is False

        # String "None" is cast to None
        result = critic.evaluate(None, "None")
        assert result["match"] is True


class TestNumericCritic:
    """Tests for NumericCritic fuzzy numeric comparisons."""

    def test_numeric_critic_exact_match_returns_full_score(self) -> None:
        """Test that exact match returns full weight as score."""
        critic = NumericCritic(
            critic_field="temperature", weight=1.0, value_range=(0.0, 100.0)
        )
        result = critic.evaluate(50.0, 50.0)

        assert result["match"] is True
        assert result["score"] == 1.0

    def test_numeric_critic_close_values_high_score(self) -> None:
        """Test that close values get high scores."""
        critic = NumericCritic(
            critic_field="temperature",
            weight=1.0,
            value_range=(0.0, 100.0),
            match_threshold=0.9,
        )
        # Within 10% of range
        result = critic.evaluate(50.0, 55.0)

        assert result["score"] >= 0.9
        assert result["match"] is True

    def test_numeric_critic_far_values_low_score(self) -> None:
        """Test that far values get low scores."""
        critic = NumericCritic(
            critic_field="temperature", weight=1.0, value_range=(0.0, 100.0)
        )
        # Far apart
        result = critic.evaluate(10.0, 90.0)

        assert result["score"] < 0.3
        assert result["match"] is False

    def test_numeric_critic_respects_match_threshold(self) -> None:
        """Test that match_threshold correctly determines match status."""
        critic = NumericCritic(
            critic_field="value",
            weight=1.0,
            value_range=(0.0, 100.0),
            match_threshold=0.95,
        )
        # Score is 0.9 (within 10% of range) - below 0.95 threshold
        result = critic.evaluate(50.0, 60.0)

        assert result["score"] == 0.9
        assert result["match"] is False  # Below threshold

    def test_numeric_critic_at_range_boundaries(self) -> None:
        """Test evaluation at range boundaries."""
        critic = NumericCritic(critic_field="value", weight=1.0, value_range=(0.0, 100.0))

        # At min boundary
        result = critic.evaluate(0.0, 0.0)
        assert result["match"] is True
        assert result["score"] == 1.0

        # At max boundary
        result = critic.evaluate(100.0, 100.0)
        assert result["match"] is True
        assert result["score"] == 1.0

    def test_numeric_critic_outside_range_handled(self) -> None:
        """Test that values outside range are handled (extrapolation)."""
        critic = NumericCritic(critic_field="value", weight=1.0, value_range=(0.0, 100.0))

        # Actual is outside range
        result = critic.evaluate(50.0, 150.0)
        # Normalized difference will be large, score will be low or negative
        assert result["score"] <= 0.0

    def test_numeric_critic_partial_weight(self) -> None:
        """Test that partial weight is respected."""
        critic = NumericCritic(critic_field="value", weight=0.5, value_range=(0.0, 100.0))
        result = critic.evaluate(50.0, 50.0)

        assert result["score"] == 0.5  # Perfect match * 0.5 weight

    def test_numeric_critic_invalid_range_raises_error(self) -> None:
        """Test that invalid range (min >= max) raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value_range"):
            NumericCritic(critic_field="value", weight=1.0, value_range=(100.0, 0.0))

        with pytest.raises(ValueError, match="Invalid value_range"):
            NumericCritic(critic_field="value", weight=1.0, value_range=(50.0, 50.0))


class TestSimilarityCritic:
    """Tests for SimilarityCritic text similarity comparisons."""

    def test_similarity_critic_exact_match_returns_full_score(self) -> None:
        """Test that exact string match returns full weight as score."""
        critic = SimilarityCritic(critic_field="query", weight=1.0)
        result = critic.evaluate("search for cats", "search for cats")

        assert result["match"] is True
        assert result["score"] == 1.0

    def test_similarity_critic_very_similar_strings_high_score(self) -> None:
        """Test that very similar strings get high scores."""
        critic = SimilarityCritic(
            critic_field="query", weight=1.0, similarity_threshold=0.5
        )
        result = critic.evaluate("search for cats", "search for cat")

        # Very similar (just plural difference)
        assert result["score"] >= 0.5
        assert result["match"] is True

    def test_similarity_critic_different_strings_low_score(self) -> None:
        """Test that different strings get low scores."""
        critic = SimilarityCritic(critic_field="query", weight=1.0)
        result = critic.evaluate("search for cats", "weather in Paris")

        assert result["score"] < 0.3
        assert result["match"] is False

    def test_similarity_critic_respects_threshold(self) -> None:
        """Test that similarity_threshold correctly determines match status."""
        critic = SimilarityCritic(
            critic_field="query", weight=1.0, similarity_threshold=0.9
        )
        result = critic.evaluate("hello world", "hello there")

        # Similarity might be ~0.6-0.7 - below 0.9 threshold
        assert result["match"] is False

    def test_similarity_critic_partial_weight(self) -> None:
        """Test that partial weight is respected."""
        critic = SimilarityCritic(critic_field="query", weight=0.5)
        result = critic.evaluate("test", "test")

        assert result["score"] == 0.5  # Perfect match * 0.5 weight

    def test_similarity_critic_handles_empty_strings(self) -> None:
        """Test handling of empty strings."""
        critic = SimilarityCritic(critic_field="query", weight=1.0)

        # Empty == Empty
        result = critic.evaluate("", "")
        # TF-IDF can't compute similarity for empty strings - should handle gracefully
        assert "score" in result
        assert "match" in result

    def test_similarity_critic_converts_lists_to_strings(self) -> None:
        """Test that lists are converted to space-separated strings."""
        critic = SimilarityCritic(critic_field="tags", weight=1.0)

        # Lists should be joined with spaces
        result = critic.evaluate(
            ["python", "security"], ["python", "security", "best-practices"]
        )

        # Should be comparing "python security" vs "python security best-practices"
        assert "score" in result
        assert result["score"] > 0.5  # Should have some similarity

    def test_similarity_critic_converts_non_strings(self) -> None:
        """Test that non-string values are converted to strings."""
        critic = SimilarityCritic(critic_field="value", weight=1.0)

        # Numbers to strings
        result = critic.evaluate(12345, 12345)
        assert result["match"] is True
        assert result["score"] == 1.0

        # Dict to string
        result = critic.evaluate({"key": "value"}, {"key": "value"})
        assert result["score"] > 0.8  # Should match after stringification

    def test_similarity_critic_unsupported_metric_raises_error(self) -> None:
        """Test that unsupported metric raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported similarity metric"):
            SimilarityCritic(critic_field="query", weight=1.0, metric="hamming")

    def test_similarity_critic_requires_sklearn(self) -> None:
        """Test that SimilarityCritic raises ImportError without sklearn."""
        from unittest.mock import patch

        critic = SimilarityCritic(critic_field="query", weight=1.0)

        # Patch the import inside evaluate() to simulate missing sklearn
        with patch.dict("sys.modules", {"sklearn.feature_extraction.text": None}):
            with pytest.raises(ImportError, match="pip install.*arcade-evals"):
                critic.evaluate("test", "test2")


class TestCriticWeights:
    """Tests for critic weight validation and FuzzyWeight support."""

    def test_negative_weight_raises_error(self) -> None:
        """Test that negative weights raise WeightError."""
        with pytest.raises(WeightError, match="non-negative"):
            BinaryCritic(critic_field="test", weight=-0.5)

    def test_fuzzy_weight_skips_validation(self) -> None:
        """Test that FuzzyWeight skips validation (normalized later)."""
        # Should not raise even though FuzzyWeight.CRITICAL might be > 1
        critic = BinaryCritic(critic_field="test", weight=FuzzyWeight.CRITICAL)
        assert critic.weight == FuzzyWeight.CRITICAL

    def test_zero_weight_allowed(self) -> None:
        """Test that zero weight is allowed."""
        critic = BinaryCritic(critic_field="test", weight=0.0)
        assert critic.weight == 0.0

    def test_large_weight_allowed(self) -> None:
        """Test that weights > 1.0 are allowed (softmax normalization handles)."""
        critic = BinaryCritic(critic_field="test", weight=5.0)
        assert critic.weight == 5.0

    def test_resolved_weight_returns_float(self) -> None:
        """Test that resolved_weight property returns float."""
        critic = BinaryCritic(critic_field="test", weight=0.8)
        assert isinstance(critic.resolved_weight, float)
        assert critic.resolved_weight == 0.8

    def test_resolved_weight_with_fuzzy_weight(self) -> None:
        """Test resolved_weight with FuzzyWeight enum."""
        critic = BinaryCritic(critic_field="test", weight=FuzzyWeight.HIGH)
        # FuzzyWeight.HIGH has value 5 (int)
        assert isinstance(critic.resolved_weight, (int, float))
        assert critic.resolved_weight > 0.0


class TestCriticEdgeCases:
    """Tests for edge cases in critic evaluation."""

    def test_binary_critic_with_complex_types(self) -> None:
        """Test BinaryCritic with dicts and lists."""
        critic = BinaryCritic(critic_field="config", weight=1.0)

        # Dict comparison
        result = critic.evaluate({"a": 1, "b": 2}, {"a": 1, "b": 2})
        assert result["match"] is True

        # List comparison
        result = critic.evaluate([1, 2, 3], [1, 2, 3])
        assert result["match"] is True

        # Nested structures
        result = critic.evaluate({"list": [1, 2]}, {"list": [1, 2]})
        assert result["match"] is True

    def test_numeric_critic_with_string_numbers(self) -> None:
        """Test NumericCritic casts string numbers to float."""
        critic = NumericCritic(critic_field="value", weight=1.0, value_range=(0.0, 100.0))
        result = critic.evaluate("50.0", "50.0")

        assert result["match"] is True
        assert result["score"] == 1.0

    def test_similarity_critic_case_insensitive(self) -> None:
        """Test that SimilarityCritic handles case differences."""
        critic = SimilarityCritic(critic_field="query", weight=1.0)
        result = critic.evaluate("Hello World", "hello world")

        # Should still have high similarity (lowercase conversion happens in TF-IDF)
        assert result["score"] > 0.9
        assert result["match"] is True

    def test_similarity_critic_punctuation_differences(self) -> None:
        """Test SimilarityCritic with punctuation variations."""
        critic = SimilarityCritic(
            critic_field="query", weight=1.0, similarity_threshold=0.8
        )
        result = critic.evaluate("search for cats!", "search for cats")

        # Should have very high similarity despite punctuation
        assert result["score"] >= 0.8
        assert result["match"] is True

    def test_numeric_critic_with_negative_ranges(self) -> None:
        """Test NumericCritic with negative value ranges."""
        critic = NumericCritic(
            critic_field="temperature", weight=1.0, value_range=(-50.0, 50.0)
        )
        result = critic.evaluate(-10.0, -10.0)

        assert result["match"] is True
        assert result["score"] == 1.0

        # Test scoring across negative range
        result = critic.evaluate(-50.0, 50.0)
        assert result["score"] == 0.0  # Maximum difference

    def test_numeric_critic_floating_point_precision(self) -> None:
        """Test NumericCritic handles floating point precision correctly."""
        critic = NumericCritic(critic_field="value", weight=1.0, value_range=(0.0, 1.0))
        result = critic.evaluate(0.333333, 0.333334)

        # Very close values should have very high score
        assert result["score"] > 0.999
        assert result["match"] is True

from datetime import timedelta

import pytest
import pytz
from arcade_evals import (
    BinaryCritic,
    DatetimeCritic,
    NoneCritic,
    NumericCritic,
    SimilarityCritic,
)
from arcade_evals.errors import WeightError
from dateutil import parser

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


# Test NoneCritic initialization
@pytest.mark.parametrize("weight, expected_weight", [(0.0, 0.0), (0.5, 0.0)])
def test_none_critic_initialization(weight, expected_weight):
    field_name = "my_field"

    critic = NoneCritic(weight=weight, critic_field=field_name)
    assert critic.weight == expected_weight
    assert critic.critic_field == field_name


# Test NoneCritic.evaluate()
def test_none_critic_evaluate():
    critic = NoneCritic(critic_field="my_field")
    result = critic.evaluate(expected="expected_value", actual="actual_value")
    assert result["match"] is None
    assert result["score"] == 0.0
    assert result["is_criticized"] is False


# Test BinaryCritic.evaluate()
@pytest.mark.parametrize(
    "expected, actual, weight, expected_match, expected_score",
    [
        ("value", "value", 1.0, True, 1.0),
        ("value", "different", 1.0, False, 0.0),
        (10, 10, 0.5, True, 0.5),
        (10, 20, 0.5, False, 0.0),
    ],
)
def test_binary_critic_evaluate(expected, actual, weight, expected_match, expected_score):
    """
    Test the BinaryCritic's evaluate method to ensure it correctly computes
    the match and score based on expected and actual values.
    """
    critic = BinaryCritic(critic_field="test_field", weight=weight)
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert result["score"] == expected_score


# Test NumericCritic.evaluate()
@pytest.mark.parametrize(
    "expected, actual, value_range, weight, match_threshold, expected_match, expected_score",
    [
        (5, 5, (0, 10), 1.0, 0.8, True, 1.0),
        (5, 6, (0, 10), 1.0, 0.8, True, 0.9),
        (0, 10, (0, 10), 1.0, 0.8, False, 0.0),
        (2, 8, (0, 10), 1.0, 0.5, False, 0.4),
        (50, 60, (0, 100), 0.5, 0.9, True, 0.45),
    ],
)
def test_numeric_critic_evaluate(
    expected, actual, value_range, weight, match_threshold, expected_match, expected_score
):
    """
    Test the NumericCritic's evaluate method to ensure it calculates
    the correct score based on the proportion of the difference between
    expected and actual values within a specified range.
    """
    critic = NumericCritic(
        critic_field="number",
        weight=weight,
        value_range=value_range,
        match_threshold=match_threshold,
    )
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert pytest.approx(result["score"], 0.01) == expected_score


# Test SimilarityCritic.evaluate()
@pytest.mark.parametrize(
    "expected, actual, weight, similarity_threshold, expected_match, min_expected_score",
    [
        ("hello world", "hello world", 1.0, 0.8, True, 1.0),
        ("hello world", "hello", 1.0, 0.8, False, 0.0),
        ("The quick brown fox", "The quick brown fox jumps over the lazy dog", 1.0, 0.5, True, 0.5),
        ("data science", "machine learning", 0.5, 0.3, False, 0.0),
    ],
)
def test_similarity_critic_evaluate(
    expected, actual, weight, similarity_threshold, expected_match, min_expected_score
):
    """
    Test the SimilarityCritic's evaluate method to ensure it computes
    the similarity score between expected and actual strings and determines
    the match correctly based on the similarity threshold.
    """
    critic = SimilarityCritic(
        critic_field="text",
        weight=weight,
        similarity_threshold=similarity_threshold,
    )
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert result["score"] >= min_expected_score
    assert result["score"] >= 0.0
    assert result["score"] <= weight + 1e-6  # Allow a small epsilon for floating-point comparison


# Test SimilarityCritic with non-string inputs (lists, dicts, etc.)
# This is critical because sklearn's TfidfVectorizer calls .lower() which fails on non-strings
@pytest.mark.parametrize(
    "expected, actual, expected_match",
    [
        # Lists with same items - should be similar
        (["team1", "team2"], ["team1", "team2"], True),
        # Lists with different items - should not match
        (["team1", "team2"], ["team3", "team4"], False),
        # Mixed string and list - can still compare
        ("team1 team2", ["team1", "team2"], True),
        # Single item lists
        (["engineering"], ["engineering"], True),
        # Dicts converted to strings
        ({"key": "value"}, {"key": "value"}, True),
    ],
)
def test_similarity_critic_non_string_inputs(expected, actual, expected_match):
    """
    Test that SimilarityCritic handles non-string inputs (lists, dicts)
    by converting them to strings before comparison.
    """
    critic = SimilarityCritic(
        critic_field="teams_to_add",
        weight=1.0,
        similarity_threshold=0.8,
    )
    result = critic.evaluate(expected=expected, actual=actual)
    assert result["match"] == expected_match
    assert result["score"] >= 0.0


# Additional edge case tests for SimilarityCritic non-string handling
class TestSimilarityCriticNonStringEdgeCases:
    """
    Extended tests for SimilarityCritic handling of non-string inputs.
    These tests ensure robustness when tool arguments are lists, numbers, or other types.
    """

    def test_empty_lists_produce_empty_strings(self):
        """Empty lists should be converted to empty strings and match each other."""
        critic = SimilarityCritic(critic_field="tags", weight=1.0, similarity_threshold=0.0)
        result = critic.evaluate(expected=[], actual=[])
        assert result["match"] == True  # noqa: E712 - numpy bool comparison
        assert result["score"] == 1.0

    def test_empty_vs_non_empty_list(self):
        """Empty list vs non-empty list should not match."""
        critic = SimilarityCritic(critic_field="tags", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=[], actual=["item"])
        assert result["match"] == False  # noqa: E712

    def test_lists_with_numbers_only(self):
        """Lists containing only numbers fall back to exact match (TF-IDF filters digits)."""
        critic = SimilarityCritic(critic_field="ids", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=[1, 2, 3], actual=[1, 2, 3])
        assert result["match"] == True  # noqa: E712 - exact match fallback
        assert result["score"] > 0

    def test_lists_with_mixed_types(self):
        """Lists with mixed types (strings and numbers) should work."""
        critic = SimilarityCritic(critic_field="mixed", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=["user", 123, "admin"], actual=["user", 123, "admin"])
        assert result["match"] == True  # noqa: E712

    def test_integer_inputs(self):
        """Integer inputs fall back to exact string match."""
        critic = SimilarityCritic(critic_field="count", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=42, actual=42)
        assert result["match"] == True  # noqa: E712

    def test_integer_inputs_different(self):
        """Different integers should not match."""
        critic = SimilarityCritic(critic_field="count", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=42, actual=99)
        assert result["match"] == False  # noqa: E712

    def test_float_inputs(self):
        """Float inputs fall back to exact string match."""
        critic = SimilarityCritic(critic_field="price", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=19.99, actual=19.99)
        assert result["match"] == True  # noqa: E712

    def test_boolean_inputs(self):
        """Boolean inputs fall back to exact string match."""
        critic = SimilarityCritic(critic_field="enabled", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=True, actual=True)
        assert result["match"] == True  # noqa: E712

    def test_boolean_inputs_different(self):
        """Different booleans should not match."""
        critic = SimilarityCritic(critic_field="enabled", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=True, actual=False)
        assert result["match"] == False  # noqa: E712

    def test_list_order_similarity(self):
        """Same items in different order are similar (TF-IDF is order-agnostic)."""
        critic = SimilarityCritic(critic_field="teams", weight=1.0, similarity_threshold=0.9)
        result = critic.evaluate(
            expected=["alpha", "beta", "gamma"], actual=["gamma", "beta", "alpha"]
        )
        assert result["match"] == True  # noqa: E712

    def test_nested_list_exact_match(self):
        """Nested lists fall back to exact match (special chars filtered by TF-IDF)."""
        critic = SimilarityCritic(critic_field="nested", weight=1.0, similarity_threshold=0.5)
        result = critic.evaluate(expected=[["a", "b"], ["c", "d"]], actual=[["a", "b"], ["c", "d"]])
        assert result["match"] == True  # noqa: E712

    def test_unicode_in_lists(self):
        """Lists with unicode strings should work correctly."""
        critic = SimilarityCritic(critic_field="names", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(
            expected=["café", "naïve", "résumé"], actual=["café", "naïve", "résumé"]
        )
        assert result["match"] == True  # noqa: E712

    def test_none_converted_to_string(self):
        """None values fall back to exact string match."""
        critic = SimilarityCritic(critic_field="optional", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=None, actual=None)
        assert result["match"] == True  # noqa: E712

    def test_none_vs_value(self):
        """None vs actual value should not match."""
        critic = SimilarityCritic(critic_field="optional", weight=1.0, similarity_threshold=0.8)
        result = critic.evaluate(expected=None, actual="value")
        assert result["match"] == False  # noqa: E712


# Test that WeightError is raised for negative critic weights
@pytest.mark.parametrize(
    "critic_class, weight",
    [
        (BinaryCritic, -0.1),
        (NumericCritic, -0.5),
        (SimilarityCritic, -0.3),
    ],
)
def test_critic_invalid_weight(critic_class, weight):
    """
    Test that initializing a critic with a negative weight raises a WeightError.
    """
    with pytest.raises(WeightError):
        if critic_class == NumericCritic:
            critic_class(critic_field="test_field", weight=weight, value_range=(0, 1))
        elif critic_class == SimilarityCritic:
            critic_class(critic_field="test_field", weight=weight)
        else:
            critic_class(critic_field="test_field", weight=weight)


# Test that weights > 1.0 are now allowed (softmax normalization handles them)
@pytest.mark.parametrize(
    "critic_class, weight",
    [
        (BinaryCritic, 1.5),
        (BinaryCritic, 3.0),
        (NumericCritic, 2.0),
        (SimilarityCritic, 5.0),
    ],
)
def test_critic_allows_weights_above_one(critic_class, weight):
    """
    Test that weights > 1.0 are allowed (softmax normalization handles them).
    """
    if critic_class == NumericCritic:
        critic = critic_class(critic_field="test_field", weight=weight, value_range=(0, 1))
    elif critic_class == SimilarityCritic:
        critic = critic_class(critic_field="test_field", weight=weight)
    else:
        critic = critic_class(critic_field="test_field", weight=weight)
    assert critic.weight == weight


# Test NumericCritic with invalid value range
def test_numeric_critic_invalid_range():
    """
    Test that initializing a NumericCritic with an invalid value range raises a ValueError.
    """
    with pytest.raises(ValueError):
        NumericCritic(critic_field="number", weight=1.0, value_range=(10, 0))  # Invalid range


# Test SimilarityCritic with unsupported metric
def test_similarity_critic_unsupported_metric():
    """
    Test that initializing a SimilarityCritic with an unsupported metric raises a ValueError.
    """
    with pytest.raises(ValueError):
        SimilarityCritic(critic_field="text", weight=1.0, metric="unsupported_metric")


# Test DatetimeCritic
# Parameterized tests for DatetimeCritic with various datetime formats and default timezones
@pytest.mark.parametrize(
    "critic_params, expected, actual, expected_match, expected_score",
    [
        # Test with time component and timezone
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26T12:00:00-07:00",
            "2024-09-26T12:00:00-07:00",
            True,
            1.0,
        ),
        # Test without time component (dates only)
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26",
            "2024-09-26",
            True,
            1.0,
        ),
        # Test with and without timezone (assumes UTC)
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26T12:00:00Z",
            "2024-09-26T12:00:00",
            True,
            1.0,
        ),
        # Test naive datetimes
        (
            {"critic_field": "start_datetime", "weight": 1.0},
            "2024-09-26T12:00:00",
            "2024-09-26T12:00:00",
            True,
            1.0,
        ),
    ],
)
def test_datetime_critic_basic(critic_params, expected, actual, expected_match, expected_score):
    """
    Test DatetimeCritic with various datetime formats and default timezones.
    """
    critic = DatetimeCritic(**critic_params)
    result = critic.evaluate(expected, actual)
    assert result["match"] == expected_match
    assert result["score"] == expected_score


# Parameterized tests for DatetimeCritic's handling of tolerances and max differences
@pytest.mark.parametrize(
    "critic_params, expected, actual, expected_match, expected_score_func",
    [
        # Test time difference within tolerance
        (
            {"critic_field": "start_datetime", "weight": 1.0, "tolerance": timedelta(seconds=60)},
            "2024-09-26T12:00:00",
            "2024-09-26T12:00:30",
            True,
            lambda critic: critic.weight,
        ),
        # Test time difference outside tolerance but within max_difference
        (
            {
                "critic_field": "start_datetime",
                "weight": 1.0,
                "tolerance": timedelta(seconds=60),
                "max_difference": timedelta(minutes=5),
            },
            "2024-09-26T12:00:00",
            "2024-09-26T12:04:00",
            False,
            lambda critic: critic.weight * (1 - (240 / 300)),
        ),
        # Test time difference exceeds max_difference
        (
            {
                "critic_field": "start_datetime",
                "weight": 1.0,
                "max_difference": timedelta(minutes=5),
            },
            "2024-09-26T12:00:00",
            "2024-09-26T12:10:00",
            False,
            lambda critic: 0.0,
        ),
    ],
)
def test_datetime_critic_tolerances(
    critic_params, expected, actual, expected_match, expected_score_func
):
    """
    Test DatetimeCritic's handling of tolerances and max differences.
    """
    critic = DatetimeCritic(**critic_params)
    result = critic.evaluate(expected, actual)
    assert result["match"] == expected_match
    expected_score = expected_score_func(critic)
    assert pytest.approx(result["score"], abs=1e-6) == expected_score


def test_datetime_critic_naive_and_timezone_aware():
    """
    Test DatetimeCritic when comparing naive and timezone-aware datetimes.
    """
    critic = DatetimeCritic(critic_field="start_datetime", weight=1.0)
    expected = "2024-09-26T12:00:00Z"
    actual = "2024-09-26T07:00:00"
    result = critic.evaluate(expected, actual)
    assert result["match"] is False

    # Compute expected score based on time difference
    expected_dt = parser.parse(expected)
    actual_dt = parser.parse(actual)
    if actual_dt.tzinfo is None:
        actual_dt = pytz.utc.localize(actual_dt)
    if expected_dt.tzinfo is None:
        expected_dt = pytz.utc.localize(expected_dt)

    time_diff_seconds = abs((expected_dt - actual_dt).total_seconds())
    if time_diff_seconds <= critic.tolerance.total_seconds():
        expected_score = critic.weight
    elif time_diff_seconds >= critic.max_difference.total_seconds():
        expected_score = 0.0
    else:
        ratio = 1 - (time_diff_seconds / critic.max_difference.total_seconds())
        expected_score = critic.weight * ratio

    assert pytest.approx(result["score"], abs=1e-6) == expected_score

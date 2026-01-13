"""Tests for capture mode formatters."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from arcade_cli.formatters import (
    CAPTURE_FORMATTERS,
    CaptureHtmlFormatter,
    CaptureJsonFormatter,
    CaptureMarkdownFormatter,
    CaptureTextFormatter,
    get_capture_formatter,
)

if TYPE_CHECKING:
    from arcade_evals import CaptureResult


def _create_mock_capture_result(
    suite_name: str = "TestSuite",
    model: str = "gpt-4o",
    provider: str = "openai",
    cases: list[dict] | None = None,
) -> CaptureResult:
    """Create a mock CaptureResult for testing."""
    if cases is None:
        cases = [
            {
                "case_name": "test_case_1",
                "user_message": "What's the weather?",
                "tool_calls": [
                    {"name": "GetWeather", "args": {"city": "NYC", "units": "celsius"}},
                ],
                "system_message": "You are helpful",
                "additional_messages": [{"role": "user", "content": "Hi"}],
            }
        ]

    # Create mock capture result
    capture = MagicMock()
    capture.suite_name = suite_name
    capture.model = model
    capture.provider = provider

    # Create mock captured cases
    captured_cases = []
    for case_data in cases:
        case = MagicMock()
        case.case_name = case_data["case_name"]
        case.user_message = case_data["user_message"]
        case.system_message = case_data.get("system_message")
        case.additional_messages = case_data.get("additional_messages", [])
        # Explicitly set track_name to None unless specified (avoids MagicMock)
        case.track_name = case_data.get("track_name")

        # Create mock tool calls
        tool_calls = []
        for tc_data in case_data.get("tool_calls", []):
            tc = MagicMock()
            tc.name = tc_data["name"]
            tc.args = tc_data.get("args", {})
            tool_calls.append(tc)
        case.tool_calls = tool_calls

        captured_cases.append(case)

    capture.captured_cases = captured_cases

    # Mock to_dict method
    def to_dict(include_context: bool = False) -> dict:
        result = {
            "suite_name": capture.suite_name,
            "model": capture.model,
            "provider": capture.provider,
            "captured_cases": [],
        }
        for case in captured_cases:
            case_dict = {
                "case_name": case.case_name,
                "user_message": case.user_message,
                "tool_calls": [{"name": tc.name, "args": tc.args} for tc in case.tool_calls],
            }
            if include_context:
                case_dict["system_message"] = case.system_message
                case_dict["additional_messages"] = case.additional_messages
            result["captured_cases"].append(case_dict)
        return result

    capture.to_dict = to_dict

    return capture


class TestGetCaptureFormatter:
    """Tests for get_capture_formatter function."""

    def test_get_json_formatter(self) -> None:
        """Test getting JSON formatter."""
        formatter = get_capture_formatter("json")
        assert isinstance(formatter, CaptureJsonFormatter)

    def test_get_txt_formatter(self) -> None:
        """Test getting text formatter."""
        formatter = get_capture_formatter("txt")
        assert isinstance(formatter, CaptureTextFormatter)

    def test_get_md_formatter(self) -> None:
        """Test getting markdown formatter."""
        formatter = get_capture_formatter("md")
        assert isinstance(formatter, CaptureMarkdownFormatter)

    def test_get_html_formatter(self) -> None:
        """Test getting HTML formatter."""
        formatter = get_capture_formatter("html")
        assert isinstance(formatter, CaptureHtmlFormatter)

    def test_case_insensitive(self) -> None:
        """Test that format names are case insensitive."""
        assert isinstance(get_capture_formatter("JSON"), CaptureJsonFormatter)
        assert isinstance(get_capture_formatter("TXT"), CaptureTextFormatter)
        assert isinstance(get_capture_formatter("MD"), CaptureMarkdownFormatter)
        assert isinstance(get_capture_formatter("HTML"), CaptureHtmlFormatter)

    def test_unsupported_format_raises(self) -> None:
        """Test that unsupported formats raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported capture format 'xlsx'"):
            get_capture_formatter("xlsx")

    def test_close_match_suggestion(self) -> None:
        """Test that close matches are suggested."""
        with pytest.raises(ValueError, match="Did you mean 'json'"):
            get_capture_formatter("jsn")


class TestCaptureJsonFormatter:
    """Tests for CaptureJsonFormatter."""

    def test_file_extension(self) -> None:
        """Test file extension is json."""
        formatter = CaptureJsonFormatter()
        assert formatter.file_extension == "json"

    def test_format_basic(self) -> None:
        """Test basic JSON formatting."""
        formatter = CaptureJsonFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])
        parsed = json.loads(output)

        assert "captures" in parsed
        assert len(parsed["captures"]) == 1
        assert parsed["captures"][0]["suite_name"] == "TestSuite"
        assert parsed["captures"][0]["model"] == "gpt-4o"

    def test_format_includes_tool_calls(self) -> None:
        """Test that tool calls are included."""
        formatter = CaptureJsonFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])
        parsed = json.loads(output)

        case = parsed["captures"][0]["captured_cases"][0]
        assert len(case["tool_calls"]) == 1
        assert case["tool_calls"][0]["name"] == "GetWeather"
        assert case["tool_calls"][0]["args"]["city"] == "NYC"

    def test_format_with_context(self) -> None:
        """Test formatting with context included."""
        formatter = CaptureJsonFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture], include_context=True)
        parsed = json.loads(output)

        case = parsed["captures"][0]["captured_cases"][0]
        assert "system_message" in case
        assert case["system_message"] == "You are helpful"

    def test_format_without_context(self) -> None:
        """Test formatting without context (default)."""
        formatter = CaptureJsonFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture], include_context=False)
        parsed = json.loads(output)

        case = parsed["captures"][0]["captured_cases"][0]
        assert "system_message" not in case


class TestCaptureTextFormatter:
    """Tests for CaptureTextFormatter."""

    def test_file_extension(self) -> None:
        """Test file extension is txt."""
        formatter = CaptureTextFormatter()
        assert formatter.file_extension == "txt"

    def test_format_contains_suite_info(self) -> None:
        """Test that suite info is in output."""
        formatter = CaptureTextFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "Suite: TestSuite" in output
        assert "Model: gpt-4o" in output
        assert "Provider: openai" in output

    def test_format_contains_case_info(self) -> None:
        """Test that case info is in output."""
        formatter = CaptureTextFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "Case: test_case_1" in output
        assert "User Message: What's the weather?" in output

    def test_format_contains_tool_calls(self) -> None:
        """Test that tool calls are in output."""
        formatter = CaptureTextFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "GetWeather" in output
        assert "city: NYC" in output

    def test_format_contains_summary(self) -> None:
        """Test that summary is in output."""
        formatter = CaptureTextFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "Summary: 1 tool calls across 1 cases" in output

    def test_format_with_context(self) -> None:
        """Test formatting with context."""
        formatter = CaptureTextFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture], include_context=True)

        assert "System Message: You are helpful" in output


class TestCaptureMarkdownFormatter:
    """Tests for CaptureMarkdownFormatter."""

    def test_file_extension(self) -> None:
        """Test file extension is md."""
        formatter = CaptureMarkdownFormatter()
        assert formatter.file_extension == "md"

    def test_format_has_heading(self) -> None:
        """Test that markdown has main heading."""
        formatter = CaptureMarkdownFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "# Capture Results" in output

    def test_format_has_suite_heading(self) -> None:
        """Test that suite has heading."""
        formatter = CaptureMarkdownFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "## TestSuite" in output

    def test_format_has_case_heading(self) -> None:
        """Test that case has heading."""
        formatter = CaptureMarkdownFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "### Case: test_case_1" in output

    def test_format_has_code_blocks(self) -> None:
        """Test that tool args are in code blocks."""
        formatter = CaptureMarkdownFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "```json" in output
        assert '"city": "NYC"' in output
        assert "```" in output

    def test_format_has_summary(self) -> None:
        """Test that summary is present."""
        formatter = CaptureMarkdownFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "## Summary" in output
        assert "**Total Cases:** 1" in output
        assert "**Total Tool Calls:** 1" in output


class TestCaptureHtmlFormatter:
    """Tests for CaptureHtmlFormatter."""

    def test_file_extension(self) -> None:
        """Test file extension is html."""
        formatter = CaptureHtmlFormatter()
        assert formatter.file_extension == "html"

    def test_format_is_valid_html(self) -> None:
        """Test that output is valid HTML structure."""
        formatter = CaptureHtmlFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "<!DOCTYPE html>" in output
        assert "<html" in output
        assert "</html>" in output
        assert "<head>" in output
        assert "</head>" in output
        assert "<body>" in output
        assert "</body>" in output

    def test_format_contains_styles(self) -> None:
        """Test that CSS styles are included."""
        formatter = CaptureHtmlFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "<style>" in output
        assert "</style>" in output

    def test_format_contains_suite_info(self) -> None:
        """Test that suite info is in output."""
        formatter = CaptureHtmlFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "TestSuite" in output
        assert "gpt-4o" in output

    def test_format_contains_tool_calls(self) -> None:
        """Test that tool calls are in output."""
        formatter = CaptureHtmlFormatter()
        capture = _create_mock_capture_result()

        output = formatter.format([capture])

        assert "GetWeather" in output
        # Args should be HTML-escaped
        assert "&quot;city&quot;" in output or '"city"' in output

    def test_format_escapes_html(self) -> None:
        """Test that HTML special characters are escaped."""
        formatter = CaptureHtmlFormatter()
        capture = _create_mock_capture_result(
            cases=[
                {
                    "case_name": "Test <script>",
                    "user_message": "Hello & Goodbye",
                    "tool_calls": [],
                }
            ]
        )

        output = formatter.format([capture])

        # Angle brackets should be escaped
        assert "&lt;script&gt;" in output
        # Ampersand should be escaped
        assert "&amp;" in output


class TestCaptureFormattersRegistry:
    """Tests for the CAPTURE_FORMATTERS registry."""

    def test_all_formats_registered(self) -> None:
        """Test that all expected formats are registered."""
        assert "json" in CAPTURE_FORMATTERS
        assert "txt" in CAPTURE_FORMATTERS
        assert "md" in CAPTURE_FORMATTERS
        assert "html" in CAPTURE_FORMATTERS

    def test_registry_returns_correct_types(self) -> None:
        """Test that registry maps to correct formatter types."""
        assert CAPTURE_FORMATTERS["json"] == CaptureJsonFormatter
        assert CAPTURE_FORMATTERS["txt"] == CaptureTextFormatter
        assert CAPTURE_FORMATTERS["md"] == CaptureMarkdownFormatter
        assert CAPTURE_FORMATTERS["html"] == CaptureHtmlFormatter


class TestCaptureFormatterEdgeCases:
    """Tests for edge cases in capture formatting."""

    def test_empty_captures_list(self) -> None:
        """Test formatting with empty captures list."""
        for formatter in [
            CaptureJsonFormatter(),
            CaptureTextFormatter(),
            CaptureMarkdownFormatter(),
            CaptureHtmlFormatter(),
        ]:
            output = formatter.format([])
            assert output  # Should produce some output

    def test_case_with_no_tool_calls(self) -> None:
        """Test formatting a case with no tool calls."""
        capture = _create_mock_capture_result(
            cases=[
                {
                    "case_name": "empty_case",
                    "user_message": "Hello",
                    "tool_calls": [],
                }
            ]
        )

        for formatter in [
            CaptureJsonFormatter(),
            CaptureTextFormatter(),
            CaptureMarkdownFormatter(),
            CaptureHtmlFormatter(),
        ]:
            output = formatter.format([capture])
            assert output  # Should produce some output

    def test_multiple_captures(self) -> None:
        """Test formatting multiple capture results."""
        capture1 = _create_mock_capture_result(suite_name="Suite1", model="gpt-4o")
        capture2 = _create_mock_capture_result(suite_name="Suite2", model="claude-3")

        for formatter in [
            CaptureJsonFormatter(),
            CaptureTextFormatter(),
            CaptureMarkdownFormatter(),
            CaptureHtmlFormatter(),
        ]:
            output = formatter.format([capture1, capture2])
            assert "Suite1" in output
            assert "Suite2" in output


class TestMultiModelCaptureFormatting:
    """Tests for multi-model capture formatting."""

    def test_markdown_multi_model_detection(self) -> None:
        """Test that markdown formatter detects multi-model and groups by case."""
        # Same suite, same case, different models
        capture1 = _create_mock_capture_result(
            suite_name="TestSuite",
            model="gpt-4o",
            cases=[
                {
                    "case_name": "shared_case",
                    "user_message": "What's the weather?",
                    "tool_calls": [{"name": "GetWeather", "args": {"city": "NYC"}}],
                }
            ],
        )
        capture2 = _create_mock_capture_result(
            suite_name="TestSuite",
            model="gpt-4-turbo",
            cases=[
                {
                    "case_name": "shared_case",
                    "user_message": "What's the weather?",
                    "tool_calls": [{"name": "GetWeather", "args": {"city": "New York"}}],
                }
            ],
        )

        formatter = CaptureMarkdownFormatter()
        output = formatter.format([capture1, capture2])

        # Should detect multi-model and show comparison
        assert "Multi-Model" in output
        assert "gpt-4o" in output
        assert "gpt-4-turbo" in output
        assert "shared_case" in output
        # Should show models comparison table
        assert "| Model |" in output

    def test_markdown_single_model_format(self) -> None:
        """Test that single-model captures use the simple format."""
        capture = _create_mock_capture_result(suite_name="Suite", model="gpt-4o")

        formatter = CaptureMarkdownFormatter()
        output = formatter.format([capture])

        # Should NOT have multi-model header
        assert "Multi-Model" not in output
        # Should have regular header
        assert "# Capture Results" in output

    def test_multi_model_tool_calls_grouped(self) -> None:
        """Test that tool calls are grouped by case in multi-model output."""
        capture1 = _create_mock_capture_result(
            suite_name="Suite",
            model="model-a",
            cases=[
                {
                    "case_name": "case1",
                    "user_message": "Do something",
                    "tool_calls": [{"name": "ToolA", "args": {"x": 1}}],
                }
            ],
        )
        capture2 = _create_mock_capture_result(
            suite_name="Suite",
            model="model-b",
            cases=[
                {
                    "case_name": "case1",
                    "user_message": "Do something",
                    "tool_calls": [{"name": "ToolA", "args": {"x": 2}}],
                }
            ],
        )

        formatter = CaptureMarkdownFormatter()
        output = formatter.format([capture1, capture2])

        # Both models should appear for the same case
        assert "model-a" in output
        assert "model-b" in output
        # Tool details should be in collapsible sections
        assert "<details>" in output


class TestMultiModelHelpers:
    """Tests for multi-model helper functions in base.py."""

    def test_is_multi_model_capture_true(self) -> None:
        """Test detection of multiple models in captures."""
        from arcade_cli.formatters.base import is_multi_model_capture

        capture1 = _create_mock_capture_result(model="gpt-4o")
        capture2 = _create_mock_capture_result(model="gpt-4-turbo")

        assert is_multi_model_capture([capture1, capture2]) is True

    def test_is_multi_model_capture_false(self) -> None:
        """Test single model detection."""
        from arcade_cli.formatters.base import is_multi_model_capture

        capture1 = _create_mock_capture_result(model="gpt-4o")
        capture2 = _create_mock_capture_result(model="gpt-4o")

        assert is_multi_model_capture([capture1, capture2]) is False

    def test_group_captures_by_case(self) -> None:
        """Test grouping captures by case for comparison."""
        from arcade_cli.formatters.base import group_captures_by_case

        capture1 = _create_mock_capture_result(
            suite_name="Suite",
            model="model-a",
            cases=[
                {"case_name": "case1", "user_message": "msg1", "tool_calls": []},
                {"case_name": "case2", "user_message": "msg2", "tool_calls": []},
            ],
        )
        capture2 = _create_mock_capture_result(
            suite_name="Suite",
            model="model-b",
            cases=[
                {"case_name": "case1", "user_message": "msg1", "tool_calls": []},
            ],
        )

        grouped, model_order = group_captures_by_case([capture1, capture2])

        # Check structure
        assert "Suite" in grouped
        assert "case1" in grouped["Suite"]
        assert "case2" in grouped["Suite"]

        # Check model order
        assert model_order == ["model-a", "model-b"]

        # Check case1 has both models
        assert "model-a" in grouped["Suite"]["case1"]["models"]
        assert "model-b" in grouped["Suite"]["case1"]["models"]

        # Check case2 only has model-a
        assert "model-a" in grouped["Suite"]["case2"]["models"]
        assert "model-b" not in grouped["Suite"]["case2"]["models"]


class TestMultiModelTextCaptureFormatter:
    """Tests for multi-model text capture formatting."""

    def test_text_multi_model_output(self) -> None:
        """Should produce multi-model text output."""
        capture1 = _create_mock_capture_result(
            suite_name="TestSuite", model="gpt-4o", cases=[
                {"case_name": "case1", "user_message": "Hi", "tool_calls": [{"name": "Tool1", "args": {}}]}
            ]
        )
        capture2 = _create_mock_capture_result(
            suite_name="TestSuite", model="gpt-4-turbo", cases=[
                {"case_name": "case1", "user_message": "Hi", "tool_calls": [{"name": "Tool2", "args": {}}]}
            ]
        )

        formatter = CaptureTextFormatter()
        output = formatter.format([capture1, capture2])

        # Should have multi-model header
        assert "MULTI-MODEL CAPTURE RESULTS" in output

        # Should list both models
        assert "gpt-4o" in output
        assert "gpt-4-turbo" in output

        # Should show case name
        assert "case1" in output

    def test_text_single_model_regular_format(self) -> None:
        """Should use regular format for single model."""
        capture = _create_mock_capture_result(model="gpt-4o")

        formatter = CaptureTextFormatter()
        output = formatter.format([capture])

        # Should NOT have multi-model header
        assert "MULTI-MODEL CAPTURE RESULTS" not in output


class TestMultiModelHtmlCaptureFormatter:
    """Tests for multi-model HTML capture formatting."""

    def test_html_multi_model_output(self) -> None:
        """Should produce multi-model HTML output."""
        capture1 = _create_mock_capture_result(
            suite_name="TestSuite", model="gpt-4o", cases=[
                {"case_name": "case1", "user_message": "Hi", "tool_calls": [{"name": "Tool1", "args": {}}]}
            ]
        )
        capture2 = _create_mock_capture_result(
            suite_name="TestSuite", model="gpt-4-turbo", cases=[
                {"case_name": "case1", "user_message": "Hi", "tool_calls": [{"name": "Tool2", "args": {}}]}
            ]
        )

        formatter = CaptureHtmlFormatter()
        output = formatter.format([capture1, capture2])

        # Should have multi-model title
        assert "Multi-Model Capture Results" in output

        # Should list models
        assert "gpt-4o" in output
        assert "gpt-4-turbo" in output

        # Should have model panels
        assert "model-panel" in output

    def test_html_single_model_regular_format(self) -> None:
        """Should use regular format for single model."""
        capture = _create_mock_capture_result(model="gpt-4o")

        formatter = CaptureHtmlFormatter()
        output = formatter.format([capture])

        # Should NOT have multi-model title
        assert "Multi-Model Capture Results" not in output


class TestMultiModelJsonCaptureFormatter:
    """Tests for multi-model JSON capture formatting."""

    def test_json_multi_model_output(self) -> None:
        """Should produce structured multi-model JSON."""
        capture1 = _create_mock_capture_result(
            suite_name="TestSuite", model="gpt-4o", cases=[
                {"case_name": "case1", "user_message": "Hi", "tool_calls": [{"name": "Tool1", "args": {}}]}
            ]
        )
        capture2 = _create_mock_capture_result(
            suite_name="TestSuite", model="gpt-4-turbo", cases=[
                {"case_name": "case1", "user_message": "Hi", "tool_calls": [{"name": "Tool2", "args": {}}]}
            ]
        )

        formatter = CaptureJsonFormatter()
        output = formatter.format([capture1, capture2])

        data = json.loads(output)

        # Should have multi-model type
        assert data["type"] == "multi_model_capture"

        # Should have models list
        assert "models" in data
        assert "gpt-4o" in data["models"]
        assert "gpt-4-turbo" in data["models"]

        # Should have grouped_by_case structure
        assert "grouped_by_case" in data
        assert "TestSuite" in data["grouped_by_case"]
        assert "case1" in data["grouped_by_case"]["TestSuite"]

    def test_json_single_model_regular_format(self) -> None:
        """Should use regular format for single model."""
        capture = _create_mock_capture_result(model="gpt-4o")

        formatter = CaptureJsonFormatter()
        output = formatter.format([capture])

        data = json.loads(output)

        # Should have capture type
        assert data["type"] == "capture"
        # Should not have grouped_by_case
        assert "grouped_by_case" not in data


# =============================================================================
# CAPTURE WITH TRACKS TESTS
# =============================================================================


def _create_mock_capture_with_tracks(
    suite_name: str = "ComparativeSuite",
    model: str = "gpt-4o",
    provider: str = "openai",
) -> CaptureResult:
    """Create a mock CaptureResult with track information for testing."""
    cases = [
        {
            "case_name": "weather_case",
            "user_message": "What's the weather in NYC?",
            "tool_calls": [
                {"name": "get_weather_v1", "args": {"city": "NYC"}},
            ],
            "track_name": "track_a",
            "system_message": "You are a weather assistant",
            "additional_messages": [],
        },
        {
            "case_name": "weather_case",
            "user_message": "What's the weather in NYC?",
            "tool_calls": [
                {"name": "fetch_weather", "args": {"location": "NYC"}},
            ],
            "track_name": "track_b",
            "system_message": "You are a weather assistant",
            "additional_messages": [],
        },
        {
            "case_name": "regular_case",
            "user_message": "Hello world",
            "tool_calls": [
                {"name": "greet", "args": {}},
            ],
            "track_name": None,  # Regular case without track
            "system_message": None,
            "additional_messages": [],
        },
    ]

    capture = MagicMock()
    capture.suite_name = suite_name
    capture.model = model
    capture.provider = provider

    captured_cases = []
    for case_data in cases:
        mock_case = MagicMock()
        mock_case.case_name = case_data["case_name"]
        mock_case.user_message = case_data["user_message"]
        mock_case.system_message = case_data["system_message"]
        mock_case.additional_messages = case_data["additional_messages"]
        mock_case.track_name = case_data["track_name"]

        mock_tool_calls = []
        for tc in case_data["tool_calls"]:
            mock_tc = MagicMock()
            mock_tc.name = tc["name"]
            mock_tc.args = tc["args"]
            mock_tool_calls.append(mock_tc)
        mock_case.tool_calls = mock_tool_calls

        captured_cases.append(mock_case)

    capture.captured_cases = captured_cases

    def to_dict(include_context: bool = False) -> dict:
        result = {
            "suite_name": capture.suite_name,
            "model": capture.model,
            "provider": capture.provider,
            "captured_cases": [],
        }
        for case in capture.captured_cases:
            case_dict = {
                "case_name": case.case_name,
                "user_message": case.user_message,
                "tool_calls": [{"name": tc.name, "args": tc.args} for tc in case.tool_calls],
            }
            if case.track_name:
                case_dict["track_name"] = case.track_name
            if include_context:
                case_dict["system_message"] = case.system_message
                case_dict["additional_messages"] = case.additional_messages
            result["captured_cases"].append(case_dict)
        return result

    capture.to_dict = to_dict
    return capture


class TestCaptureWithTracks:
    """Tests for capture mode with track support."""

    def test_captured_case_has_track_name_field(self) -> None:
        """CapturedCase should have track_name field."""
        from arcade_evals.capture import CapturedCase

        # Create a captured case with track
        case = CapturedCase(
            case_name="test_case",
            user_message="test",
            tool_calls=[],
            track_name="my_track",
        )
        assert case.track_name == "my_track"

        # Create a captured case without track
        case_no_track = CapturedCase(
            case_name="test_case",
            user_message="test",
            tool_calls=[],
        )
        assert case_no_track.track_name is None

    def test_captured_case_to_dict_includes_track_name(self) -> None:
        """CapturedCase.to_dict should include track_name when set."""
        from arcade_evals.capture import CapturedCase

        case = CapturedCase(
            case_name="test_case",
            user_message="test",
            tool_calls=[],
            track_name="my_track",
        )

        result = case.to_dict()
        assert "track_name" in result
        assert result["track_name"] == "my_track"

    def test_captured_case_to_dict_excludes_track_name_when_none(self) -> None:
        """CapturedCase.to_dict should not include track_name when None."""
        from arcade_evals.capture import CapturedCase

        case = CapturedCase(
            case_name="test_case",
            user_message="test",
            tool_calls=[],
            track_name=None,
        )

        result = case.to_dict()
        assert "track_name" not in result

    def test_json_formatter_shows_track_name(self) -> None:
        """JSON formatter should include track_name in output."""
        capture = _create_mock_capture_with_tracks()
        formatter = CaptureJsonFormatter()

        output = formatter.format([capture])
        data = json.loads(output)

        # Find case with track
        cases = data["captures"][0]["captured_cases"]
        track_case = next(c for c in cases if c.get("track_name") == "track_a")
        assert track_case["track_name"] == "track_a"

        # Find case without track
        regular_case = next(c for c in cases if c.get("track_name") is None)
        assert "track_name" not in regular_case

    def test_text_formatter_shows_track_info(self) -> None:
        """Text formatter should show track information."""
        capture = _create_mock_capture_with_tracks()
        formatter = CaptureTextFormatter()

        output = formatter.format([capture])

        # Should show track names in output
        assert "track_a" in output or "Track:" in output

    def test_html_formatter_shows_track_info(self) -> None:
        """HTML formatter should show track information."""
        capture = _create_mock_capture_with_tracks()
        formatter = CaptureHtmlFormatter()

        output = formatter.format([capture])

        # Should include track info in HTML
        assert "track_a" in output or "Track" in output

    def test_markdown_formatter_shows_track_info(self) -> None:
        """Markdown formatter should show track information."""
        capture = _create_mock_capture_with_tracks()
        formatter = CaptureMarkdownFormatter()

        output = formatter.format([capture])

        # Should include track info in markdown
        assert "[track_a]" in output or "track_a" in output

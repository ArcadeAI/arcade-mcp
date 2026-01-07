"""Tests for shared types in _types.py module."""

import pytest
from arcade_evals._evalsuite._types import (
    AnyExpectedToolCall,
    ComparativeCase,
    EvalRubric,
    ExpectedMCPToolCall,
    ExpectedToolCall,
    NamedExpectedToolCall,
    TrackConfig,
)

# Mark all tests in this module as requiring evals dependencies
pytestmark = pytest.mark.evals


class TestExpectedToolCall:
    """Tests for ExpectedToolCall dataclass."""

    def test_create_with_func_and_args(self) -> None:
        """Test creating ExpectedToolCall with function and args."""

        def my_tool(x: int, y: int) -> int:
            return x + y

        tc = ExpectedToolCall(func=my_tool, args={"x": 1, "y": 2})

        assert tc.func is my_tool
        assert tc.args == {"x": 1, "y": 2}

    def test_create_with_empty_args(self) -> None:
        """Test creating ExpectedToolCall with default empty args."""

        def my_tool() -> None:
            pass

        tc = ExpectedToolCall(func=my_tool)

        assert tc.func is my_tool
        assert tc.args == {}

    def test_create_positional_args(self) -> None:
        """Test creating ExpectedToolCall with positional args."""

        def my_tool(x: int) -> int:
            return x

        tc = ExpectedToolCall(my_tool, {"x": 5})

        assert tc.func is my_tool
        assert tc.args == {"x": 5}


class TestExpectedMCPToolCall:
    """Tests for ExpectedMCPToolCall dataclass."""

    def test_create_with_name_and_args(self) -> None:
        """Test creating ExpectedMCPToolCall with name and args."""
        tc = ExpectedMCPToolCall(tool_name="Calculator_Add", args={"a": 5, "b": 3})

        assert tc.tool_name == "Calculator_Add"
        assert tc.args == {"a": 5, "b": 3}

    def test_create_with_empty_args(self) -> None:
        """Test creating ExpectedMCPToolCall with default empty args."""
        tc = ExpectedMCPToolCall(tool_name="GetTime")

        assert tc.tool_name == "GetTime"
        assert tc.args == {}

    def test_create_positional_args(self) -> None:
        """Test creating ExpectedMCPToolCall with positional args."""
        tc = ExpectedMCPToolCall("Weather_Get", {"city": "NYC"})

        assert tc.tool_name == "Weather_Get"
        assert tc.args == {"city": "NYC"}


class TestNamedExpectedToolCall:
    """Tests for NamedExpectedToolCall dataclass."""

    def test_create(self) -> None:
        """Test creating NamedExpectedToolCall."""
        tc = NamedExpectedToolCall(name="MyTool", args={"param": "value"})

        assert tc.name == "MyTool"
        assert tc.args == {"param": "value"}

    def test_create_empty_args(self) -> None:
        """Test creating NamedExpectedToolCall with empty args."""
        tc = NamedExpectedToolCall(name="SimpleTool", args={})

        assert tc.name == "SimpleTool"
        assert tc.args == {}


class TestAnyExpectedToolCallTypeAlias:
    """Tests for AnyExpectedToolCall type alias."""

    def test_type_alias_accepts_expected_tool_call(self) -> None:
        """Test that ExpectedToolCall is valid for AnyExpectedToolCall."""

        def my_func() -> None:
            pass

        tc: AnyExpectedToolCall = ExpectedToolCall(func=my_func)
        assert isinstance(tc, ExpectedToolCall)

    def test_type_alias_accepts_expected_mcp_tool_call(self) -> None:
        """Test that ExpectedMCPToolCall is valid for AnyExpectedToolCall."""
        tc: AnyExpectedToolCall = ExpectedMCPToolCall(tool_name="Test")
        assert isinstance(tc, ExpectedMCPToolCall)


class TestEvalRubric:
    """Tests for EvalRubric dataclass."""

    def test_default_values(self) -> None:
        """Test EvalRubric has correct default values."""
        rubric = EvalRubric()

        assert rubric.fail_threshold == 0.8
        assert rubric.warn_threshold == 0.9
        assert rubric.fail_on_tool_selection is True
        assert rubric.fail_on_tool_call_quantity is True
        assert rubric.tool_selection_weight == 1.0

    def test_custom_values(self) -> None:
        """Test EvalRubric with custom values."""
        rubric = EvalRubric(
            fail_threshold=0.7,
            warn_threshold=0.85,
            fail_on_tool_selection=False,
            fail_on_tool_call_quantity=False,
            tool_selection_weight=0.5,
        )

        assert rubric.fail_threshold == 0.7
        assert rubric.warn_threshold == 0.85
        assert rubric.fail_on_tool_selection is False
        assert rubric.fail_on_tool_call_quantity is False
        assert rubric.tool_selection_weight == 0.5

    def test_str_representation(self) -> None:
        """Test EvalRubric __str__ method."""
        rubric = EvalRubric()

        result = str(rubric)

        assert "EvalRubric(" in result
        assert "fail_threshold=0.8" in result
        assert "warn_threshold=0.9" in result
        assert "fail_on_tool_selection=True" in result
        assert "fail_on_tool_call_quantity=True" in result
        assert "tool_selection_weight=1.0" in result

    def test_repr_representation(self) -> None:
        """Test EvalRubric __repr__ method returns same as __str__."""
        rubric = EvalRubric(fail_threshold=0.75)

        assert repr(rubric) == str(rubric)

    def test_str_with_custom_values(self) -> None:
        """Test __str__ reflects custom values."""
        rubric = EvalRubric(
            fail_threshold=0.5,
            warn_threshold=0.6,
            fail_on_tool_selection=False,
            fail_on_tool_call_quantity=False,
            tool_selection_weight=2.0,
        )

        result = str(rubric)

        assert "fail_threshold=0.5" in result
        assert "warn_threshold=0.6" in result
        assert "fail_on_tool_selection=False" in result
        assert "fail_on_tool_call_quantity=False" in result
        assert "tool_selection_weight=2.0" in result


class TestTrackConfigFromTypes:
    """Tests for TrackConfig dataclass from _types module."""

    def test_create_with_expected_tool_calls(self) -> None:
        """Test creating TrackConfig with expected tool calls."""

        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("Tool1", {"arg": "val"})
        ]
        config = TrackConfig(expected_tool_calls=expected)

        assert config.expected_tool_calls == expected
        assert config.critics == []

    def test_create_with_critics(self) -> None:
        """Test creating TrackConfig with critics."""
        from arcade_evals.critic import Critic, NoneCritic

        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("Tool1")]
        critics: list[Critic] = [NoneCritic(critic_field="field1")]
        config = TrackConfig(expected_tool_calls=expected, critics=critics)

        assert config.expected_tool_calls == expected
        assert config.critics == critics

    def test_mixed_expected_tool_calls(self) -> None:
        """Test TrackConfig with mixed ExpectedToolCall and ExpectedMCPToolCall."""

        def my_func() -> None:
            pass

        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedToolCall(func=my_func, args={"x": 1}),
            ExpectedMCPToolCall(tool_name="MCPTool", args={"y": 2}),
        ]
        config = TrackConfig(expected_tool_calls=expected)

        assert len(config.expected_tool_calls) == 2
        assert isinstance(config.expected_tool_calls[0], ExpectedToolCall)
        assert isinstance(config.expected_tool_calls[1], ExpectedMCPToolCall)


class TestComparativeCaseFromTypes:
    """Tests for ComparativeCase dataclass from _types module."""

    def test_default_values(self) -> None:
        """Test ComparativeCase default values."""
        case = ComparativeCase(
            name="test",
            user_message="Hello",
        )

        assert case.name == "test"
        assert case.user_message == "Hello"
        assert case.system_message == ""
        assert case.additional_messages == []
        assert case.rubric is None
        assert case.track_configs == {}

    def test_with_rubric(self) -> None:
        """Test ComparativeCase with custom rubric."""
        rubric = EvalRubric(fail_threshold=0.9)
        case = ComparativeCase(
            name="test",
            user_message="Hello",
            rubric=rubric,
        )

        assert case.rubric is rubric

    def test_add_track_config(self) -> None:
        """Test adding track configuration."""
        case = ComparativeCase(name="test", user_message="Hello")
        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [
            ExpectedMCPToolCall("Tool1", {"arg": "val"})
        ]

        case.add_track_config("Track1", expected)

        assert "Track1" in case.track_configs
        assert case.track_configs["Track1"].expected_tool_calls == expected

    def test_add_track_config_with_critics(self) -> None:
        """Test adding track config with critics."""
        from arcade_evals.critic import Critic, NoneCritic

        case = ComparativeCase(name="test", user_message="Hello")
        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("Tool1")]
        critics: list[Critic] = [NoneCritic(critic_field="field")]

        case.add_track_config("Track1", expected, critics=critics)

        assert case.track_configs["Track1"].critics == critics

    def test_add_duplicate_track_raises(self) -> None:
        """Test adding duplicate track config raises ValueError."""
        case = ComparativeCase(name="test", user_message="Hello")
        expected: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("Tool1")]

        case.add_track_config("Track1", expected)

        with pytest.raises(ValueError, match="already configured"):
            case.add_track_config("Track1", expected)

    def test_get_configured_tracks(self) -> None:
        """Test getting list of configured tracks."""
        case = ComparativeCase(name="test", user_message="Hello")

        assert case.get_configured_tracks() == []

        track1_calls: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("T1")]
        track2_calls: list[ExpectedToolCall | ExpectedMCPToolCall] = [ExpectedMCPToolCall("T2")]
        case.add_track_config("Track1", track1_calls)
        case.add_track_config("Track2", track2_calls)

        tracks = case.get_configured_tracks()

        assert "Track1" in tracks
        assert "Track2" in tracks
        assert len(tracks) == 2


class TestEvalSuiteCreateEvalCase:
    """Tests for EvalSuite._create_eval_case factory method."""

    def test_create_eval_case_basic(self) -> None:
        """Test creating EvalCase via factory method."""
        from arcade_evals import EvalSuite
        from arcade_evals._evalsuite._types import EvalRubric, NamedExpectedToolCall

        suite = EvalSuite(name="Test", system_message="System")

        case = suite._create_eval_case(
            name="test_case",
            system_message="Custom system",
            user_message="Hello",
            expected_tool_calls=[NamedExpectedToolCall(name="Tool1", args={"x": 1})],
            rubric=EvalRubric(),
            critics=[],
            additional_messages=[],
        )

        assert case.name == "test_case"
        assert case.system_message == "Custom system"
        assert case.user_message == "Hello"
        assert len(case.expected_tool_calls) == 1
        assert case.expected_tool_calls[0].name == "Tool1"

    def test_create_eval_case_with_critics(self) -> None:
        """Test creating EvalCase with critics."""
        from arcade_evals import EvalSuite
        from arcade_evals._evalsuite._types import EvalRubric, NamedExpectedToolCall
        from arcade_evals.critic import Critic, SimilarityCritic

        suite = EvalSuite(name="Test", system_message="System")
        critics: list[Critic] = [SimilarityCritic(critic_field="query", weight=1.0)]

        case = suite._create_eval_case(
            name="test_case",
            system_message="System",
            user_message="Query",
            expected_tool_calls=[NamedExpectedToolCall(name="Search", args={"query": "test"})],
            rubric=EvalRubric(),
            critics=critics,
            additional_messages=[],
        )

        assert case.critics == critics

    def test_create_eval_case_with_additional_messages(self) -> None:
        """Test creating EvalCase with additional messages."""
        from arcade_evals import EvalSuite
        from arcade_evals._evalsuite._types import EvalRubric

        suite = EvalSuite(name="Test", system_message="System")
        additional = [{"role": "assistant", "content": "Previous response"}]

        case = suite._create_eval_case(
            name="test_case",
            system_message="System",
            user_message="Follow-up",
            expected_tool_calls=[],
            rubric=EvalRubric(),
            critics=[],
            additional_messages=additional,
        )

        assert case.additional_messages == additional

    def test_create_eval_case_with_custom_rubric(self) -> None:
        """Test creating EvalCase with custom rubric."""
        from arcade_evals import EvalSuite
        from arcade_evals._evalsuite._types import EvalRubric

        suite = EvalSuite(name="Test", system_message="System")
        rubric = EvalRubric(fail_threshold=0.95, warn_threshold=0.98)

        case = suite._create_eval_case(
            name="test_case",
            system_message="System",
            user_message="Test",
            expected_tool_calls=[],
            rubric=rubric,
            critics=[],
            additional_messages=[],
        )

        assert case.rubric.fail_threshold == 0.95
        assert case.rubric.warn_threshold == 0.98

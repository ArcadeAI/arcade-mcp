"""Invoke informational quality reports with inert definitions and blocked network."""

import json
from textwrap import dedent
from unittest.mock import Mock

import pytest
from arcade_cli.main import cli
from arcade_evals import BinaryCritic, EvalSuite
from arcade_evals.eval import EvalCase
from arcade_evals.judge import JudgeVerdict
from typer.testing import CliRunner

pytestmark = pytest.mark.evals
runner = CliRunner()
PRIVATE = "synthetic-private-provider-detail"


@pytest.fixture(autouse=True)
def no_execution_or_network(monkeypatch):
    blocked = Mock(side_effect=AssertionError("Unexpected execution or network"))
    for key in ("JEV_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "synthetic-test-key")
    monkeypatch.setattr("socket.socket.connect", blocked)
    monkeypatch.setattr("arcade_cli.main.check_and_notify", blocked)
    monkeypatch.setattr("arcade_cli.main.check_existing_login", blocked)
    monkeypatch.setattr("arcade_cli.main._credentials_file_contains_legacy", blocked)
    for method in ("run", "run_comparative"):
        monkeypatch.setattr(EvalSuite, method, blocked)
    monkeypatch.setattr(EvalCase, "evaluate", blocked)
    monkeypatch.setattr(BinaryCritic, "evaluate", blocked)
    for method in (
        "_run_with_openai",
        "_run_with_anthropic",
        "_capture_with_openai",
        "_capture_with_anthropic",
    ):
        monkeypatch.setattr(f"arcade_evals.eval.{method}", blocked)
    yield
    blocked.assert_not_called()


def _verdicts():
    return {
        "contextScore": JudgeVerdict(0.9, None, "fixture", PRIVATE, raw={"private": PRIVATE}),
        "complexityChoice": JudgeVerdict(None, None, "fixture", PRIVATE, label="simple"),
        "hintNoul": JudgeVerdict(0.1, None, "fixture", PRIVATE),
        "ambiguityScore": JudgeVerdict(0.2, None, "fixture", PRIVATE),
        "humanNoul": JudgeVerdict(0.8, None, "fixture", PRIVATE),
    }


@pytest.fixture
def judge(monkeypatch):
    fake = Mock()
    fake.judge.return_value = _verdicts()
    constructor = Mock(return_value=fake)
    monkeypatch.setattr("arcade_cli.evals_quality._make_backend", constructor)
    return fake, constructor


def _definition(tmp_path, style="sync", *, name="eval_cases.py", extra=""):
    marker = tmp_path / f"{name}.constructed"
    make_suite = dedent(f"""
        from pathlib import Path
        from arcade_evals import EvalSuite, ExpectedMCPToolCall, BinaryCritic, tool_eval

        def make_suite():
            marker = Path({str(marker)!r})
            marker.write_text(marker.read_text() + 'x' if marker.exists() else 'x')
            suite = EvalSuite('support', 'Use support tools')
            suite.add_tool_definitions([{{
                'name': 'support.lookup',
                'description': 'Look up a ticket',
                'inputSchema': {{'type': 'object', 'properties': {{'id': {{'type': 'string'}}}}, 'required': ['id']}}
            }}])
            suite.add_case(
                name='ticket', user_message='synthetic-private-case-prompt',
                expected_tool_calls=[ExpectedMCPToolCall('support.lookup', {{'id': '42'}})],
                critics=[BinaryCritic('id', 1.0)]
            )
            {extra}
            return suite
    """)
    factory = {
        "sync": "@tool_eval()\ndef definition():\n    return make_suite()\n",
        "async": "@tool_eval()\nasync def definition():\n    return make_suite()\n",
        "coroutine": (
            "async def create_async():\n    return make_suite()\n"
            "@tool_eval()\ndef definition():\n    return create_async()\n"
        ),
    }[style]
    path = tmp_path / name
    path.write_text(make_suite + factory, encoding="utf-8")
    return path, marker


def _invoke(path, output, *args):
    return runner.invoke(
        cli,
        ["evals-quality", str(path), "--backend", "jev", "--output", str(output), *args],
    )


@pytest.mark.parametrize("style", ["sync", "async", "coroutine"])
def test_constructs_once_and_reports_actual_schemas_without_execution(tmp_path, judge, style):
    definition, marker = _definition(tmp_path, style)
    output = tmp_path / "report.json"
    result = _invoke(definition, output)
    assert result.exit_code == 0, result.output
    assert marker.read_text() == "x"
    fake, constructor = judge
    constructor.assert_called_once_with("jev", None)
    fake.judge.assert_called_once()
    state = fake.judge.call_args.kwargs["state"]
    schema = state["tools"][0]["function"]
    assert schema["name"] == "support_lookup"
    assert schema["parameters"]["properties"]["id"]["type"] == "string"
    assert state["reference_labels"]["expected"][0]["args"] == {"id": "42"}
    report = json.loads(output.read_text())
    assert report["schema_version"] == 1
    assert report["mode"] == "informational"
    assert report["backend"] == "jev"
    assert report["model"] == "jev-latest"
    assert report["complete"] is True
    assert report["errors"] == []
    assert report["summary"] == {
        "case_count": 1,
        "quality_concerns": 0,
        "uncertain_cases": 0,
        "usable_dimensions": 5,
    }
    case = report["cases"][0]
    assert (case["suite"], case["case"], case["track"]) == ("support", "ticket", None)
    dimensions = case["dimensions"]
    for qid, expected in (
        ("contextScore", 90),
        ("hintNoul", 10),
        ("ambiguityScore", 20),
        ("humanNoul", 80),
    ):
        assert dimensions[qid]["question_id"] == qid
        assert dimensions[qid]["percent"] == pytest.approx(expected)
        assert dimensions[qid]["confidence"] is None
    assert dimensions["contextScore"]["direction"] == "higher_is_better"
    assert dimensions["humanNoul"]["direction"] == "higher_is_better"
    assert dimensions["hintNoul"]["direction"] == "lower_is_better"
    assert dimensions["ambiguityScore"]["direction"] == "lower_is_better"
    assert dimensions["complexityChoice"]["category"] == "simple"
    assert dimensions["complexityChoice"]["percent"] is None
    assert dimensions["complexityChoice"]["score"] is None
    assert dimensions["complexityChoice"]["direction"] == "descriptive"
    assert "overall" not in json.dumps(report)
    assert "90.0%" in result.output
    assert "not model accuracy" in result.output
    assert "synthetic-private" not in result.output + output.read_text()


@pytest.mark.parametrize("style", ["sync", "async", "coroutine"])
def test_preserves_user_factory_decorator_and_required_arguments(tmp_path, judge, style):
    definition, factory_marker = _definition(tmp_path)
    setup_marker = tmp_path / "decorator.constructed"
    decorator_keyword = "async def" if style == "async" else "def"
    factory_keyword = "def" if style == "sync" else "async def"
    call = (
        "await factory('decorated support')" if style == "async" else "factory('decorated support')"
    )
    user_factory = dedent(f"""
        from functools import wraps

        def inject_setup(factory):
            @wraps(factory)
            {decorator_keyword} decorated():
                marker = Path({str(setup_marker)!r})
                marker.write_text(marker.read_text() + 'x' if marker.exists() else 'x')
                return {call}
            return decorated

        @tool_eval()
        @inject_setup
        {factory_keyword} definition(required_suite_name):
            suite = make_suite()
            suite.name = required_suite_name
            return suite
    """)
    definition.write_text(definition.read_text().split("@tool_eval()")[0] + user_factory)
    output = tmp_path / "report.json"
    result = _invoke(definition, output)
    assert result.exit_code == 0, result.output
    assert setup_marker.read_text() == "x"
    assert factory_marker.read_text() == "x"
    judge[0].judge.assert_called_once()
    report = json.loads(output.read_text())
    assert report["complete"] is True
    assert report["errors"] == []
    assert report["cases"][0]["suite"] == "decorated support"


def test_explicit_llm_model_is_used(tmp_path, judge):
    definition, _ = _definition(tmp_path)
    output = tmp_path / "report.json"
    result = runner.invoke(
        cli,
        [
            "evals-quality",
            str(definition),
            "--backend",
            "llm",
            "--model",
            "test-chat-model",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    judge[1].assert_called_once_with("llm", "test-chat-model")
    assert json.loads(output.read_text())["model"] == "test-chat-model"


@pytest.mark.parametrize(
    "condition", ["concerns", "missing", "invalid", "low_confidence", "unavailable"]
)
def test_quality_findings_and_uncertainty_are_informational(tmp_path, judge, condition):
    definition, _ = _definition(tmp_path)
    fake, _ = judge
    verdicts = _verdicts()
    if condition == "concerns":
        verdicts["contextScore"].score = 0.2
    elif condition == "missing":
        del verdicts["hintNoul"]
    elif condition == "invalid":
        verdicts["hintNoul"].score = True
    elif condition == "low_confidence":
        verdicts["contextScore"].confidence = 0.1
    else:
        fake.judge.side_effect = RuntimeError(PRIVATE)
    fake.judge.return_value = verdicts
    output = tmp_path / "report.json"
    result = _invoke(definition, output)
    assert result.exit_code == 0, result.output
    report = json.loads(output.read_text())
    case = report["cases"][0]
    expected_status = {"concerns": "failed", "missing": "invalid"}.get(condition, condition)
    assert case["status"] == expected_status
    assert report["complete"] is (condition == "concerns")
    assert case["warnings"]
    assert "Warning:" in result.output
    assert PRIVATE not in result.output + output.read_text()
    dimensions = case["dimensions"]
    if condition in {"missing", "invalid"}:
        assert dimensions["hintNoul"]["score"] is None
        assert dimensions["hintNoul"]["percent"] is None
        assert dimensions["contextScore"]["score"] == 0.9
        assert report["summary"]["usable_dimensions"] == 4
    elif condition == "low_confidence":
        assert dimensions["contextScore"]["confidence"] == 0.1
        assert dimensions["contextScore"]["percent"] == 90
    elif condition == "unavailable":
        assert all(dimension["score"] is None for dimension in dimensions.values())
        assert "No usable judgments were obtained." in result.output
    else:
        assert "quality concerns" in result.output
        assert report["summary"]["quality_concerns"] == 1


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--backend", "other"],
        ["--backend", "llm"],
        ["--backend", "llm", "--model", " "],
        ["--backend", "jev", "--model", ""],
    ],
)
def test_invalid_configuration_precedes_loading_and_backend_creation(tmp_path, judge, args):
    definition, marker = _definition(tmp_path)
    result = runner.invoke(cli, ["evals-quality", str(definition), *args])
    assert result.exit_code != 0
    assert not marker.exists()
    judge[1].assert_not_called()


@pytest.mark.parametrize(
    "failure",
    [
        "absent_path",
        "no_files",
        "import",
        "factory",
        "wrong_type",
        "no_factory",
        "no_cases",
        "schema",
        "comparative",
    ],
)
def test_operational_definition_failures_are_nonzero(tmp_path, judge, failure):
    path = tmp_path
    if failure == "absent_path":
        path = tmp_path / "missing"
    elif failure == "import":
        (tmp_path / "eval_broken.py").write_text(f"raise RuntimeError({PRIVATE!r})\n")
    elif failure in {"factory", "wrong_type"}:
        body = f"raise RuntimeError({PRIVATE!r})" if failure == "factory" else "return {}"
        (tmp_path / "eval_broken.py").write_text(
            f"from arcade_evals import tool_eval\n@tool_eval()\ndef broken():\n    {body}\n"
        )
    elif failure == "no_factory":
        (tmp_path / "eval_empty.py").write_text("value = 1\n")
    elif failure != "no_files":
        extra = {
            "no_cases": "suite.cases.clear()",
            "schema": "suite._internal_registry = None",
            "comparative": "suite.add_comparative_case('comparison', 'Look up the ticket')",
        }[failure]
        _definition(tmp_path, extra=extra)
    output = tmp_path / "report.json"
    result = _invoke(path, output)
    assert result.exit_code == 1, result.output
    report = json.loads(output.read_text())
    assert report["complete"] is False
    assert report["errors"]
    assert report["cases"] == []
    judge[0].judge.assert_not_called()
    assert PRIVATE not in result.output + output.read_text()
    if failure == "comparative":
        assert "Comparative definitions are not supported" in result.output


def test_good_file_and_broken_file_preserve_partial_report_and_error(tmp_path, judge):
    _definition(tmp_path)
    (tmp_path / "eval_broken.py").write_text(f"raise RuntimeError({PRIVATE!r})\n")
    output = tmp_path / "report.json"
    result = _invoke(tmp_path, output)
    assert result.exit_code == 1, result.output
    report = json.loads(output.read_text())
    assert report["complete"] is False
    assert len(report["cases"]) == 1
    assert len(report["errors"]) == 1
    assert report["cases"][0]["dimensions"]["contextScore"]["percent"] == 90
    assert PRIVATE not in result.output + output.read_text()


def test_backend_configuration_error_is_safe_and_precedes_factory(tmp_path, judge):
    definition, marker = _definition(tmp_path)
    judge[1].side_effect = RuntimeError(PRIVATE)
    output = tmp_path / "report.json"
    result = _invoke(definition, output)
    assert result.exit_code == 1
    assert not marker.exists()
    assert json.loads(output.read_text())["errors"][0]["source"] == "configuration"
    assert PRIVATE not in result.output + output.read_text()


@pytest.mark.parametrize("backend", ["jev", "llm"])
def test_missing_judge_credentials_are_configuration_errors(tmp_path, monkeypatch, backend):
    definition, marker = _definition(tmp_path)
    for key in ("JEV_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    output = tmp_path / "report.json"
    args = ["evals-quality", str(definition), "--backend", backend, "--output", str(output)]
    if backend == "llm":
        args.extend(["--model", "test-chat-model"])
    result = runner.invoke(cli, args)
    assert result.exit_code == 1
    assert not marker.exists()
    report = json.loads(output.read_text())
    assert report["errors"][0]["source"] == "configuration"
    assert report["cases"] == []


def test_output_write_error_is_nonzero_with_visible_results(tmp_path, judge):
    definition, _ = _definition(tmp_path)
    result = _invoke(definition, tmp_path)
    assert result.exit_code == 1
    assert "90.0%" in result.output
    assert "Quality report could not be written" in result.output
    assert "Complete: false" in result.output


def test_help_is_public_and_requires_no_backend(tmp_path, judge):
    result = runner.invoke(cli, ["evals-quality", "--help"])
    assert result.exit_code == 0
    assert "--backend" in result.output
    assert "--model" in result.output
    assert "--output" in result.output
    judge[1].assert_not_called()


def test_default_console_report_does_not_require_an_output_file(tmp_path, judge):
    definition, _ = _definition(tmp_path)
    result = runner.invoke(cli, ["evals-quality", str(definition), "--backend", "jev"])
    assert result.exit_code == 0, result.output
    assert "90.0%" in result.output
    assert "Complete: true" in result.output
    assert not list(tmp_path.glob("*.json"))

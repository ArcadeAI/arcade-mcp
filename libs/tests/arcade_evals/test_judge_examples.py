"""Run the public examples with sockets blocked, even if provider keys exist."""

import json
import runpy
from pathlib import Path

import pytest

pytestmark = pytest.mark.evals
EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "evals"


@pytest.mark.parametrize(
    "filename", ["eval_judge_critics.py", "eval_case_quality.py", "eval_grouped_judges.py"]
)
def test_default_examples_are_offline_and_show_passes_and_failures(filename, monkeypatch, capsys):
    for key in ("JEV_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "synthetic-demo-must-not-use-this")
    monkeypatch.setattr("socket.socket.connect", lambda *args: pytest.fail("Unexpected network"))
    monkeypatch.setattr("sys.argv", [filename])
    runpy.run_path(str(EXAMPLES / filename), run_name="__main__")
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "demo"
    assert "not measured model accuracy" in output["note"]
    rows = output["examples"]
    if filename == "eval_grouped_judges.py":
        assert len(rows) == 2
        assert [row["passed"] for row in rows] == [True, False]
        assert [row["judgment"]["judge_calls"]["explicit"] for row in rows] == [1, 2]
        assert all(len(row["judgment"]["details"]) == 3 for row in rows)
        assert all(row["judgment"]["cache_hit"] for row in rows)
    elif filename == "eval_case_quality.py":
        assert len(rows) == 6
        assert sum(row["passed"] for row in rows) == 2
        for row in rows:
            assert bool(row["reasons"]) is not row["passed"]
            assert all(v["backend"] == "demo" for v in row["verdicts"].values())
    else:
        assert len(rows) == 8
        assert sum(row["result"]["match"] for row in rows) == 4
        assert len({row["critic"] for row in rows}) == 4
        for row in rows:
            assert row["result"]["backend"] == "demo"
            assert row["repeat_cache_hit"] is True
            assert row["repeat_judge_calls"] == row["result"]["judge_calls"]


def test_calibration_example_is_offline_and_reports_threshold_evidence(monkeypatch, capsys):
    filename = "eval_case_quality_calibration.py"
    for key in ("JEV_API_KEY", "TYPESAFE_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.setenv(key, "synthetic-demo-must-not-use-this")
    monkeypatch.setattr("socket.socket.connect", lambda *args: pytest.fail("Unexpected network"))
    monkeypatch.setattr("sys.argv", [filename])
    runpy.run_path(str(EXAMPLES / filename), run_name="__main__")
    output = json.loads(capsys.readouterr().out)
    assert output["mode"] == "demo"
    assert output["summary"] == {
        "fixtures": 11,
        "outcome_matches": 11,
        "dimension_mismatches": 0,
    }
    assert {row["case"] for row in output["cases"]} >= {
        "pass_prior_assistant_context",
        "pass_structured_document_with_explicit_style",
        "fail_structured_style_without_contract",
        "pass_spreadsheet_formula_with_source_context",
    }
    for dimension in ("context", "hint", "ambiguity", "human"):
        assert output["thresholds"][dimension]["separable"] is True
        assert output["thresholds"][dimension]["current_supported"] is True


def test_calibration_example_selects_named_offline_fixtures(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *args: pytest.fail("Unexpected network"))
    module = runpy.run_path(
        str(EXAMPLES / "eval_case_quality_calibration.py"), run_name="fixture_module"
    )
    output = module["run_calibration"](
        case_names={"pass_literal_identifier", "fail_explicit_benchmark_answer"}
    )
    assert output["summary"]["fixtures"] == 2
    assert {row["case"] for row in output["cases"]} == {
        "pass_literal_identifier",
        "fail_explicit_benchmark_answer",
    }


def test_calibration_example_applies_user_policy_overrides(monkeypatch):
    monkeypatch.setattr("socket.socket.connect", lambda *args: pytest.fail("Unexpected network"))
    module = runpy.run_path(
        str(EXAMPLES / "eval_case_quality_calibration.py"), run_name="policy_module"
    )
    output = module["run_calibration"](
        case_names={"pass_literal_identifier"},
        policy_overrides={"max_hint": 0.2},
    )
    assert output["policy"]["max_hint"] == 0.2
    assert output["cases"][0]["passed"] is False
    assert output["cases"][0]["reasons"] == ["hint: 0.30 outside allowed range 0.00..0.20"]
    with pytest.raises(ValueError, match="Unknown quality policy settings"):
        module["run_calibration"](policy_overrides={"unsupported": 0.2})

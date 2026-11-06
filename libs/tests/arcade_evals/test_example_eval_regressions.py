"""Offline regressions for the Jev suite and calibration examples."""

import importlib
import json
import runpy
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from arcade_core.toolkit import Toolkit
from arcade_evals import EvalSuite, JudgeVerdict
from arcade_evals.errors import JudgeError

pytestmark = [pytest.mark.evals, pytest.mark.usefixtures("offline_socket_guard")]
EXAMPLES = Path(__file__).resolve().parents[3] / "examples"
JEV_SERVER = EXAMPLES / "mcp_servers" / "server_with_evaluations"
CALIBRATION = EXAMPLES / "evals" / "eval_case_quality_calibration.py"


def _jev_suite_module(monkeypatch):
    monkeypatch.syspath_prepend(str(JEV_SERVER / "src"))

    def from_source(cls, module):
        assert module.__name__ == "server_with_evaluations"
        return cls.from_directory(JEV_SERVER)

    # The example is not installed in the root test environment. Load its real
    # toolkit from source instead of requiring separate distribution metadata.
    monkeypatch.setattr(Toolkit, "from_module", classmethod(from_source))
    return runpy.run_path(str(JEV_SERVER / "evals" / "eval_using_jev_critics.py"))


def test_jev_suite_factory_returns_both_cases(monkeypatch):
    module = _jev_suite_module(monkeypatch)
    suite = module["server_with_evaluations_jev_eval_suite"].__wrapped__()
    assert isinstance(suite, EvalSuite)
    assert [case.name for case in suite.cases] == [
        "Create email subject",
        "Write product description for fitness tracker",
    ]


def test_jev_suite_critics_explicitly_select_jev_without_fallback(monkeypatch):
    created = []
    original_init = EvalSuite.__post_init__

    def record_suite(suite):
        original_init(suite)
        created.append(suite)

    monkeypatch.setattr(EvalSuite, "__post_init__", record_suite)
    module = _jev_suite_module(monkeypatch)
    module["server_with_evaluations_jev_eval_suite"].__wrapped__()
    critics = [critic for case in created[0].cases for critic in case.critics]
    assert len(critics) == 4
    assert all(critic.provider == "jev" for critic in critics)
    assert all(critic.backend is None and critic.fallback == "none" for critic in critics)

    for key in ("JEV_API_KEY", "TYPESAFE_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    for critic in critics:
        result = critic.evaluate("required text", "paraphrased text")
        assert result["status"] == "unavailable"
        assert result["score"] == 0
        assert result["match"] is False
        assert result["judged"] is False


@pytest.mark.asyncio
async def test_jev_suite_decorator_passes_suite_to_mocked_runner(monkeypatch):
    module = _jev_suite_module(monkeypatch)
    runner = AsyncMock(return_value={"mocked": True})
    monkeypatch.setattr(importlib.import_module("arcade_evals.eval"), "_run_with_openai", runner)
    result = await module["server_with_evaluations_jev_eval_suite"](
        provider_api_key="synthetic-test-key", model="fixture-model", max_concurrency=2
    )
    assert result == [{"mocked": True}]
    suite, key, model = runner.call_args.args
    assert isinstance(suite, EvalSuite)
    assert len(suite.cases) == 2
    assert suite.max_concurrent == 2
    assert key == "synthetic-test-key"
    assert model == "fixture-model"


def _verdicts():
    return {
        "contextScore": JudgeVerdict(0.9, 0.9, "fixture", "fixture-model"),
        "hintNoul": JudgeVerdict(0.1, None, "fixture", "fixture-model"),
        "ambiguityScore": JudgeVerdict(0.1, 0.9, "fixture", "fixture-model"),
        "humanNoul": JudgeVerdict(0.9, None, "fixture", "fixture-model"),
        "complexityChoice": JudgeVerdict(None, 0.9, "fixture", "fixture-model", label="simple"),
    }


@pytest.mark.parametrize(
    ("failure", "question_id", "expected_status"),
    [
        ("missing", "contextScore", "invalid"),
        ("missing", "complexityChoice", "invalid"),
        ("invalid", "contextScore", "invalid"),
        ("invalid", "complexityChoice", "invalid"),
        ("unavailable", None, "unavailable"),
        ("low_confidence", "contextScore", "low_confidence"),
    ],
)
def test_calibration_records_withheld_verdicts_without_accuracy_claims(
    failure, question_id, expected_status
):
    module = runpy.run_path(str(CALIBRATION))
    backend = MagicMock()
    answers = _verdicts()
    if failure == "missing":
        del answers[question_id]
    elif failure == "invalid":
        answers[question_id] = (
            JudgeVerdict(None, None, "fixture", "fixture-model", label="unsupported")
            if question_id == "complexityChoice"
            else JudgeVerdict(float("nan"), None, "fixture", "fixture-model")
        )
    elif failure == "unavailable":
        backend.judge.side_effect = JudgeError("Fixture backend unavailable")
    else:
        answers[question_id].confidence = 0.1
    backend.judge.return_value = answers
    output = module["run_calibration"](backend=backend, case_names={"fail_missing_target_context"})

    row = output["cases"][0]
    assert row["status"] == expected_status
    assert row["passed"] is False
    assert row["expected_pass"] is False
    assert row["outcome_matches"] is None
    assert row["dimension_matches"] == dict.fromkeys(module["DIMENSIONS"])
    assert row["reasons"]
    assert output["summary"]["outcome_matches"] == 0
    assert output["summary"]["dimension_mismatches"] == 0
    for threshold in output["thresholds"].values():
        assert threshold["good_scores"] == threshold["bad_scores"] == []
        assert threshold["range"] is None
        assert threshold["current_supported"] is None

    if failure == "unavailable":
        assert row["scores"] == dict.fromkeys(module["DIMENSIONS"])
        assert row["model"] is None
        assert row["complexity"] is None
    else:
        assert row["scores"]["hint"] == 0.1
        if question_id == "complexityChoice":
            assert row["complexity"] is None
            assert row["model"] == "fixture-model"
        elif failure == "low_confidence":
            assert row["scores"]["context"] == 0.9
        else:
            assert row["scores"]["context"] is None
            assert row["model"] is None
    json.dumps(output, allow_nan=False)
    backend.judge.assert_called_once()

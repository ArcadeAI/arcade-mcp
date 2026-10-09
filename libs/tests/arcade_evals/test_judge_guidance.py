"""Application guidance stays in questions; scenario context stays in evidence."""

from unittest.mock import MagicMock

import pytest
from arcade_evals import (
    CompletenessCritic,
    GroundednessCritic,
    IntentionCritic,
    JudgeVerdict,
    SemanticSimilarityCritic,
)

pytestmark = pytest.mark.evals


@pytest.mark.parametrize(
    "critic_type,options",
    [
        (SemanticSimilarityCritic, {}),
        (GroundednessCritic, {}),
        (CompletenessCritic, {}),
        (IntentionCritic, {"intent": "Create a readable table"}),
    ],
)
def test_every_judge_critic_sends_custom_guidance_and_context(critic_type, options):
    backend = MagicMock()
    backend.judge.side_effect = lambda **request: {
        qid: JudgeVerdict(0.9, None, "test") for qid in request["questions"]
    }
    instructions = "Preserve existing formulas and format the header consistently."
    context = {
        "before": {"A1": "Revenue"},
        "additional_messages": [{"role": "user", "content": "Keep the original totals"}],
    }
    critic = critic_type(
        "update", 1.0, backend=backend, instructions=instructions, context=context, **options
    )
    expected = {"header": "Revenue", "totals": "unchanged"}
    actual = {"header": "Revenue", "totals": "unchanged", "style": "bold"}
    result = critic.evaluate(expected, actual)
    request = backend.judge.call_args.kwargs
    assert result["match"] is True
    assert request["state"]["context"] == context
    assert request["state"]["expected"] == expected
    assert request["state"]["actual"] == actual
    question = request["questions"][critic.question_id]
    assert instructions in question["instructions"]
    assert (
        critic.build_questions(expected, actual)[critic.question_id]["instructions"]
        in question["instructions"]
    )
    assert "Keep the original totals" not in question["instructions"]

    # Changed evidence or guidance must not reuse an old verdict.
    critic.evaluate(expected, actual)
    assert backend.judge.call_count == 2
    critic.instructions = "Preserve formulas; use a blue header."
    critic.evaluate(expected, actual)
    critic.context["before"]["A1"] = "Net revenue"
    critic.evaluate(expected, actual)
    assert backend.judge.call_count == 4


def test_new_fields_do_not_change_existing_intention_positional_arguments():
    critic = IntentionCritic("text", 1.0, 0.7, 0.5, None, "jev-latest", None, "Say hello")
    assert critic.intent == "Say hello"
    assert critic.instructions == ""
    assert critic.context is None

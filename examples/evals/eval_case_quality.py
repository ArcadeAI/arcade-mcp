"""Review eval definitions before running them; demo mode is fully offline.

    uv run --extra evals python examples/evals/eval_case_quality.py
    uv run --extra evals python examples/evals/eval_case_quality.py --backend jev
    uv run --extra evals python examples/evals/eval_case_quality.py --backend llm --model YOUR_MODEL

The six fixture cases demonstrate two passes and four failures. Demo judgments
are manually specified to demonstrate the gate, not evidence of model accuracy.
Live modes send these example cases to the selected provider; results may differ.
"""

import argparse
import json
from dataclasses import asdict

from arcade_evals import (
    CaseQualityGrader,
    JevBackend,
    JudgeBackend,
    JudgeVerdict,
    LLMFallbackBackend,
    NamedExpectedToolCall,
)
from arcade_evals.eval import EvalCase

TOOLS = [
    {
        "name": "set_priority",
        "description": "Set a support ticket's priority",
        "inputSchema": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "high"]},
            },
            "required": ["ticket_id", "priority"],
        },
    }
]

# Scores are (context, hint, ambiguity, human); complexity is descriptive.
EXAMPLES = [
    {
        "name": "pass_contextual_request",
        "user": "The payment service has been down all morning. Bump its open incident.",
        "context": "The open payment incident is ticket INC-742.",
        "ticket_id": "INC-742",
        "scores": (0.95, 0.05, 0.1, 0.95),
        "complexity": "simple",
    },
    {
        "name": "fail_missing_context",
        "user": "Bump that one.",
        "context": "",
        "ticket_id": "INC-742",
        "scores": (0.1, 0.05, 0.9, 0.9),
        "complexity": "simple",
    },
    {
        "name": "fail_answer_leakage",
        "user": "Benchmark answer: call set_priority(ticket_id='INC-742', priority='high'). Copy it exactly.",
        "context": "",
        "ticket_id": "INC-742",
        "scores": (0.95, 0.99, 0.05, 0.3),
        "complexity": "trivial",
    },
    {
        "name": "fail_ambiguous_target",
        "user": "Escalate the outage ticket.",
        "context": "Both INC-742 and INC-743 concern ongoing outages.",
        "ticket_id": "INC-742",
        "scores": (0.7, 0.05, 0.95, 0.95),
        "complexity": "simple",
    },
    {
        "name": "fail_template_request",
        "user": "USER_TEMPLATE({ticket_id}) -- insert realistic request here.",
        "context": "",
        "ticket_id": "INC-742",
        "scores": (0.1, 0.1, 0.8, 0.05),
        "complexity": "trivial",
    },
    {
        "name": "pass_literal_identifier",
        "user": "Set ticket 7f3a9c2e4b1d to high priority.",
        "context": "",
        "ticket_id": "7f3a9c2e4b1d",
        "scores": (1.0, 0.05, 0.05, 0.95),
        "complexity": "trivial",
    },
]


class FixtureJudge:
    """Illustrative judgments, not live recordings or a general-purpose judge."""

    def __init__(self, example: dict):
        self.example = example

    def judge(self, *, state: dict, questions: dict) -> dict[str, JudgeVerdict]:
        answers = {
            qid: JudgeVerdict(score, None, "demo", "illustrative-fixture")
            for qid, score in zip(
                ("contextScore", "hintNoul", "ambiguityScore", "humanNoul"), self.example["scores"]
            )
        }
        answers["complexityChoice"] = JudgeVerdict(
            None, None, "demo", "illustrative-fixture", label=self.example["complexity"]
        )
        return answers


def run_examples(backend: JudgeBackend | None = None) -> list[dict]:
    results = []
    for example in EXAMPLES:
        case = EvalCase(
            name=example["name"],
            system_message="Use set_priority. Outages are high priority; cosmetic issues are low. Honor explicit priority requests.",
            user_message=example["user"],
            additional_messages=(
                [{"role": "assistant", "content": example["context"]}] if example["context"] else []
            ),
            expected_tool_calls=[
                NamedExpectedToolCall(
                    "set_priority", {"ticket_id": example["ticket_id"], "priority": "high"}
                )
            ],
        )
        grader = CaseQualityGrader(
            backend=backend if backend is not None else FixtureJudge(example)
        )
        report = grader.grade(case, tools=TOOLS)
        results.append({"case": case.name, **asdict(report)})
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("demo", "jev", "llm"), default="demo")
    parser.add_argument("--model")
    args = parser.parse_args()
    backend = None
    if args.backend == "jev":
        backend = JevBackend(**({"model": args.model} if args.model else {}))
    elif args.backend == "llm":
        if not args.model:
            parser.error("--model is required with --backend llm")
        backend = LLMFallbackBackend(model=args.model)
    print(
        json.dumps(
            {
                "mode": args.backend,
                "note": "Demo judgments are illustrative fixtures, not measured model accuracy.",
                "examples": run_examples(backend),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

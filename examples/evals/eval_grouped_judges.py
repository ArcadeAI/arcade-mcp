"""Batch content, grounding, and style checks for a structured document argument.

    uv run --extra evals python examples/evals/eval_grouped_judges.py
    uv run --extra evals python examples/evals/eval_grouped_judges.py --backend jev
    uv run --extra evals python examples/evals/eval_grouped_judges.py --backend llm --model YOUR_MODEL

Default mode uses scripted scores and pre-captured arguments. No document is
edited or rendered. Live modes send the example evidence to the selected judge.
"""

import argparse
import json

from arcade_evals import (
    CompletenessCritic,
    EvalSuite,
    ExpectedMCPToolCall,
    GroundednessCritic,
    IntentionCritic,
    JevBackend,
    JudgeBackend,
    JudgeCriticGroup,
    JudgeVerdict,
    LLMFallbackBackend,
)


class FixtureJudge:
    """Two illustrative batches, not evidence of model accuracy."""

    def __init__(self):
        self.scores = iter((0.95, 0.2))

    def judge(self, *, state: dict, questions: dict) -> dict[str, JudgeVerdict]:
        score = next(self.scores)
        return {qid: JudgeVerdict(score, None, "demo", "fixture") for qid in questions}


def run_examples(backend: JudgeBackend | None = None) -> list[dict]:
    expected = {
        "title": "Sales",
        "table": {
            "headers": ["Product", "Quantity", "Total"],
            "rows": [["Pen", 2, "$4.00"]],
            "header_style": {"bold": True, "background": "navy", "text_color": "white"},
        },
    }
    context = {
        "before": {"title": "Sales", "table": None},
        "additional_messages": [{"role": "user", "content": "Two pens cost four dollars."}],
    }
    group = JudgeCriticGroup(
        critic_field="document",
        weight=1.0,
        backend=backend if backend is not None else FixtureJudge(),
        context=context,
        instructions="Preserve content outside the table; do not require identical JSON key order.",
        critics=[
            CompletenessCritic(
                "document",
                0.4,
                instructions="Require Product, Quantity, and Total columns and all supplied rows.",
            ),
            GroundednessCritic(
                "document",
                0.3,
                instructions="Amounts and quantities must agree with expected and the source messages.",
            ),
            IntentionCritic(
                "document",
                0.3,
                intent="Create a readable sales table",
                instructions="Use a distinct header style and consistent currency formatting. Judge supplied style metadata, not unseen pixels.",
            ),
        ],
    )
    suite = EvalSuite(name="Grouped document checks", system_message="Use edit_document")
    examples = [
        ("complete_table", expected),
        (
            "missing_columns_and_invented_amount",
            {"title": "Sales", "table": {"headers": ["Product"], "rows": [["Pen", "$400.00"]]}},
        ),
    ]
    results = []
    for name, actual in examples:
        suite.add_case(
            name=name,
            user_message="Create a readable sales table and preserve the title.",
            additional_messages=context["additional_messages"],
            expected_tool_calls=[ExpectedMCPToolCall("edit_document", {"document": expected})],
            critics=[group],
        )
        result = suite.cases[-1].evaluate([("edit_document", {"document": actual})])
        detail = next(row for row in result.results if row["field"] == "document")
        results.append({"case": name, "passed": result.passed, "judgment": detail})
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
                "note": "Demo judgments are scripted, not measured model accuracy.",
                "examples": run_examples(backend),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

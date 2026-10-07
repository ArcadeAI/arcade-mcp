"""Run all four judge critics; demo mode is offline and uses illustrative scores.

    uv run --extra evals python examples/evals/eval_judge_critics.py
    uv run --extra evals python examples/evals/eval_judge_critics.py --backend jev
    uv run --extra evals python examples/evals/eval_judge_critics.py --backend llm --model YOUR_MODEL

Live modes send example text to the selected provider and require credentials.
An injected OpenAI-compatible client can also use a custom base_url.
"""

import argparse
import json

from arcade_evals import (
    CompletenessCritic,
    GroundednessCritic,
    IntentionCritic,
    JevBackend,
    JudgeBackend,
    JudgeVerdict,
    LLMFallbackBackend,
    SemanticSimilarityCritic,
)


class FixtureJudge:
    """Small custom backend, deliberately scripted; not a semantic judge."""

    def __init__(self, score: float):
        self.score = score

    def judge(self, *, state: dict, questions: dict) -> dict[str, JudgeVerdict]:
        return {
            qid: JudgeVerdict(self.score, None, "demo", model="illustrative-fixture")
            for qid in questions
        }


def run_examples(backend: JudgeBackend | None = None) -> list[dict]:
    examples = [
        (
            SemanticSimilarityCritic,
            {},
            "The parcel arrives Monday.",
            "Delivery is on Monday.",
            0.95,
        ),
        (
            SemanticSimilarityCritic,
            {},
            "The parcel arrives Monday.",
            "It will not arrive Monday.",
            0.05,
        ),
        (
            IntentionCritic,
            {"intent": "Politely request a document"},
            "Please send the report.",
            "Could you share the report?",
            0.95,
        ),
        (
            IntentionCritic,
            {"intent": "Politely request a document"},
            "Please send the report.",
            "Send it now, idiot.",
            0.05,
        ),
        (GroundednessCritic, {}, "The tracker has GPS.", "GPS is included.", 0.95),
        (
            GroundednessCritic,
            {},
            "The tracker has GPS.",
            "GPS and a lifetime warranty are included.",
            0.05,
        ),
        (
            CompletenessCritic,
            {},
            "Mention GPS and heart-rate monitoring.",
            "Includes GPS and heart-rate monitoring.",
            0.95,
        ),
        (CompletenessCritic, {}, "Mention GPS and heart-rate monitoring.", "Includes GPS.", 0.05),
    ]
    results = []
    for critic_type, options, expected, actual, demo_score in examples:
        critic = critic_type(
            critic_field="text",
            weight=1.0,
            backend=backend if backend is not None else FixtureJudge(demo_score),
            **options,
        )
        first = critic.evaluate(expected, actual)
        cached = critic.evaluate(expected, actual)
        results.append({
            "critic": critic_type.__name__,
            "expected": expected,
            "actual": actual,
            "result": first,
            "repeat_cache_hit": cached["cache_hit"],
            "repeat_judge_calls": cached["judge_calls"],
        })
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
                "note": "Demo scores are scripted examples, not measured model accuracy.",
                "examples": run_examples(backend),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

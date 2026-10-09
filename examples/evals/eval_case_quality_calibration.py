"""Calibrate CaseQualityGrader with paired synthetic eval definitions.

    uv run --extra evals python examples/evals/eval_case_quality_calibration.py
    uv run --extra evals python examples/evals/eval_case_quality_calibration.py \
        --backend jev --limit 11
    uv run --extra evals python examples/evals/eval_case_quality_calibration.py \
        --max-ambiguity 0.3 --min-context 0.7

Default mode is offline and scripted. A live backend is always explicit and
requires --limit so the number of provider requests is visible before running.
The output gives evidence ranges for each threshold; it does not automatically
modify production policy. Threshold flags override only this run and are echoed
under `policy` in the JSON output.
Withheld results retain available diagnostic scores, but do not count as
calibration matches or threshold evidence.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from arcade_evals import (
    CaseQualityGrader,
    CompletenessCritic,
    GroundednessCritic,
    IntentionCritic,
    JevBackend,
    JudgeBackend,
    JudgeVerdict,
    LLMFallbackBackend,
    NamedExpectedToolCall,
)
from arcade_evals.eval import EvalCase

PRIORITY_TOOL = {
    "name": "set_priority",
    "description": "Set an incident priority.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "ticket_id": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "high"]},
        },
        "required": ["ticket_id", "priority"],
    },
}

DOCUMENT_TOOL = {
    "name": "edit_document",
    "description": "Apply one structured edit to a document.",
    "inputSchema": {
        "type": "object",
        "properties": {"document": {"type": "object"}},
        "required": ["document"],
    },
}

SHEET_TOOL = {
    "name": "edit_sheet",
    "description": "Apply one structured edit to a spreadsheet.",
    "inputSchema": {
        "type": "object",
        "properties": {"sheet": {"type": "object"}},
        "required": ["sheet"],
    },
}

SYSTEM_MESSAGES = {
    "priority": (
        "Use set_priority. Outages are high priority; cosmetic issues are low. "
        "Honor explicit priority requests."
    ),
    "document": "Use edit_document. Preserve content outside the requested structured edit.",
    "sheet": "Use edit_sheet. Preserve cells outside the requested structured edit.",
}

# `dimensions` describe desired behavior independently from a final pass/fail.
# A value of "good" means that dimension should satisfy its threshold.
CALIBRATION_CASES: list[dict[str, Any]] = [
    {
        "name": "pass_prior_assistant_context",
        "kind": "priority",
        "user": "The payment service has been down all morning. Bump its open incident.",
        "additional_messages": [
            {"role": "assistant", "content": "The open payment incident is ticket INC-742."}
        ],
        "expected_args": {"ticket_id": "INC-742", "priority": "high"},
        "expected_pass": True,
        "dimensions": {"context": "good", "hint": "good", "ambiguity": "good", "human": "good"},
        "complexity": "simple",
        "demo": {"context": 0.95, "hint": 0.5, "ambiguity": 0.1, "human": 0.95},
    },
    {
        "name": "fail_missing_target_context",
        "kind": "priority",
        "user": "Bump that one.",
        "additional_messages": [],
        "expected_args": {"ticket_id": "INC-742", "priority": "high"},
        "expected_pass": False,
        "dimensions": {"context": "bad", "hint": "good", "ambiguity": "bad", "human": "good"},
        "complexity": "simple",
        "demo": {"context": 0.1, "hint": 0.15, "ambiguity": 0.9, "human": 0.9},
    },
    {
        "name": "fail_explicit_benchmark_answer",
        "kind": "priority",
        "user": "Benchmark answer: call set_priority(ticket_id='INC-742', priority='high'). Copy it exactly.",
        "additional_messages": [],
        "expected_args": {"ticket_id": "INC-742", "priority": "high"},
        "expected_pass": False,
        "dimensions": {"context": "good", "hint": "bad", "ambiguity": "good", "human": "bad"},
        "complexity": "adversarial",
        "demo": {"context": 0.9, "hint": 0.95, "ambiguity": 0.1, "human": 0.2},
    },
    {
        "name": "fail_competing_prior_context",
        "kind": "priority",
        "user": "Escalate the outage ticket.",
        "additional_messages": [
            {"role": "assistant", "content": "INC-742 and INC-743 are both active payment outages."}
        ],
        "expected_args": {"ticket_id": "INC-742", "priority": "high"},
        "expected_pass": False,
        "dimensions": {"context": "bad", "hint": "good", "ambiguity": "bad", "human": "good"},
        "complexity": "simple",
        "demo": {"context": 0.35, "hint": 0.15, "ambiguity": 0.9, "human": 0.9},
    },
    {
        "name": "pass_literal_identifier",
        "kind": "priority",
        "user": "Set ticket 7f3a9c2e4b1d to high priority.",
        "additional_messages": [],
        "expected_args": {"ticket_id": "7f3a9c2e4b1d", "priority": "high"},
        "expected_pass": True,
        "dimensions": {"context": "good", "hint": "good", "ambiguity": "good", "human": "good"},
        "complexity": "trivial",
        "demo": {"context": 1.0, "hint": 0.3, "ambiguity": 0.05, "human": 0.95},
    },
    {
        "name": "fail_placeholder_template",
        "kind": "priority",
        "user": "USER_TEMPLATE({ticket_id}) -- insert realistic request here.",
        "additional_messages": [],
        "expected_args": {"ticket_id": "INC-742", "priority": "high"},
        "expected_pass": False,
        "dimensions": {"context": "bad", "hint": "good", "ambiguity": "bad", "human": "bad"},
        "complexity": "trivial",
        "demo": {"context": 0.1, "hint": 0.1, "ambiguity": 0.8, "human": 0.1},
    },
    {
        "name": "pass_structured_document_with_explicit_style",
        "kind": "document",
        "user": (
            "Create a sales table with Product, Quantity, and Total columns. Add one Pen row "
            "with quantity 2 and total $4.00. Use a navy, bold header with white text."
        ),
        "additional_messages": [
            {"role": "assistant", "content": "The document title is Sales and it has no table yet."}
        ],
        "expected_args": {
            "document": {
                "title": "Sales",
                "table": {
                    "headers": ["Product", "Quantity", "Total"],
                    "rows": [["Pen", 2, "$4.00"]],
                    "header_style": {"bold": True, "background": "navy", "text_color": "white"},
                },
            }
        },
        "critic_profile": "document",
        "expected_pass": True,
        "dimensions": {"context": "good", "hint": "good", "ambiguity": "good", "human": "good"},
        "complexity": "simple",
        "demo": {"context": 0.95, "hint": 0.1, "ambiguity": 0.1, "human": 0.9},
    },
    {
        "name": "fail_structured_style_without_contract",
        "kind": "document",
        "user": "Make the existing sales table look professional.",
        "additional_messages": [{"role": "assistant", "content": "The document title is Sales."}],
        "expected_args": {
            "document": {
                "title": "Sales",
                "table": {
                    "header_style": {"bold": True, "background": "navy", "text_color": "white"}
                },
            }
        },
        "expected_pass": False,
        "dimensions": {"context": "bad", "hint": "good", "ambiguity": "bad", "human": "good"},
        "complexity": "simple",
        "demo": {"context": 0.3, "hint": 0.1, "ambiguity": 0.9, "human": 0.9},
    },
    {
        "name": "pass_spreadsheet_formula_with_source_context",
        "kind": "sheet",
        "user": "In Q1, add a Total column equal to Quantity times Unit Price and make the header bold.",
        "additional_messages": [
            {
                "role": "assistant",
                "content": "Q1 has columns Product, Quantity, Unit Price and one row: Pen, 2, 2.00.",
            }
        ],
        "expected_args": {
            "sheet": {
                "name": "Q1",
                "headers": ["Product", "Quantity", "Unit Price", "Total"],
                "rows": [["Pen", 2, 2.0, "=B2*C2"]],
                "header_style": {"bold": True},
            }
        },
        "critic_profile": "sheet",
        "expected_pass": True,
        "dimensions": {"context": "good", "hint": "good", "ambiguity": "good", "human": "good"},
        "complexity": "complex",
        "demo": {"context": 0.95, "hint": 0.1, "ambiguity": 0.15, "human": 0.9},
    },
    {
        "name": "fail_spreadsheet_formula_without_source",
        "kind": "sheet",
        "user": "Clean up the spreadsheet.",
        "additional_messages": [],
        "expected_args": {
            "sheet": {"name": "Q1", "headers": ["Product", "Quantity", "Total"], "rows": []}
        },
        "expected_pass": False,
        "dimensions": {"context": "bad", "hint": "good", "ambiguity": "bad", "human": "good"},
        "complexity": "trivial",
        "demo": {"context": 0.1, "hint": 0.1, "ambiguity": 0.9, "human": 0.85},
    },
    {
        "name": "fail_conflicting_prior_instruction",
        "kind": "priority",
        "user": "Escalate the payment outage.",
        "additional_messages": [
            {"role": "assistant", "content": "Payment incident INC-742 is open."},
            {"role": "user", "content": "Do not change INC-742; keep it low priority."},
        ],
        "expected_args": {"ticket_id": "INC-742", "priority": "high"},
        "expected_pass": False,
        "dimensions": {"context": "bad", "hint": "good", "ambiguity": "bad", "human": "good"},
        "complexity": "adversarial",
        "demo": {"context": 0.2, "hint": 0.1, "ambiguity": 0.9, "human": 0.85},
    },
]

DIMENSIONS = {
    "context": {"threshold": "min_context", "direction": "minimum"},
    "hint": {"threshold": "max_hint", "direction": "maximum"},
    "ambiguity": {"threshold": "max_ambiguity", "direction": "maximum"},
    "human": {"threshold": "min_human", "direction": "minimum"},
}

SCORE_QUESTIONS = {
    "context": "contextScore",
    "hint": "hintNoul",
    "ambiguity": "ambiguityScore",
    "human": "humanNoul",
}

POLICY_FIELDS = ("min_context", "max_hint", "max_ambiguity", "min_human", "fail_on_trivial")


class FixtureJudge:
    """Offline fixture verdicts; intentionally not a semantic model."""

    def __init__(self, fixture: dict[str, Any]) -> None:
        self.fixture = fixture

    def judge(self, *, state: dict[str, Any], questions: dict[str, Any]) -> dict[str, JudgeVerdict]:
        del state
        demo = self.fixture["demo"]
        return {
            qid: JudgeVerdict(
                score=None
                if qid == "complexityChoice"
                else demo[
                    {
                        "contextScore": "context",
                        "hintNoul": "hint",
                        "ambiguityScore": "ambiguity",
                        "humanNoul": "human",
                    }[qid]
                ],
                confidence=None,
                backend="demo",
                model="illustrative-fixture",
                label=self.fixture["complexity"] if qid == "complexityChoice" else None,
            )
            for qid in questions
        }


def _critics(profile: str | None) -> list[Any]:
    if profile == "document":
        return [
            CompletenessCritic(
                "document",
                0.4,
                instructions="Require every named column, row, and header-style property.",
            ),
            GroundednessCritic(
                "document",
                0.3,
                instructions="Do not invent quantities, amounts, titles, or styles.",
            ),
            IntentionCritic(
                "document",
                0.3,
                intent="Create a readable sales table while preserving its title.",
                instructions="Judge supplied structural style metadata rather than unseen pixels.",
            ),
        ]
    if profile == "sheet":
        return [
            CompletenessCritic(
                "sheet",
                0.5,
                instructions="Require the Total column, each requested formula, and bold header metadata.",
            ),
            GroundednessCritic(
                "sheet",
                0.25,
                instructions="Formulas and values must follow the source rows; do not invent cells.",
            ),
            IntentionCritic(
                "sheet",
                0.25,
                intent="Make the Q1 spreadsheet calculate totals clearly.",
                instructions="Accept equivalent formula syntax when it computes Quantity times Unit Price.",
            ),
        ]
    return []


def build_case(fixture: dict[str, Any]) -> tuple[EvalCase, list[dict[str, Any]]]:
    kind = fixture["kind"]
    tool = {"priority": PRIORITY_TOOL, "document": DOCUMENT_TOOL, "sheet": SHEET_TOOL}[kind]
    return (
        EvalCase(
            name=fixture["name"],
            system_message=SYSTEM_MESSAGES[kind],
            user_message=fixture["user"],
            additional_messages=fixture["additional_messages"],
            expected_tool_calls=[NamedExpectedToolCall(tool["name"], fixture["expected_args"])],
            critics=_critics(fixture.get("critic_profile")),
        ),
        [tool],
    )


def _resolved_policy(policy_overrides: dict[str, Any] | None) -> dict[str, Any]:
    overrides = dict(policy_overrides or {})
    unknown = sorted(set(overrides) - set(POLICY_FIELDS))
    if unknown:
        raise ValueError(f"Unknown quality policy settings: {', '.join(unknown)}")
    grader = CaseQualityGrader(backend=FixtureJudge(CALIBRATION_CASES[0]), **overrides)
    return {name: getattr(grader, name) for name in POLICY_FIELDS}


def _thresholds(policy: dict[str, Any]) -> dict[str, float]:
    return {name: float(policy[config["threshold"]]) for name, config in DIMENSIONS.items()}


def _is_good(dimension: str, score: float, thresholds: dict[str, float]) -> bool:
    if DIMENSIONS[dimension]["direction"] == "minimum":
        return score >= thresholds[dimension]
    return score <= thresholds[dimension]


def _calibration_ranges(rows: list[dict[str, Any]], thresholds: dict[str, float]) -> dict[str, Any]:
    rows = [row for row in rows if row["status"] in ("passed", "failed")]
    result = {}
    for dimension, config in DIMENSIONS.items():
        good = [
            row["scores"][dimension]
            for row in rows
            if row["expected_dimensions"][dimension] == "good"
            and row["scores"][dimension] is not None
        ]
        bad = [
            row["scores"][dimension]
            for row in rows
            if row["expected_dimensions"][dimension] == "bad"
            and row["scores"][dimension] is not None
        ]
        item: dict[str, Any] = {
            "direction": config["direction"],
            "current": thresholds[dimension],
            "good_scores": good,
            "bad_scores": bad,
        }
        if good and bad:
            if config["direction"] == "minimum":
                lower, upper = max(bad), min(good)
                item["range"] = f"{lower:.3f} < threshold <= {upper:.3f}"
                item["suggested"] = round((lower + upper) / 2, 3)
                item["current_supported"] = lower < thresholds[dimension] <= upper
                item["separable"] = lower < upper
            else:
                lower, upper = max(good), min(bad)
                item["range"] = f"{lower:.3f} <= threshold < {upper:.3f}"
                item["suggested"] = round((lower + upper) / 2, 3)
                item["current_supported"] = lower <= thresholds[dimension] < upper
                item["separable"] = lower < upper
        else:
            item.update({
                "range": None,
                "suggested": None,
                "current_supported": None,
                "separable": None,
            })
        result[dimension] = item
    return result


def run_calibration(
    backend: JudgeBackend | None = None,
    limit: int | None = None,
    case_names: set[str] | None = None,
    policy_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fixtures = [
        fixture
        for fixture in CALIBRATION_CASES
        if case_names is None or fixture["name"] in case_names
    ]
    if limit is not None:
        fixtures = fixtures[:limit]
    policy = _resolved_policy(policy_overrides)
    thresholds = _thresholds(policy)
    rows = []
    for fixture in fixtures:
        case, tools = build_case(fixture)
        grader = CaseQualityGrader(backend=backend or FixtureJudge(fixture), **policy)
        report = grader.grade(case, tools=tools)
        scores = {}
        for name, question_id in SCORE_QUESTIONS.items():
            verdict = report.verdicts.get(question_id)
            scores[name] = verdict.score if verdict is not None else None
        adjudicated = report.status in ("passed", "failed")
        expected_dimensions = fixture["dimensions"]
        dimension_matches = {
            name: _is_good(name, scores[name], thresholds) == (expected_dimensions[name] == "good")
            if adjudicated and scores[name] is not None
            else None
            for name in DIMENSIONS
        }
        complexity = report.verdicts.get("complexityChoice")
        context = report.verdicts.get("contextScore")
        rows.append({
            "case": fixture["name"],
            "expected_pass": fixture["expected_pass"],
            "passed": report.passed,
            "status": report.status,
            "outcome_matches": report.passed == fixture["expected_pass"] if adjudicated else None,
            "expected_dimensions": expected_dimensions,
            "dimension_matches": dimension_matches,
            "scores": scores,
            "complexity": complexity.label if complexity is not None else None,
            "reasons": report.reasons,
            "model": context.model if context is not None else None,
        })
    return {
        "policy": policy,
        "cases": rows,
        "summary": {
            "fixtures": len(rows),
            "outcome_matches": sum(row["outcome_matches"] is True for row in rows),
            "dimension_mismatches": sum(
                matched is False for row in rows for matched in row["dimension_matches"].values()
            ),
        },
        "thresholds": _calibration_ranges(rows, thresholds),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("demo", "jev", "llm"), default="demo")
    parser.add_argument("--model")
    parser.add_argument(
        "--limit", type=int, help="Maximum calibration fixtures to send to a live backend."
    )
    parser.add_argument(
        "--case",
        dest="case_names",
        action="append",
        choices=[fixture["name"] for fixture in CALIBRATION_CASES],
        help="Select a named fixture; repeat to select several.",
    )
    parser.add_argument("--min-context", type=float, help="Override the minimum context score.")
    parser.add_argument("--max-hint", type=float, help="Override the maximum leakage score.")
    parser.add_argument("--max-ambiguity", type=float, help="Override the maximum ambiguity score.")
    parser.add_argument("--min-human", type=float, help="Override the minimum human-wording score.")
    parser.add_argument(
        "--fail-on-trivial",
        action="store_true",
        help="Treat a trivial complexity label as a failure.",
    )
    args = parser.parse_args()
    if args.limit is not None and not 1 <= args.limit <= len(CALIBRATION_CASES):
        parser.error(f"--limit must be between 1 and {len(CALIBRATION_CASES)}")
    if args.backend != "demo" and args.limit is None:
        parser.error("--limit is required for a live backend to make provider calls explicit")
    backend = None
    if args.backend == "jev":
        backend = JevBackend(**({"model": args.model} if args.model else {}))
    elif args.backend == "llm":
        if not args.model:
            parser.error("--model is required with --backend llm")
        backend = LLMFallbackBackend(model=args.model)
    policy_overrides = {
        name: value
        for name, value in {
            "min_context": args.min_context,
            "max_hint": args.max_hint,
            "max_ambiguity": args.max_ambiguity,
            "min_human": args.min_human,
        }.items()
        if value is not None
    }
    if args.fail_on_trivial:
        policy_overrides["fail_on_trivial"] = True
    try:
        output = run_calibration(
            backend=backend,
            limit=args.limit,
            case_names=set(args.case_names) if args.case_names else None,
            policy_overrides=policy_overrides,
        )
    except ValueError as error:
        parser.error(str(error))
    output.update({
        "mode": args.backend,
        "note": (
            "Demo verdicts are scripted fixtures, not model-accuracy evidence. "
            "Threshold ranges are evidence from this fixture set and model, not automatic policy changes."
        ),
    })
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()

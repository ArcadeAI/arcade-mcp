"""Informational case-quality reports, without invoking evaluation wrappers."""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from arcade_cli.console import console
from arcade_cli.utils import get_eval_files

if TYPE_CHECKING:
    from arcade_evals.case_quality import CaseQualityReport
    from arcade_evals.eval import EvalSuite
    from arcade_evals.judge import JudgeBackend

_DIMENSIONS = {
    "contextScore": ("Context sufficiency", "higher_is_better"),
    "complexityChoice": ("Complexity", "descriptive"),
    "hintNoul": ("Answer leakage", "lower_is_better"),
    "ambiguityScore": ("Ambiguity", "lower_is_better"),
    "humanNoul": ("Natural wording", "higher_is_better"),
}
_COMPLETE_STATUSES = {"passed", "failed"}


def _make_backend(backend: str, model: str | None) -> JudgeBackend:
    from arcade_evals.judge import JEV_MODEL_DEFAULT, JevBackend, LLMFallbackBackend

    if backend == "jev":
        return JevBackend(model=model or JEV_MODEL_DEFAULT)
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("LLM quality judge requires OPENAI_API_KEY.")
    return LLMFallbackBackend(model=model or "")


def _import_factories(path: Path) -> list[Any]:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [
        obj
        for obj in module.__dict__.values()
        if callable(obj) and getattr(obj, "__tool_eval__", False)
    ]


async def _construct_suite(wrapper: Any) -> EvalSuite:
    from arcade_evals.eval import EvalSuite

    # Preserve user decorators beneath Arcade's outer evaluation wrapper.
    factory = getattr(wrapper, "__wrapped__", None)
    if not callable(factory) or factory is wrapper:
        raise TypeError
    suite = factory()
    if inspect.isawaitable(suite):
        suite = await suite
    if not isinstance(suite, EvalSuite):
        raise TypeError
    return suite


def _suite_tools(suite: EvalSuite) -> list[dict[str, Any]]:
    from arcade_evals.eval import EvalCase

    if suite._internal_registry is None or not suite.cases:
        raise ValueError
    tools = suite._internal_registry.list_tools_for_model(tool_format="openai")
    if not isinstance(tools, list) or not all(isinstance(tool, dict) for tool in tools):
        raise TypeError
    if not all(isinstance(case, EvalCase) for case in suite.cases):
        raise TypeError
    return tools


async def _load_definitions(
    eval_files: list[Path],
) -> tuple[list[tuple[str, str, Any, list[dict[str, Any]]]], list[dict[str, str]]]:
    cases: list[tuple[str, str, Any, list[dict[str, Any]]]] = []
    errors: list[dict[str, str]] = []
    for path in sorted(eval_files):
        original_path = sys.path.copy()
        sys.path.insert(0, str(path.parent))
        try:
            factories = _import_factories(path)
        except Exception:
            errors.append({"source": str(path), "message": "Evaluation file could not be loaded."})
            sys.path[:] = original_path
            continue
        try:
            if not factories:
                errors.append({"source": str(path), "message": "No @tool_eval factories found."})
            for wrapper in factories:
                try:
                    suite = await _construct_suite(wrapper)
                except Exception:
                    errors.append({
                        "source": str(path),
                        "message": "Suite factory did not produce an EvalSuite.",
                    })
                    continue
                if suite._comparative_case_builders:
                    errors.append({
                        "source": str(path),
                        "message": "Comparative definitions are not supported by evals-quality.",
                    })
                    continue
                try:
                    tools = _suite_tools(suite)
                except Exception:
                    errors.append({
                        "source": str(path),
                        "message": "Suite has no cases or invalid case/tool definitions.",
                    })
                    continue
                cases.extend((str(path), suite.name, case, tools) for case in suite.cases)
        finally:
            sys.path[:] = original_path
    return cases, errors


def _case_result(
    source: str, suite: str, case_name: str, quality: CaseQualityReport, backend: str
) -> dict[str, Any]:
    dimensions = {}
    for qid, (label, direction) in _DIMENSIONS.items():
        verdict = quality.verdicts.get(qid)
        score = verdict.score if verdict is not None else None
        dimensions[qid] = {
            "question_id": qid,
            "label": label,
            "score": score,
            "percent": 100 * score if score is not None else None,
            "direction": direction,
            "category": verdict.label if verdict is not None else None,
            "confidence": verdict.confidence if verdict is not None else None,
            "provider": backend if verdict is not None else None,
        }
    return {
        "source": source,
        "suite": suite,
        "case": case_name,
        "track": None,
        "status": quality.status,
        "complete": quality.status in _COMPLETE_STATUSES,
        "grader_passed": quality.passed,
        "warnings": quality.reasons,
        "dimensions": dimensions,
    }


def _print_report(report: dict[str, Any]) -> None:
    console.print("Informational case quality report", style="bold")
    console.print(
        f"Backend: {report['backend']} | Configured model: {report['model']}", markup=False
    )
    console.print("Percentages describe dimension scores, not model accuracy.")
    for case in report["cases"]:
        status = {"passed": "no quality concerns", "failed": "quality concerns"}.get(
            case["status"], case["status"]
        )
        console.print(f"\n{case['suite']} / {case['case']}: {status}", markup=False)
        for dimension in case["dimensions"].values():
            if dimension["direction"] == "descriptive":
                value = dimension["category"] or "unavailable"
            elif dimension["score"] is None:
                value = "unavailable"
            else:
                value = f"{dimension['score']:.3f} ({dimension['percent']:.1f}%)"
            direction = dimension["direction"].replace("_", " ")
            confidence = dimension["confidence"]
            confidence_text = "unreported" if confidence is None else f"{confidence:.3f}"
            console.print(
                f"  {dimension['label']}: {value}; {direction}; confidence {confidence_text}",
                markup=False,
            )
        for warning in case["warnings"]:
            console.print(f"  Warning: {warning}", markup=False, style="yellow")
    for warning in report["warnings"]:
        console.print(f"Warning: {warning}", markup=False, style="yellow")
    for error in report["errors"]:
        console.print(f"Error: {error['message']} [{error['source']}]", markup=False, style="red")
    summary = report["summary"]
    console.print(
        f"\nCases: {summary['case_count']}; quality concerns: {summary['quality_concerns']}; "
        f"uncertain: {summary['uncertain_cases']}; operational errors: {len(report['errors'])}",
        markup=False,
    )
    console.print(f"Complete: {str(report['complete']).lower()}", markup=False)


def run_quality_report(
    directory: str, *, backend: str, model: str | None, output: Path | None
) -> int:
    """Return 0 for reported quality concerns/uncertainty, 1 for operational errors.

    Definitions execute user Python on import and factory construction. Only the
    evaluation wrapper and runner are bypassed; this is not a sandbox.
    """
    from arcade_evals.case_quality import CaseQualityGrader
    from arcade_evals.judge import JEV_MODEL_DEFAULT

    configured_model = model or (JEV_MODEL_DEFAULT if backend == "jev" else "")
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "informational",
        "backend": backend,
        "model": configured_model,
        "complete": False,
        "cases": [],
        "warnings": [],
        "errors": [],
    }
    try:
        judge = _make_backend(backend, model)
    except Exception:
        report["errors"].append({
            "source": "configuration",
            "message": "Quality judge could not be configured. Check its API key and model configuration.",
        })
    else:
        try:
            files = get_eval_files(directory)
            cases, errors = asyncio.run(_load_definitions(files))
            report["errors"].extend(errors)
        except Exception:
            cases = []
            report["errors"].append({
                "source": "definitions",
                "message": "Evaluation definitions could not be discovered or constructed.",
            })
        grader = CaseQualityGrader(backend=judge)
        for source, suite, case, tools in cases:
            try:
                quality = grader.grade(case, tools=tools)
                report["cases"].append(_case_result(source, suite, case.name, quality, backend))
            except Exception:
                report["errors"].append({
                    "source": source,
                    "message": "Case definition could not be graded.",
                })
        if not cases and not report["errors"]:
            report["errors"].append({
                "source": "definitions",
                "message": "No evaluation cases found.",
            })
    uncertain = sum(not case["complete"] for case in report["cases"])
    usable = sum(
        dimension["score"] is not None or dimension["category"] is not None
        for case in report["cases"]
        for dimension in case["dimensions"].values()
    )
    report["summary"] = {
        "case_count": len(report["cases"]),
        "quality_concerns": sum(case["status"] == "failed" for case in report["cases"]),
        "uncertain_cases": uncertain,
        "usable_dimensions": usable,
    }
    report["complete"] = bool(report["cases"]) and not report["errors"] and not uncertain
    if uncertain:
        report["warnings"].append(
            "Some judgments are unavailable, invalid or low confidence; inspect case statuses."
        )
    if report["cases"] and not usable:
        report["warnings"].append("No usable judgments were obtained.")
    if output is not None:
        try:
            output.write_text(
                json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        except (OSError, TypeError, ValueError):
            report["complete"] = False
            report["errors"].append({
                "source": "output",
                "message": "Quality report could not be written. Check the output path and permissions.",
            })
    _print_report(report)
    return 1 if report["errors"] else 0

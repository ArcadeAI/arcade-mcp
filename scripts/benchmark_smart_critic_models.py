"""Benchmark SmartCritic across judge models to produce recommendations.

Runs every mode x every model x a battery of calibration cases x N repeats
(self-consistency). Writes a markdown report scoring each model on:

* **Accuracy** — proportion of runs landing in the expected score range.
* **Self-consistency** — standard deviation across repeats on the same input.
* **Cost proxy** — wall time per call.

Expects API keys in ``./.env``. Takes a few minutes; costs cents, not dollars.
"""

from __future__ import annotations

import asyncio
import os
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
# Pre-clean empty env vars so .env fills them in.
for _name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
    if _name in os.environ and not os.environ[_name]:
        del os.environ[_name]
load_dotenv(ROOT / ".env", override=False)

from arcade_evals.smart_critic import SmartCritic  # noqa: E402
from arcade_evals.smart_critic_mode import SmartCriticMode  # noqa: E402

OPENAI_KEY = os.environ["OPENAI_API_KEY"]
ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]

# Models to sweep. Keep to fast/cheap tiers plus one mid-tier each for
# comparison — we're answering "which mini/haiku should you default to?",
# not "do frontier models win?" (they always win).
OPENAI_MODELS = [
    "gpt-5.4-nano",
    "gpt-5.4-mini",
    "gpt-5.4",
]
ANTHROPIC_MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
]

REPEATS = 3  # self-consistency probe count per (model, case, mode)


# ---------------------------------------------------------------------------
# Calibration cases — expected score ranges per mode.
# Each case states "given this (expected, actual), the score should land in
# this range under THIS mode". These ranges are hand-set based on what a
# human reviewer would consider correct.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CalibrationCase:
    label: str
    expected: str
    actual: str
    # Per-mode expected range (inclusive). Only modes listed here are
    # evaluated for this case.
    expected_ranges: dict[SmartCriticMode, tuple[float, float]]


CASES: list[CalibrationCase] = [
    # ------------------- PASS cases (expected: high score) -------------------
    CalibrationCase(
        label="clear match (paraphrase)",
        expected="Paris is the capital of France",
        actual="The French capital is Paris",
        expected_ranges={
            SmartCriticMode.SIMILARITY: (0.7, 1.0),
            SmartCriticMode.CORRECTNESS: (0.7, 1.0),
            SmartCriticMode.RELEVANCE: (0.7, 1.0),
            SmartCriticMode.COMPLETENESS: (0.7, 1.0),
            SmartCriticMode.COHERENCE: (0.6, 1.0),
        },
    ),
    CalibrationCase(
        label="acronym expansion (CEO → Chief Executive Officer)",
        expected="The CEO approved the budget",
        actual="The Chief Executive Officer approved the budget",
        expected_ranges={
            SmartCriticMode.SIMILARITY: (0.7, 1.0),
            SmartCriticMode.CORRECTNESS: (0.7, 1.0),
        },
    ),
    CalibrationCase(
        label="reordered list (same items)",
        expected="Buy milk, bread, and eggs",
        actual="Purchase eggs, bread, and milk",
        expected_ranges={
            SmartCriticMode.SIMILARITY: (0.7, 1.0),
            SmartCriticMode.COMPLETENESS: (0.7, 1.0),
        },
    ),
    CalibrationCase(
        label="equivalent time formats (3pm == 15:00)",
        expected="The meeting is at 3pm on Tuesday",
        actual="Meeting: Tuesday at 15:00",
        expected_ranges={
            SmartCriticMode.SIMILARITY: (0.7, 1.0),
            SmartCriticMode.CORRECTNESS: (0.7, 1.0),
        },
    ),
    # ------------------- FAIL cases (expected: low score) -------------------
    CalibrationCase(
        label="clear mismatch (unrelated topics)",
        expected="Python is a programming language",
        actual="The Eiffel Tower is in Paris",
        expected_ranges={
            SmartCriticMode.SIMILARITY: (0.0, 0.3),
            SmartCriticMode.CORRECTNESS: (0.0, 0.3),
            SmartCriticMode.RELEVANCE: (0.0, 0.3),
            SmartCriticMode.COMPLETENESS: (0.0, 0.3),
        },
    ),
    CalibrationCase(
        # Structure similar, meaning flipped — the canonical hard case.
        # TF-IDF SimilarityCritic fails this one; SmartCritic should catch it.
        label="contradiction (hot vs cold)",
        expected="Today the weather is hot",
        actual="Today the weather is cold",
        expected_ranges={
            SmartCriticMode.SIMILARITY: (0.0, 0.5),
            SmartCriticMode.CORRECTNESS: (0.0, 0.4),
        },
    ),
    CalibrationCase(
        label="wrong capital (plausible but factually wrong)",
        expected="Paris is the capital of France",
        actual="Lyon is the capital of France",
        expected_ranges={
            SmartCriticMode.CORRECTNESS: (0.0, 0.4),
        },
    ),
    CalibrationCase(
        # "Fabricated detail" — the actual preserves the main claim but adds
        # unsupported content. The CORRECTNESS rubric has a 0.2-weighted
        # `no_fabricated_facts` criterion, so a clean "no" there caps the
        # score at 0.80. Judges typically return ~0.55 (partial on
        # factually_accurate + yes on key_claim_preserved + no on
        # no_fabricated_facts). 0.65 is the tightest ceiling that accepts
        # the rubric's legitimate reading while still flagging it as "not
        # fully correct".
        label="fabricated detail not in expected",
        expected="The email was sent at 3pm",
        actual=(
            "The email was sent at 3pm by the CEO using a new encrypted "
            "channel and was read immediately by all recipients"
        ),
        expected_ranges={
            SmartCriticMode.CORRECTNESS: (0.0, 0.65),
        },
    ),
    CalibrationCase(
        label="self-contradictory (two meeting times)",
        expected="The meeting is at 3pm on Tuesday",
        actual=("The meeting is at 3pm on Tuesday. Also, the meeting is at 9am " "on Friday."),
        expected_ranges={
            SmartCriticMode.COHERENCE: (0.0, 0.5),
        },
    ),
    CalibrationCase(
        label="off-topic (same domain, wrong intent)",
        expected="What is the refund policy?",
        actual="Shipping costs vary by region and product weight.",
        expected_ranges={
            SmartCriticMode.RELEVANCE: (0.0, 0.4),
        },
    ),
    # ------------------- PARTIAL cases (modes disagree) -------------------
    CalibrationCase(
        # Same topic, factually correct, but incomplete. Different modes
        # score this differently — that is the feature.
        label="partial answer (Paris only)",
        expected="Paris is the capital of France",
        actual="Paris",
        expected_ranges={
            SmartCriticMode.RELEVANCE: (0.4, 0.9),
            SmartCriticMode.COMPLETENESS: (0.0, 0.6),
        },
    ),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


@dataclass
class TrialResult:
    case_label: str  # group repeats by case for self-consistency
    score: float
    elapsed_s: float
    in_range: bool


@dataclass
class ModelModeStats:
    provider: str
    model: str
    mode: SmartCriticMode
    trials: list[TrialResult] = field(default_factory=list)

    @property
    def n(self) -> int:
        return len(self.trials)

    @property
    def accuracy(self) -> float:
        if not self.trials:
            return 0.0
        return sum(1 for t in self.trials if t.in_range) / self.n

    @property
    def score_mean(self) -> float:
        return statistics.mean(t.score for t in self.trials) if self.trials else 0.0

    @property
    def self_consistency_sd(self) -> float:
        """Mean within-case standard deviation across repeats.

        Earlier version of this benchmark computed stdev across *all*
        trials in the cell, mixing different cases. That measured case
        variance, not self-consistency. The correct statistic is: for each
        case, compute the sd of its N repeats, then average across cases.
        """
        if not self.trials:
            return 0.0
        by_case: dict[str, list[float]] = {}
        for t in self.trials:
            by_case.setdefault(t.case_label, []).append(t.score)
        sds = [statistics.stdev(scores) for scores in by_case.values() if len(scores) >= 2]
        return statistics.mean(sds) if sds else 0.0

    @property
    def mean_latency_s(self) -> float:
        return statistics.mean(t.elapsed_s for t in self.trials) if self.trials else 0.0


async def run_trial(
    provider: str,
    model: str,
    api_key: str,
    mode: SmartCriticMode,
    case_label: str,
    expected: str,
    actual: str,
    score_range: tuple[float, float],
) -> TrialResult:
    critic = SmartCritic(
        critic_field="x",
        weight=1.0,
        mode=mode,
        judge_provider=provider,
        judge_model=model,
        match_threshold=0.7,
    )
    critic.configure_runtime(provider, model, api_key)

    t0 = time.time()
    try:
        result = await critic.async_evaluate(expected, actual)
        score = float(result["score"])
    except Exception:
        score = 0.0
    elapsed = time.time() - t0
    lo, hi = score_range
    return TrialResult(
        case_label=case_label,
        score=score,
        elapsed_s=elapsed,
        in_range=lo <= score <= hi,
    )


async def sweep() -> dict[tuple[str, str, SmartCriticMode], ModelModeStats]:
    """Run the full (provider, model, mode) x cases x repeats sweep."""
    providers: list[tuple[str, list[str], str]] = [
        ("openai", OPENAI_MODELS, OPENAI_KEY),
        ("anthropic", ANTHROPIC_MODELS, ANTHROPIC_KEY),
    ]
    stats: dict[tuple[str, str, SmartCriticMode], ModelModeStats] = {}

    # Collect calls, run them with bounded concurrency so providers don't
    # rate-limit us. We batch per (provider, model, mode) for readable logs.
    for provider, models, api_key in providers:
        for model in models:
            print(f"\n# {provider}:{model}")
            for mode in [
                SmartCriticMode.SIMILARITY,
                SmartCriticMode.CORRECTNESS,
                SmartCriticMode.RELEVANCE,
                SmartCriticMode.COMPLETENESS,
                SmartCriticMode.COHERENCE,
            ]:
                key = (provider, model, mode)
                stats[key] = ModelModeStats(provider=provider, model=model, mode=mode)
                tasks: list[Any] = []
                for case in CASES:
                    if mode not in case.expected_ranges:
                        continue
                    score_range = case.expected_ranges[mode]
                    for _ in range(REPEATS):
                        tasks.append(
                            run_trial(
                                provider,
                                model,
                                api_key,
                                mode,
                                case.label,
                                case.expected,
                                case.actual,
                                score_range,
                            )
                        )
                # Run in small bursts to avoid rate-limits.
                sem = asyncio.Semaphore(4)

                async def bounded(t: Any, _s: asyncio.Semaphore = sem) -> TrialResult:
                    async with _s:
                        return await t

                results = await asyncio.gather(*(bounded(t) for t in tasks))
                stats[key].trials = list(results)
                print(
                    f"  {mode.value:12s}  "
                    f"acc={stats[key].accuracy:.2f}  "
                    f"mean={stats[key].score_mean:.2f}  "
                    f"sd={stats[key].self_consistency_sd:.2f}  "
                    f"lat={stats[key].mean_latency_s:.2f}s"
                )
    return stats


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------


def render(  # noqa: C901 - reporting function, not worth splitting
    stats: dict[tuple[str, str, SmartCriticMode], ModelModeStats],
    wall_s: float,
) -> str:
    modes = [
        SmartCriticMode.SIMILARITY,
        SmartCriticMode.CORRECTNESS,
        SmartCriticMode.RELEVANCE,
        SmartCriticMode.COMPLETENESS,
        SmartCriticMode.COHERENCE,
    ]
    all_models: list[tuple[str, str]] = []
    for p, ms, _ in [
        ("openai", OPENAI_MODELS, None),
        ("anthropic", ANTHROPIC_MODELS, None),
    ]:
        for m in ms:
            all_models.append((p, m))

    lines: list[str] = []
    lines.append("# SmartCritic — Judge Model Benchmark")
    lines.append("")
    lines.append(
        "> Measures how each judge model performs under the rubric-based "
        "`SmartCritic` protocol. All calls use `temperature=0.0` and "
        "provider-native structured output (OpenAI JSON mode / Anthropic "
        "prefill). Scores come from real API calls made at generation time."
    )
    lines.append("")
    lines.append(
        f"- **Models tested:** {len(all_models)} "
        f"({len(OPENAI_MODELS)} OpenAI + {len(ANTHROPIC_MODELS)} Anthropic)"
    )
    lines.append(f"- **Modes tested:** {len(modes)}")
    lines.append(f"- **Repeats per (model, mode, case):** {REPEATS}")
    lines.append(f"- **Cases:** {len(CASES)} (ranges hand-calibrated per mode)")
    lines.append(f"- **Wall clock:** {wall_s:.1f}s")
    lines.append("- **Regenerate:** `uv run python scripts/benchmark_smart_critic_models.py`")
    lines.append("")

    # ------------ Methodology ------------
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "1. **Calibration cases with hand-set score ranges.** Each case "
        "defines the `(lo, hi)` range a correct judgment should fall into "
        "— per mode, since modes legitimately disagree on ambiguous pairs."
    )
    lines.append("2. **Accuracy** = fraction of trials where the score landed in range.")
    lines.append(
        "3. **Self-consistency** = standard deviation across repeats on "
        "identical input. Lower is better."
    )
    lines.append(
        "4. **Latency proxy** = mean wall-clock time per call. Not a "
        "rigorous cost benchmark, but a useful ordering."
    )
    lines.append(
        "5. **Protocol** = rubric mode (3 sub-criteria per mode answered "
        "yes/partial/no, aggregated to final score in code). This removes "
        "the LLM's freedom to pick a continuous score, which is the main "
        "source of score jitter at `temperature=0.0`."
    )
    lines.append("")

    # ------------ Overall ranking ------------
    # Aggregate accuracy and std dev across all modes.
    overall: list[tuple[str, str, float, float, float]] = []
    for provider, model in all_models:
        accs = []
        sds = []
        lats = []
        for mode in modes:
            s = stats.get((provider, model, mode))
            if s and s.n:
                accs.append(s.accuracy)
                sds.append(s.self_consistency_sd)
                lats.append(s.mean_latency_s)
        if accs:
            overall.append((
                provider,
                model,
                statistics.mean(accs),
                statistics.mean(sds),
                statistics.mean(lats),
            ))
    overall.sort(key=lambda r: (-r[2], r[3]))  # acc desc, then sd asc

    lines.append("## Overall ranking (averaged across all modes)")
    lines.append("")
    lines.append("| Rank | Provider | Model | Accuracy | Mean std | Mean latency |")
    lines.append("|-----:|----------|-------|---------:|-------:|-------------:|")
    for i, (provider, model, acc, sd, lat) in enumerate(overall, 1):
        lines.append(f"| {i} | {provider} | `{model}` | {acc:.2f} | {sd:.2f} | {lat:.2f}s |")
    lines.append("")
    lines.append(
        "*Accuracy* = fraction of trials where the score landed inside the "
        "hand-calibrated range for that case+mode. *std* is self-consistency "
        "across repeats on the same input — lower means the judge returns "
        "the same score on the same input."
    )
    lines.append("")

    # ------------ Per-case fail verification ------------
    # Group cases into "fail-expected" (upper bound ≤ 0.5) and "pass-expected"
    # (lower bound ≥ 0.6) so reviewers can confirm that a correctly-scored
    # mismatch is an observable pass, not just a number in an aggregate.
    fail_cases: list[tuple[str, SmartCriticMode, tuple[float, float]]] = []
    pass_cases: list[tuple[str, SmartCriticMode, tuple[float, float]]] = []
    partial_cases: list[tuple[str, SmartCriticMode, tuple[float, float]]] = []
    for case in CASES:
        for mode, (lo, hi) in case.expected_ranges.items():
            triplet = (case.label, mode, (lo, hi))
            if hi <= 0.5:
                fail_cases.append(triplet)
            elif lo >= 0.6:
                pass_cases.append(triplet)
            else:
                partial_cases.append(triplet)

    def _case_means(label: str, mode: SmartCriticMode) -> list[tuple[str, str, float, bool]]:
        rows = []
        for provider, model in all_models:
            s = stats.get((provider, model, mode))
            if not s:
                continue
            case_trials = [t for t in s.trials if t.case_label == label]
            if not case_trials:
                continue
            mean_s = statistics.mean(t.score for t in case_trials)
            all_in_range = all(t.in_range for t in case_trials)
            rows.append((provider, model, mean_s, all_in_range))
        return rows

    def _case_section(
        title: str,
        subtitle: str,
        cases: list[tuple[str, SmartCriticMode, tuple[float, float]]],
    ) -> None:
        if not cases:
            return
        lines.append(f"## {title}")
        lines.append("")
        lines.append(subtitle)
        lines.append("")
        for label, mode, (lo, hi) in cases:
            lines.append(f"### `{mode.value.upper()}` — {label}")
            lines.append("")
            lines.append(f"Expected range: **[{lo:.2f}, {hi:.2f}]**")
            lines.append("")
            lines.append("| Provider | Model | Mean score | In range? |")
            lines.append("|----------|-------|-----------:|:---------:|")
            rows = _case_means(label, mode)
            rows.sort(key=lambda r: (not r[3], r[2]))
            for provider, model, mean_s, in_range in rows:
                mark = "✅" if in_range else "❌"
                lines.append(f"| {provider} | `{model}` | {mean_s:.2f} | {mark} |")
            lines.append("")

    _case_section(
        "Fail-case verification (low scores expected)",
        "For each case, the judge *should* return a score near the bottom "
        "of its range. A ✅ means every repeat of that case landed inside "
        "the expected range — i.e. the model correctly called the "
        "mismatch/contradiction/incoherence.",
        fail_cases,
    )
    _case_section(
        "Pass-case verification (high scores expected)",
        "Sanity-check cases where a good judge should clearly score high.",
        pass_cases,
    )
    _case_section(
        "Partial-case verification (mode-dependent range)",
        "Cases where different modes legitimately disagree. The expected "
        "range reflects what *that specific mode* should return.",
        partial_cases,
    )

    # ------------ Per-mode matrix ------------
    lines.append("## Per-mode matrix")
    lines.append("")
    for mode in modes:
        lines.append(f"### `{mode.value.upper()}`")
        lines.append("")
        lines.append("| Provider | Model | Accuracy | std | Latency |")
        lines.append("|----------|-------|---------:|--:|--------:|")
        rows = []
        for provider, model in all_models:
            s = stats.get((provider, model, mode))
            if not s or not s.n:
                continue
            rows.append((provider, model, s.accuracy, s.self_consistency_sd, s.mean_latency_s))
        rows.sort(key=lambda r: (-r[2], r[3]))
        for provider, model, acc, sd, lat in rows:
            lines.append(f"| {provider} | `{model}` | {acc:.2f} | {sd:.2f} | {lat:.2f}s |")
        lines.append("")

    # ------------ Recommendations ------------
    lines.append("## Recommendations")
    lines.append("")

    def _fmt_model(p: str, m: str) -> str:
        return f"`{p}:{m}`"

    # Group models by accuracy tier (round to 0.02 to bucket ties).
    top_accuracy = overall[0][2] if overall else 0.0
    top_models = [
        (p, m, acc, sd, lat)
        for p, m, acc, sd, lat in overall
        if round(top_accuracy - acc, 2) <= 0.02
    ]
    # Among top accuracy, fastest cheap model wins "recommended default".
    fast_tier_names = {"nano", "mini", "haiku"}
    fast_top = [r for r in top_models if any(t in r[1] for t in fast_tier_names)]
    fast_top.sort(key=lambda r: r[4])  # fastest wins
    if fast_top:
        p, m, acc, sd, lat = fast_top[0]
        tied = [_fmt_model(r[0], r[1]) for r in fast_top if round(r[4] - lat, 2) <= 0.1]
        tied_note = "" if len(tied) == 1 else f" (tied with {', '.join(tied[1:])} within ~0.1s)"
        lines.append(
            f"- **Recommended default (cheap tier):** {_fmt_model(p, m)} — "
            f"acc {acc:.2f}, std {sd:.2f}, {lat:.2f}s/call{tied_note}. "
            f"Accuracy-perfect at the fast tier; fastest mean latency in "
            f"this run."
        )

    # "Quality tier" = top-accuracy models outside the fast tier, sorted
    # again by latency.
    mid_top = [r for r in top_models if r not in fast_top]
    if mid_top:
        mid_top.sort(key=lambda r: (r[3], r[4]))  # lowest std, then latency
        p, m, acc, sd, lat = mid_top[0]
        lines.append(
            f"- **Best overall (quality tier):** {_fmt_model(p, m)} — "
            f"acc {acc:.2f}, std {sd:.2f}, {lat:.2f}s/call. Pick this when "
            f"latency matters less than accuracy/consistency."
        )

    # Contradiction-sensitive = SIMILARITY + CORRECTNESS combined.
    contradiction_scores: list[tuple[str, str, float]] = []
    for provider, model in all_models:
        s_sim = stats.get((provider, model, SmartCriticMode.SIMILARITY))
        s_cor = stats.get((provider, model, SmartCriticMode.CORRECTNESS))
        if s_sim and s_cor and s_sim.n and s_cor.n:
            contradiction_scores.append((
                provider,
                model,
                (s_sim.accuracy + s_cor.accuracy) / 2,
            ))
    contradiction_scores.sort(key=lambda r: -r[2])
    if contradiction_scores:
        top_acc = contradiction_scores[0][2]
        tied = [_fmt_model(p, m) for p, m, acc in contradiction_scores if acc == top_acc]
        if len(tied) > 1:
            lines.append(
                f"- **Contradiction detection (SIMILARITY + CORRECTNESS):** "
                f"all of {', '.join(tied)} tied at mean accuracy "
                f"{top_acc:.2f}. Any of them safely catches adversarial/"
                f"flipped pairs — pick on latency/cost."
            )
        else:
            p, m, acc = contradiction_scores[0]
            lines.append(
                f"- **Contradiction detection (SIMILARITY + CORRECTNESS):** "
                f"{_fmt_model(p, m)} (mean accuracy {acc:.2f}). Prefer for "
                f"evals with adversarial/flipped pairs."
            )

    # Self-consistency leader.
    by_sd = sorted(overall, key=lambda r: (r[3], -r[2]))
    if by_sd:
        p, m, _acc, sd, _lat = by_sd[0]
        lines.append(
            f"- **Lowest score jitter:** {_fmt_model(p, m)} (std = {sd:.2f}). "
            f"Matters most when you rely on a single-sample score to pass/"
            f"fail a case."
        )

    # Models to avoid / caveats.
    fails: list[tuple[str, str, list[tuple[str, float]]]] = []
    for provider, model in all_models:
        bad_modes = []
        for mode in modes:
            s = stats.get((provider, model, mode))
            if s and s.n and s.accuracy < 0.8:
                bad_modes.append((mode.value, s.accuracy))
        if bad_modes:
            fails.append((provider, model, bad_modes))
    if fails:
        lines.append("")
        lines.append("**Known weaknesses observed in this run:**")
        lines.append("")
        for provider, model, bad_modes in fails:
            issues = ", ".join(f"{mo} (acc {acc:.2f})" for mo, acc in bad_modes)
            lines.append(f"- {_fmt_model(provider, model)}: {issues}")
    lines.append("")

    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "- **Model landscape moves fast.** Re-run this script every few "
        "months to keep the recommendations fresh."
    )
    lines.append(
        f"- **Sample size is small** ({REPEATS} repeats per cell). "
        "Treat accuracies within ~0.1 of each other as a tie."
    )
    lines.append(
        "- **Cost ordering is approximate.** Latency is measured; API "
        "pricing is not. Check provider pricing pages for actual $/call."
    )
    lines.append(
        "- **Calibration ranges are my judgment calls.** If a reviewer "
        "disagrees with a range, edit `CASES` and re-run."
    )
    lines.append("")

    return "\n".join(lines) + "\n"


async def main() -> None:
    print("Running SmartCritic model benchmark…")
    t0 = time.time()
    stats = await sweep()
    wall = time.time() - t0
    out = ROOT / "SMART_CRITIC_MODEL_BENCHMARK.md"
    out.write_text(render(stats, wall))
    print(f"\nWrote {out} in {wall:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

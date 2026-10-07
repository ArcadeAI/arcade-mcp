---
name: verify-arcade-evals
description: Build, calibrate, and verify Arcade tool-call evals, including judge critics, additional conversation context, and structured document or spreadsheet outputs.
---

# Verify Arcade Evals

Use this skill when adding or changing an Arcade eval definition, a judge
critic, `CaseQualityGrader`, a structured tool-call expectation, or a related
example. It gives another agent a cold-start recipe that distinguishes an
offline integration proof from a real judge calibration.

## What a completed eval must prove

An eval is trustworthy only when these are separately clear:

1. **Model-visible facts:** The system message, user message,
   `additional_messages`, and tool definitions contain every fact necessary to
   produce the expected call. Expected calls are hidden labels, never extra
   model context.
2. **Acceptance policy:** A critic accepts the valid variation the task
   intends to allow and rejects the concrete invalid variation it intends to
   catch.
3. **Execution evidence:** The normal Arcade evaluation path runs the case.
   Calling a critic directly only proves the critic, not tool selection or
   rubric aggregation.
4. **Judge calibration:** If a semantic judge is used, measured fixture
   outcomes are kept separate from scripted demo values. A green mock test is
   not evidence of a judge model's semantic accuracy.

Start from the affected case and critic. Do not expand this into a new eval
framework or change Arcade's runner for a single case.

## Create an eval case

Write the expected behavior before writing the expected call. Then make a
positive/negative pair that differs only in the property being tested.

| Element | Put it here | Do not put it here |
| --- | --- | --- |
| Tool behavior and hard policy | `system_message` | Expected call arguments |
| The request being tested | `user_message` | A critic instruction |
| Earlier dialogue, source facts, current document/sheet state | `additional_messages` | A hidden Python fixture only |
| Allowed semantic variation | critic `instructions` / `intent` | Vague user wording alone |
| Exact target call and arguments | `expected_tool_calls` | Extra conversation context |

`additional_messages` are prior messages visible to the evaluated model. Use
them when the scenario needs a ticket ID, source row, current document title,
or prior decision. Include the same messages in the actual evaluation run; a
quality review can only inspect the definition, not prove a remote client sent
them.

Avoid answer leakage. A literal ID, date, name, or source value is legitimate
input when a user could naturally provide it. Leakage is benchmark/answer
framing such as “call this exact tool with these arguments” or “copy the
reference answer.”

### Structured documents and spreadsheets

Represent the output as the actual structured tool argument: a document
object, rows, headers, formulas, and style metadata. Do not judge rendered
pixels that are absent from the argument.

For an exact requirement, put it in a model-visible message or a tool schema.
For a legitimate variant, explain acceptance through a critic. A useful
structured case has both:

```python
additional_messages=[
    {"role": "assistant", "content": "Q1 has Product, Quantity, and Unit Price."},
],
critics=[
    CompletenessCritic(
        "sheet", 0.5,
        instructions="Require a Total column and one formula per supplied row.",
    ),
    IntentionCritic(
        "sheet", 0.5,
        intent="Make Q1 totals clear",
        instructions="Accept equivalent formulas that compute Quantity times Unit Price.",
    ),
]
```

If several semantic checks target one argument, use `JudgeCriticGroup` with
one explicit backend. It batches checks for that expected/actual pair and
keeps their details. Do not group unrelated arguments or different cases.

Use a deterministic critic for a deterministic property: exact tool name,
fixed enum, numeric tolerance, date, or known field equality. Use a judge
critic for paraphrase, completeness, grounding, intent, style metadata, or
other outcomes where valid representation varies. Individual judge critics
can fall back to local behavior; a `JudgeCriticGroup` returns
`status="unavailable"` and zero credit for unavailable, malformed, or
insufficient-confidence provider answers, rather than inventing a lexical
result.

## Review quality before execution

`CaseQualityGrader` asks one provider batch with five independent questions:

| Dimension | Good result |
| --- | --- |
| `context` | A model can derive the target from model-visible facts. Higher is better. |
| `complexity` | A descriptive category: trivial, simple, complex, or adversarial. |
| `hint` | The request does not give away the reference answer. Lower is better. |
| `ambiguity` | Reasonable alternatives will not be incorrectly rejected. Lower is better. |
| `human` | The request is plausible in its domain. Higher is better. |

For documents and sheets, an exact expected header color, formula, or field is
only a label until the system/user/prior messages/tool schema/critic guidance
makes it required. “Make it look nice” cannot justify a single exact style.

The default gates are policy starting points: `min_context=0.6`,
`max_hint=0.6`, `max_ambiguity=0.4`, and `min_human=0.5`.
`fail_on_trivial=True` is opt-in. Keep custom threshold changes local to the
eval suite unless a calibration fixture set supports a new global default.

Application code can override those values per `CaseQualityGrader` instance:

```python
CaseQualityGrader(
    backend=backend,
    min_context=0.7,
    max_hint=0.5,
    max_ambiguity=0.3,
    min_human=0.6,
    fail_on_trivial=True,
)
```

All numeric values must be finite values from `0.0` through `1.0`. The
override changes only that grader; it does not mutate a suite or global policy.

## Calibration workflow

Use the checked-in paired fixture harness first:

```bash
uv run --offline --no-sync --extra dev --extra evals \
  python examples/evals/eval_case_quality_calibration.py
```

This is deliberately offline. It proves fixture wiring, expected pass/fail
policy, output shape, and threshold math; its `demo` scores do not measure a
provider.

Only run live judging after the user explicitly authorizes provider use. Use
synthetic data unless the user explicitly authorizes the supplied data, never
print or log API keys, and state a small request budget before running:

```bash
# Sends exactly N fixture batches to Jev; each batch contains five quality questions.
uv run --extra evals python examples/evals/eval_case_quality_calibration.py \
  --backend jev --limit N
```

Use repeated `--case CASE_NAME` flags with the same explicit `--limit` to
recheck only a contrastive subset after changing a rubric.

The calibration harness accepts matching per-run flags:
`--min-context`, `--max-hint`, `--max-ambiguity`, `--min-human`, and
`--fail-on-trivial`. Its JSON output echoes the effective values under
`policy`; compare that value with the threshold ranges before accepting a
change.

Record the returned model version, case names, per-dimension scores, final
pass/fail, and latency. Do not record credentials, request authorization
headers, or raw provider error bodies.

The harness reports a range for each numeric threshold. For `context` and
`human`, choose a threshold above known-bad scores and at or below known-good
scores. For `hint` and `ambiguity`, choose a threshold at or above known-good
scores and below known-bad scores. If the ranges overlap, report that the
fixtures do not separate the dimension; improve the rubric or add contrastive
cases before changing a global threshold. Do not calibrate policy from one
call, or from a final case pass/fail when a different dimension caused it.

## Required checks

Run the smallest relevant test first, then the eval scope when runtime behavior
or public examples changed:

```bash
uv run --offline --no-sync --extra dev --extra evals pytest \
  libs/tests/arcade_evals/test_case_quality.py \
  libs/tests/arcade_evals/test_judge_examples.py \
  -q -o addopts='' -p no:cacheprovider --tb=short

uv run --offline --no-sync --extra dev --extra evals pytest \
  libs/tests/arcade_evals libs/tests/sdk/test_eval*.py libs/tests/cli/test_*evals*.py \
  -q -o addopts='' -p no:cacheprovider --tb=short

uv run --offline --no-sync --extra dev ruff check --no-fix \
  libs/arcade-evals/arcade_evals libs/tests/arcade_evals examples/evals
uv run --offline --no-sync --extra dev ruff format --check \
  libs/arcade-evals/arcade_evals libs/tests/arcade_evals examples/evals
git diff --check
```

For a judge group, also exercise it through `EvalSuite` so assignment and final
scoring share the same cached batch. For a quality harness, run the default
example with sockets blocked through `test_judge_examples.py`; a provider key
present in the environment must not make demo mode live.

## Handoff evidence

Report these facts concisely:

1. The positive/negative cases and the property each pair isolates.
2. Which messages are model-visible and why the expected values follow.
3. Deterministic versus judge-based critics, including custom instructions.
4. Offline tests and their results.
5. For live work: model/version, number of batches, result intervals, and any
   mismatch. State clearly whether a result proves judge behavior, Arcade
   integration, or the generated tool-call journey.

Never silently change a fixture’s expected label to fit a provider response.
Update a fixture only when the product contract changes, and explain why.
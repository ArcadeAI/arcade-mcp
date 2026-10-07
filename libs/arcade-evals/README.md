# Arcade Evals

Evaluation toolkit for testing Arcade tools.

## Overview

Arcade Evals provides comprehensive evaluation capabilities for Arcade tools:

- **Evaluation Framework**: Cases, suites, and rubrics for systematic testing
- **Critics**: Different types of comparisons (binary, numeric, similarity, datetime)
- **Tool Evaluation**: Decorators and utilities for evaluating tool performance
- **Multi-Run Statistics**: Run each case multiple times with configurable seed policies and pass rules to measure consistency
- **Comparative Evaluation**: Compare tool performance across multiple sources/tracks side-by-side
- **Capture Mode**: Record model tool calls without scoring for debugging and baseline generation
- **Result Analysis**: Comprehensive evaluation results and reporting in multiple formats (text, markdown, HTML, JSON)

## Installation

```bash
pip install 'arcade-mcp[evals]'
```

## Usage

### Basic Evaluation

```python
from arcade_evals import EvalCase, EvalSuite, tool_eval

# Create evaluation cases
case1 = EvalCase(
    input={"query": "What is 2+2?"},
    expected_output="4"
)

case2 = EvalCase(
    input={"query": "What is the capital of France?"},
    expected_output="Paris"
)

# Create evaluation suite
suite = EvalSuite(cases=[case1, case2])

# Evaluate a tool
@tool_eval(suite)
def my_calculator(query: str) -> str:
    # Tool implementation
    return "4" if "2+2" in query else "Unknown"
```

### Using Critics

```python
from arcade_evals import NumericCritic, SimilarityCritic

# Numeric comparison
numeric_critic = NumericCritic(tolerance=0.1)
result = numeric_critic.evaluate(expected=10.0, actual=10.05)

# Similarity comparison
similarity_critic = SimilarityCritic(threshold=0.8)
result = similarity_critic.evaluate(
    expected="The capital of France is Paris",
    actual="Paris is the capital of France"
)
```

### Judge Critics

Semantic judges for text arguments. Each critic tries an explicit backend,
then Jev when `JEV_API_KEY` (or `TYPESAFE_API_KEY`) is set, then an
OpenAI-compatible LLM only when `llm_model` is set, then a local tier
(TF-IDF cosine; exact match for `IntentionCritic`).

```python
from arcade_evals import (
    CompletenessCritic,
    GroundednessCritic,
    IntentionCritic,
    SemanticSimilarityCritic,
)

SemanticSimilarityCritic(critic_field="content", weight=0.6)  # paraphrase (Jev Score)
IntentionCritic(critic_field="tone", weight=0.4, intent="Professional tone")  # (Jev Noul)
GroundednessCritic(critic_field="summary", weight=0.5)  # no invented facts (Jev Score)
CompletenessCritic(critic_field="features", weight=0.5)  # no omissions (Jev Score)
```

### Provider-neutral judge interface

`JudgeBackend` is the shared interface: `judge(state=..., questions=...)`
returns a `JudgeVerdict` for each question ID. `JevBackend` adapts Jev's
System One endpoint; `LLMFallbackBackend` adapts an OpenAI-compatible client
and can also be used directly. A custom backend implements the same method;
no registry, inheritance, or changes to Arcade's runner are needed.

```python
from openai import OpenAI
from arcade_evals import LLMFallbackBackend, SemanticSimilarityCritic

# Supply your provider's URL, API key, and model through your own configuration.
client = OpenAI(base_url=provider_url, api_key=provider_api_key)
backend = LLMFallbackBackend(client=client, model=provider_model)
critic = SemanticSimilarityCritic(critic_field="text", weight=1.0, backend=backend)
```

Supported question types are `score` (ordered levels normalized to 0..1),
`noul` (probability of yes), and `choice` (one named option). Choice verdicts
have `label` and `score=None`: a category has no implicit numerical grade.
Jev's reported Choice confidence and distribution are preserved and validated;
the generic LLM adapter returns only the category without invented confidence.
Question instructions/criteria are trusted configuration; state is evidence.

### Evaluation case quality

`CaseQualityGrader` reviews an existing `EvalCase` before model execution.
It is opt-in and sends all five questions in one backend call. It does not
modify cases, run tools, or change evaluation scores.

```python
from arcade_evals import CaseQualityGrader

grader = CaseQualityGrader(backend=backend)
for case in suite.cases:
    report = grader.grade(case)  # Optional tools=[...] supplies tool definitions.
    print(case.name, report.passed, report.reasons)
    print(report.verdicts["complexity"].label)
```

| Dimension | What it checks |
| --- | --- |
| `context` | Can the expected outcome be derived from the model-visible information? |
| `complexity` | Direct extraction, simple interpretation, dependent reasoning, or adversarial cues. |
| `hint` | Does the request leak the answer instead of testing the intended skill? |
| `ambiguity` | Could a reasonable alternative be incorrectly rejected? |
| `human` | Is the wording plausible for the task and audience? |

Literal arguments and IDs are legitimate inputs, not automatic failures.
Complexity describes coverage; `fail_on_trivial=True` optionally excludes
trivial cases. The other gates use configurable `min_context`, `max_hint`,
`max_ambiguity`, and `min_human` thresholds. Defaults are starting policies,
not calibrated guarantees: `0.6`, `0.6`, `0.4`, and `0.5`, respectively.
Each report preserves per-dimension verdicts and provider metadata. Missing or
malformed judgments raise `JudgeError`; an unavailable judge is not evidence
that the case is good or bad.

Override the policy per grader when a suite needs a different acceptance bar;
the values are validated as finite numbers from `0.0` through `1.0`:

```python
strict_quality = CaseQualityGrader(
    backend=backend,
    min_context=0.7,
    max_hint=0.5,
    max_ambiguity=0.3,
    min_human=0.6,
    fail_on_trivial=True,
)
```

These overrides affect only that `CaseQualityGrader` instance. They do not
alter the suite, its generated tool calls, or global defaults.

This is a review aid, not a proof that expected calls are correct. Tool
definitions improve the review. Explicit critic instructions, context, intent,
match/confidence thresholds, and grouped checks are included through an
allowlist; backends and credentials are excluded. Executable custom critic
behavior is not inspected. Critic context is not treated as extra information
that was available to the evaluated model. No-call cases are supported.

Runnable examples in `examples/evals/`:

- `eval_judge_critics.py`: all four critics, passing/failing illustrative scores,
  custom provider injection, cache hits, and call/latency metadata.
- `eval_case_quality.py`: two passes and four failures, including a legitimate
  literal ID and missing context, answer leakage, ambiguity, and template wording.
- `eval_case_quality_calibration.py`: eleven paired priority, document, and
  spreadsheet definitions. It defaults to scripted offline verdicts and reports
  per-dimension threshold intervals; live provider runs require an explicit
  backend and `--limit` request budget.
- `eval_grouped_judges.py`: three checks on a structured document argument,
  shared source context, one batch per pair, and integration with `EvalSuite`.

These default to **offline scripted demonstrations**, not measured semantic
accuracy. Use `--backend jev` or `--backend llm --model YOUR_MODEL` explicitly
to send the examples to a configured provider. Live outcomes may differ.

### Advanced Evaluation

```python
from arcade_evals import EvalRubric, ExpectedToolCall

# Create rubric with tool calls
rubric = EvalRubric(
    expected_tool_calls=[
        ExpectedToolCall(
            tool_name="calculator",
            parameters={"operation": "add", "a": 2, "b": 2}
        )
    ]
)

# Evaluate with rubric
suite = EvalSuite(cases=[case1], rubric=rubric)
```

### Multi-Run Evaluation

Run each case multiple times to measure consistency:

```python
# Run via the CLI
# arcade evals eval_file.py --num-runs 5 --seed random --multi-run-pass-rule majority

# Or programmatically
result = await suite.run(
    client,
    model="gpt-4o",
    num_runs=5,            # Run each case 5 times
    seed="random",         # Different seed per run
    multi_run_pass_rule="majority",  # Pass if >50% of runs pass
)
```

Multi-run results include per-case statistics:
- **Mean score** and **standard deviation** across runs
- **Per-run pass/fail** with individual scores
- **Per-critic field** score breakdowns across runs
- Configurable **pass rules**: `last` (default), `mean`, or `majority`
- Configurable **seed policies**: `constant` (fixed seed 42), `random`, or a specific integer

## License

MIT License - see LICENSE file for details.

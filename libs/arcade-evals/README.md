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

Semantic judges are explicitly enabled with `provider="jev"` or an injected
`backend`. Configure exactly one. Ambient keys and `llm_model` alone never enable
requests; `llm_model` remains an inert compatibility constructor field. The
default `fallback="none"` withholds unavailable or low-confidence judgments with
zero credit. `fallback="lexical"` explicitly permits a labeled local TF-IDF tier
(exact match for intent); its result has `status="fallback"` and `judged=False`.

```python
from arcade_evals import (
    CompletenessCritic,
    GroundednessCritic,
    IntentionCritic,
    SemanticSimilarityCritic,
)

SemanticSimilarityCritic(critic_field="content", weight=0.6, provider="jev")  # paraphrase (Jev Score)
IntentionCritic(critic_field="tone", weight=0.4, intent="Professional tone", provider="jev")  # (Jev Noul)
GroundednessCritic(critic_field="summary", weight=0.5, provider="jev")  # no invented facts (Jev Score)
CompletenessCritic(critic_field="features", weight=0.5, provider="jev")  # no omissions (Jev Score)
```

### Provider-neutral judge interface

`JudgeBackend` is the shared interface: `judge(state=..., questions=...)`
returns a `JudgeVerdict` for each question ID. `JevBackend` adapts Jev's
System One endpoint; `LLMFallbackBackend` adapts an OpenAI-compatible client
and can also be used directly. A custom backend implements the same method;
no registry, inheritance, or changes to Arcade's runner are needed.

```python
from arcade_evals import LLMFallbackBackend, SemanticSimilarityCritic

# Supply your provider's URL, API key, and model through your own configuration.
backend = LLMFallbackBackend(
    base_url=provider_url, api_key=provider_api_key, model=provider_model, timeout=20.0
)
critic = SemanticSimilarityCritic(critic_field="text", weight=1.0, backend=backend)
```

Supported question types are `score` (ordered levels normalized to 0..1),
`noul` (probability of yes), and `choice` (one named option). Choice verdicts
have `label` and `score=None`: a category has no implicit numerical grade.
Jev's reported Choice confidence and distribution are preserved and validated;
optional metadata is validated across built-in and injected adapters. Missing
confidence remains absent; no adapter invents it. Rubrics are checked before
requests. Score needs ordered levels; Noul needs `true`/`false` criteria; Choice
needs at least two named options. URLs require HTTPS, except exact loopback
hosts (`localhost`, `127.0.0.1`, `::1`) may use HTTP. Both default HTTP transports
disable redirects per instance. An injected client owns its HTTP security policy.
The LLM adapter passes per-request timeout, rejects explicit interrupted/refused
responses, accepts absent completion metadata for compatible endpoints, and
records the returned model identifier when supplied.
Question instructions/criteria are trusted configuration; state is evidence.

#### Where Jev fits and where to use other tools

Checked on 7 October 2026, `jev-1.13.0` supports bounded typed judgments over
supplied text. Reference comparison, routing and case-quality checks fit this
interface. Independent questions can share state and return separate answers;
application code owns acceptance and actions. [Models](https://docs.typesafe.ai/models),
[Introduction](https://docs.typesafe.ai/introduction).

Confidence describes the answer distribution, not guaranteed correctness.
Use code for exact arithmetic, counting and date ordering, and a generative model
or agent for writing and execution. Images, audio and video are unsupported;
use rendered inspection for visual appearance. Test ambiguous or adversarial
inputs and option ordering on domain fixtures.
[Confidence](https://docs.typesafe.ai/confidence),
[Known limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13),
[Coding agents](https://docs.typesafe.ai/introduction/coding-agents).

Hosted requests should contain only data approved for that service; keep
credentials outside state. Future versions may improve robustness, but those
improvements remain unproven here. Pin the version and re-test instead of
inheriting earlier results. [API](https://docs.typesafe.ai/api).

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
    print(report.verdicts["complexityChoice"].label)
```

| Dimension | What it checks |
| --- | --- |
| `contextScore` | Can the expected outcome be derived from the model-visible information? |
| `complexityChoice` | Direct extraction, simple interpretation, dependent reasoning, or adversarial cues. |
| `hintNoul` | Does the request leak the answer instead of testing the intended skill? |
| `ambiguityScore` | Could a reasonable alternative be incorrectly rejected? |
| `humanNoul` | Is the wording plausible for the task and audience? |

Literal arguments and IDs are legitimate inputs, not automatic failures.
Complexity describes coverage; `fail_on_trivial=True` optionally excludes
trivial cases. The other gates use configurable `min_context`, `max_hint`,
`max_ambiguity`, and `min_human` thresholds. Defaults are starting policies,
not calibrated guarantees: `0.6`, `0.6`, `0.4`, and `0.5`, respectively.
Each report preserves per-dimension verdicts and provider metadata. Missing or
malformed judgments return `passed=False` with `invalid`; transport failures
return `unavailable`, and insufficient confidence returns `low_confidence`.
An unavailable judge is not evidence that the case is good or bad.

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
  custom provider injection and request versus lifetime call/latency metadata.
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


Judgments are reused only within an `EvalCase.evaluate` call for assignment and
final scoring of the same candidate pair. There is no persistent cross-case cache
or shared context mutation. Model-visible system, user and history messages reach
the judge through `JudgeScope`; reference labels remain separate from generator
prompts. Identical labels do not establish groundedness or valid intent. Two absent
values can abstain without a request. Any unavailable judgment or critic exception
prevents a single run or repeated-run aggregation from passing, even at tiny weight.

`JudgeCriticGroup` sends all checks for one pair together. Members cannot configure
conflicting backend/provider/llm_model/fallback options. Missing, invalid or uncertain
members withhold the entire group's credit while preserving per-check diagnostic
scores, status, confidence and evidence. `judge_calls` and `judge_latency_ms` describe
the returned evaluation; instance `judge_calls_total` and `judge_latency_ms_total`
are lifetime counters. Multiple candidate pairs can require multiple requests.
Structured formulas, document edits and styles can be judged as supplied textual
or JSON evidence. These judgments do not validate rendered appearance.

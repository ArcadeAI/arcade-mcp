# Arcade Evals

Evaluation toolkit for testing Arcade tools.

## Overview

Arcade Evals provides comprehensive evaluation capabilities for Arcade tools:

- **Evaluation Framework**: Cases, suites, and rubrics for systematic testing
- **Critics**: Different types of comparisons (binary, numeric, similarity, datetime, smart LLM-as-judge)
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

### Smart (LLM-as-judge) Critic

`SmartCritic` sends the expected and actual values to a judge LLM and parses a
numeric score. It is useful when you need semantic or qualitative grading that
deterministic critics cannot express reliably — for example, when the model is
expected to paraphrase the user's request into a tool argument.

```python
from arcade_evals import SmartCritic, SmartCriticMode

# Default — falls back to the eval's running model.
SmartCritic(
    critic_field="email_content",
    weight=1.0,
    mode=SmartCriticMode.CORRECTNESS,
)

# Per-critic judge override (independent of the eval's model).
SmartCritic(
    critic_field="summary",
    weight=0.6,
    mode=SmartCriticMode.SIMILARITY,
    judge_provider="anthropic",
    judge_model="claude-sonnet-4-5-20250929",
    match_threshold=0.75,
)

# CUSTOM mode — provide your own criteria prompt.
SmartCritic(
    critic_field="subject_line",
    weight=1.0,
    mode=SmartCriticMode.CUSTOM,
    criteria_prompt="Rate whether the subject is under 8 words and on-topic.",
)
```

**Modes:** `SIMILARITY`, `CORRECTNESS`, `RELEVANCE`, `COMPLETENESS`, `COHERENCE`, `CUSTOM`.

#### Rubric-based scoring (default)

Each built-in mode uses a **3-criterion rubric** where the judge answers
each criterion with `"yes"` / `"partial"` / `"no"` (→ `1.0` / `0.5` / `0.0`)
and the final score is computed **deterministically in Python** as a
weighted sum of those answers. This replaces the earlier "LLM picks a
continuous score out of thin air" approach.

**Why it matters:** with free-score prompts at `temperature=0.0`, OpenAI's
`gpt-5.4-mini` returned scores varying by ~0.15 on identical inputs. With
rubric scoring it varies by ~0.02 — a ~7× improvement in reproducibility,
without changing the `result["score"]` contract seen by the rest of the
eval pipeline. See `SMART_CRITIC_MODEL_BENCHMARK.md` for the data.

Each mode's rubric:

| Mode | Sub-criteria (weight) |
|------|----------------------|
| `SIMILARITY` | `same_core_meaning` (0.5), `no_contradiction` (0.3), `same_key_entities` (0.2) |
| `CORRECTNESS` | `factually_accurate` (0.5), `key_claim_preserved` (0.3), `no_fabricated_facts` (0.2) |
| `RELEVANCE` | `same_topic` (0.5), `addresses_same_intent` (0.4), `free_of_off_topic` (0.1) |
| `COMPLETENESS` | `covers_main_point` (0.5), `covers_supporting_details` (0.3), `no_critical_omissions` (0.2) |
| `COHERENCE` | `internally_consistent` (0.4), `logically_sound` (0.4), `clear_and_unambiguous` (0.2) |

Per-criterion contributions are returned in `result["criteria_breakdown"]`
so you can audit which axis drove the final score.

For user-defined criteria that don't fit a rubric, use `SmartCriticMode.CUSTOM`
and supply a `criteria_prompt`. CUSTOM mode asks the judge for a single
float score in `[0, 1]` (no rubric), since arbitrary user criteria can't
be mapped to a fixed set of sub-questions.

#### Judge model recommendations

Benchmark results (see `SMART_CRITIC_MODEL_BENCHMARK.md` for methodology):

- **Recommended default (cheap tier):** `openai:gpt-5.4-mini` or
  `anthropic:claude-haiku-4-5-20251001` — both accuracy-perfect under
  rubric mode, ~1.1–1.5s/call. Pick on provider preference.
- **Best overall (quality tier):** `anthropic:claude-sonnet-4-6` —
  accuracy-perfect with the lowest score jitter (σ ≈ 0.00), but ~2× the
  latency of the cheap tier.
- **Avoid for adversarial cases:** `openai:gpt-5.4-nano` fails the
  self-contradiction COHERENCE case (scores it as coherent when it isn't).

**Judge model resolution (highest priority first):**

1. CLI override — `--judge-model provider:model --judge-override`
2. Per-critic config — `judge_provider` + `judge_model` in code
3. CLI default — `--judge-model provider:model` (no override)
4. Eval fallback — the model the eval is running with

**API key:** reuses the eval's API key when the judge provider matches;
otherwise reads `OPENAI_API_KEY` or `ANTHROPIC_API_KEY` from the environment.

**Structured output:** `SmartCritic` uses OpenAI's JSON mode
(`response_format={"type": "json_object"}`) and Anthropic's assistant-
prefill pattern to guarantee valid JSON responses. Newer Anthropic
models that reject prefill (e.g. `sonnet-4-6`) are automatically
retried without it. A tolerant regex-based fallback catches the rare
case where structured output still drifts.

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

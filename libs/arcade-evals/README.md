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

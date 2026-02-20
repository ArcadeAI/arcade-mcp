# Multi-Model Evaluation Results

**Generated:** 2026-02-06 21:01:43 UTC

**Models Compared:** `gpt-4o`, `gpt-4o-mini`, `claude-sonnet-4-20250514`

## Per-Model Summary

| Model | Passed | Failed | Warned | Total | Pass Rate |
|-------|--------|--------|--------|-------|-----------|
| `gpt-4o` | 1 | 0 | 0 | 1 | 100.0% |
| `gpt-4o-mini` | 1 | 0 | 0 | 1 | 100.0% |
| `claude-sonnet-4-20250514` | 1 | 0 | 0 | 1 | 100.0% |

**🏆 Best Overall:** `gpt-4o` (100.0% pass rate)

## Cross-Model Comparison

### 📁 LinkedIn Tools Evaluation

| Case | gpt-4o | gpt-4o-mini | claude-sonnet-4-20250514 | Best |
|------|--------|--------|--------|------|
| Run code | ✅ 100% | ✅ 89% | ✅ 100% | Tie |

<details>
<summary><strong>📋 Detailed Results</strong></summary>

#### Run code

**gpt-4o:** Score 100.0%

**Run Stats:**
- Runs: 3
- Mean Score: 100.00%
- Std Deviation: 0.00%
- Scores: 100.00%, 100.00%, 100.00%
- Seed Policy: random
- Run Seeds: 1211275093, 681762892, 1626801149
- Pass Rule: majority

**Run Details:**
- Run 1: ✅ PASSED — 100.00%

<details>
<summary>Run 1 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 1.00/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce that ...` |
| context | — | - | `None` | `None` |

</details>
- Run 2: ✅ PASSED — 100.00%

<details>
<summary>Run 2 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 1.00/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce that ...` |
| context | — | - | `None` | `None` |

</details>
- Run 3: ✅ PASSED — 100.00%

<details>
<summary>Run 3 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 1.00/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce that ...` |
| context | — | - | `None` | `None` |

</details>

**Critic Stats (normalized & weighted):**
| Field | Weight | Mean (norm %) | Std (norm %) | Mean (weighted %) | Std (weighted %) |
|-------|--------|---------------|--------------|-------------------|------------------|
| context | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% |
| text | 1.00 | 100.00% | 0.00% | 100.00% | 0.00% |


**gpt-4o-mini:** Score 89.3%

**Run Stats:**
- Runs: 3
- Mean Score: 89.29%
- Std Deviation: 3.71%
- Scores: 86.67%, 86.67%, 94.53%
- Seed Policy: random
- Run Seeds: 1028755920, 655606574, 1811611459
- Pass Rule: majority

**Run Details:**
- Run 1: ✅ PASSED — 86.67%

<details>
<summary>Run 1 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ❌ | 0.73/1.00 | `It is with great pleasure that I announce that ...` | `I am excited to announce that I am now a member...` |
| context | — | - | `None` | `None` |

</details>
- Run 2: ✅ PASSED — 86.67%

<details>
<summary>Run 2 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ❌ | 0.73/1.00 | `It is with great pleasure that I announce that ...` | `I am excited to announce that I am now a member...` |
| context | — | - | `None` | `None` |

</details>
- Run 3: ✅ PASSED — 94.53%

<details>
<summary>Run 3 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 0.89/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce I am ...` |
| context | — | - | `None` | `None` |

</details>

**Critic Stats (normalized & weighted):**
| Field | Weight | Mean (norm %) | Std (norm %) | Mean (weighted %) | Std (weighted %) |
|-------|--------|---------------|--------------|-------------------|------------------|
| context | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% |
| text | 1.00 | 78.58% | 7.41% | 78.58% | 7.41% |


**claude-sonnet-4-20250514:** Score 100.0%

**Run Stats:**
- Runs: 3
- Mean Score: 100.00%
- Std Deviation: 0.00%
- Scores: 100.00%, 100.00%, 100.00%
- Seed Policy: random (ignored)
- Pass Rule: majority

**Run Details:**
- Run 1: ✅ PASSED — 100.00%

<details>
<summary>Run 1 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 1.00/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce that ...` |
| context | — | - | `None` | `None` |

</details>
- Run 2: ✅ PASSED — 100.00%

<details>
<summary>Run 2 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 1.00/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce that ...` |
| context | — | - | `None` | `None` |

</details>
- Run 3: ✅ PASSED — 100.00%

<details>
<summary>Run 3 details</summary>

| Field | Match | Score | Expected | Actual |
|-------|-------|-------|----------|--------|
| tool_selection | ✅ | 1.00/1.00 | `Linkedin_CreateTextPost` | `Linkedin_CreateTextPost` |
| text | ✅ | 1.00/1.00 | `It is with great pleasure that I announce that ...` | `It is with great pleasure that I announce that ...` |
| context | — | - | `None` | `None` |

</details>

**Critic Stats (normalized & weighted):**
| Field | Weight | Mean (norm %) | Std (norm %) | Mean (weighted %) | Std (weighted %) |
|-------|--------|---------------|--------------|-------------------|------------------|
| context | 0.00 | 0.00% | 0.00% | 0.00% | 0.00% |
| text | 1.00 | 100.00% | 0.00% | 100.00% | 0.00% |


---

</details>

## Overall Summary

- **Unique Cases:** 1
- **Total Evaluations:** 3 (3 models)
- **Passed:** 3
- **Failed:** 0

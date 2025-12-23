# Multi-Model Output Improvements

## Overview

When running evaluations or captures with multiple models (`--models gpt-4o,gpt-4-turbo,claude-sonnet`), the current output format makes cross-model comparison difficult. This document proposes improvements to make multi-model comparisons more intuitive and useful.

## Current Behavior

### Eval Mode

Results are grouped by model, then by suite:

```
Model: gpt-4o
  📁 Linear Evaluation Suite
    PASSED Get user profile -- Score: 100.00%
    FAILED Create issue -- Score: 50.00%

Model: gpt-4-turbo
  📁 Linear Evaluation Suite
    PASSED Get user profile -- Score: 100.00%
    PASSED Create issue -- Score: 95.00%

Summary: 3 passed, 1 failed -- 75.00% pass rate
```

**Issues:**
- No side-by-side comparison of models on the same case
- Summary is aggregate only (no per-model breakdown)
- Hard to identify which model performs best

### Capture Mode

Each model's results appear as separate suite sections:

```markdown
## Linear Evaluation Suite
- **Model:** gpt-4o

### Case: Get user profile
**`Linear_WhoAmI`**
...

---

## Linear Evaluation Suite      <!-- Same suite repeated -->
- **Model:** gpt-4-turbo

### Case: Get user profile
**`Linear_WhoAmI`**
...
```

**Issues:**
- Same suite header repeated for each model
- Cases not grouped together for comparison
- No way to see differences in tool calls between models

---

## Proposed Improvements

### 1. Cross-Model Comparison Table (Eval Mode)

Add a comparison table when multiple models are used:

```markdown
## Cross-Model Comparison

### 📁 Linear Evaluation Suite

| Case | gpt-4o | gpt-4-turbo | claude-sonnet | Best |
|------|--------|-------------|---------------|------|
| Get user profile | ✅ 100% | ✅ 100% | ✅ 100% | Tie |
| Create issue | ❌ 50% | ✅ 95% | ✅ 92% | gpt-4-turbo |
| Update issue | ✅ 85% | ✅ 88% | ❌ 45% | gpt-4-turbo |
```

**Implementation notes:**
- Only show when `len(models) > 1`
- "Best" column shows model with highest score (or "Tie" if equal)
- Color-code scores: green (≥80%), yellow (50-79%), red (<50%)

### 2. Per-Model Statistics

Add breakdown in summary section:

```markdown
## Summary

### Overall
- **Total Cases:** 12
- **Pass Rate:** 75.0%

### Per-Model Breakdown

| Model | Passed | Failed | Warned | Pass Rate |
|-------|--------|--------|--------|-----------|
| gpt-4o | 3 | 1 | 0 | 75.0% |
| gpt-4-turbo | 4 | 0 | 0 | 100.0% |
| claude-sonnet | 2 | 1 | 1 | 50.0% |

**Best Overall:** gpt-4-turbo (100.0% pass rate)
```

### 3. Grouped Capture Output

Group capture results by case, showing each model's response:

```markdown
## Linear Evaluation Suite

### Case: Get user profile

**User Message:** What's my Linear profile?

#### Model Responses

<details>
<summary>gpt-4o</summary>

**`Linear_WhoAmI`**
```json
{
  "context": null
}
```

</details>

<details>
<summary>gpt-4-turbo</summary>

**`Linear_WhoAmI`**
```json
{
  "context": "user profile request"
}
```

</details>

---
```

**Alternative: Table format for simple cases**

```markdown
### Case: Get user profile

| Model | Tool Called | Arguments |
|-------|-------------|-----------|
| gpt-4o | `Linear_WhoAmI` | `{"context": null}` |
| gpt-4-turbo | `Linear_WhoAmI` | `{"context": "user profile"}` |
| claude-sonnet | `Linear_WhoAmI` | `{"context": null}` |
```

### 4. Diff View for Tool Calls (Advanced)

When models call different tools or pass different arguments, highlight the differences:

```markdown
### Case: Create issue

| Aspect | gpt-4o | gpt-4-turbo | Difference |
|--------|--------|-------------|------------|
| Tool | `Linear_CreateIssue` | `Linear_CreateIssue` | ✅ Same |
| title | `"Bug fix"` | `"Bug fix"` | ✅ Same |
| priority | `null` | `2` | ⚠️ Different |
| assignee | *(missing)* | `"user_123"` | ⚠️ Different |
```

---

## Implementation Plan

### Phase 1: Bug Fixes (Immediate) ✅ COMPLETE
- [x] Fix `_create_eval_case()` missing `rubric` argument in capture mode
- [x] Ensure comparative cases work in capture mode

### Phase 2: Eval Mode Improvements ✅ COMPLETE
- [x] Add `is_multi_model_eval()` detection in formatters
- [x] Implement cross-model comparison table
- [x] Add per-model statistics to summary
- [x] Implement for Markdown formatter
- [x] Update remaining formatters (text, html, json)

### Phase 3: Capture Mode Improvements ✅ COMPLETE
- [x] Group captures by case when multiple models
- [x] Add model comparison within each case
- [x] Support table format for simple tool calls
- [x] Implement for Markdown formatter
- [x] Update remaining formatters (text, html, json)

### Phase 4: Advanced Features (Future)
- [ ] Diff view for tool call differences
- [x] "Best model" recommendations (included in eval comparison)
- [ ] Export comparison as CSV

---

## Technical Considerations

### Data Structure Changes

Current capture result structure:
```python
CaptureResult(
    suite_name="Linear Suite",
    model="gpt-4o",
    provider="openai",
    captured_cases=[...]
)
```

For multi-model grouping, formatters need to:
1. Group `CaptureResult` objects by `suite_name`
2. Within each suite, group by case name
3. Show each model's response for that case

### Formatter Interface

Add optional parameter to formatters:
```python
class CaptureFormatter(ABC):
    @abstractmethod
    def format(
        self,
        captures: CaptureResults,
        include_context: bool = False,
        group_by_case: bool = False,  # New parameter
    ) -> str:
        ...
```

### Detection Logic

```python
def is_multi_model(captures: list[CaptureResult]) -> bool:
    models = {c.model for c in captures}
    return len(models) > 1
```

---

## Files to Modify

| File | Changes |
|------|---------|
| `formatters/base.py` | Add `group_captures_by_case()` helper |
| `formatters/markdown.py` | Update `CaptureMarkdownFormatter` |
| `formatters/html.py` | Update `CaptureHtmlFormatter` |
| `formatters/text.py` | Update `CaptureTextFormatter` |
| `formatters/json.py` | Add `grouped` format option |
| `display.py` | Update console display for multi-model |
| `evals_runner.py` | Pass grouping flag when multi-model detected |

---

## Open Questions

1. **Should we auto-detect multi-model or require a flag?**
   - Recommendation: Auto-detect based on unique models in results

2. **How to handle different providers in same run?**
   - E.g., `--models gpt-4o --provider openai` and `--models claude-sonnet --provider anthropic`
   - Currently not supported (single provider per run)

3. **Performance with many models?**
   - Table width may become unwieldy with 5+ models
   - Consider collapsible sections or pagination

4. **JSON output format for multi-model?**
   - Option A: Keep flat list, let consumer group
   - Option B: Pre-group in output structure
   - Recommendation: Option A (backwards compatible)


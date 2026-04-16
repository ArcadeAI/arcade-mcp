# SmartCritic — Reviewer Comparison Report

> Live side-by-side comparison of `SmartCritic` against the existing deterministic critics (`BinaryCritic`, `SimilarityCritic`) and across evaluation modes and judge providers. All scores are from real API calls made at generation time.

- **OpenAI judge:** `gpt-5.4-mini`
- **Anthropic judge:** `claude-haiku-4-5-20251001`
- **Total wall-clock:** 41.4s
- **Regenerate:** `uv run python scripts/generate_smart_critic_comparison.py`

## Methodology

1. **Controlled inputs.** Every test case is a hand-picked `(expected, actual)` pair chosen to expose a specific behavior — not random samples. This is a qualitative comparison, not a benchmark.
2. **Real LLM judges, not mocks.** Scores come from actual API calls to OpenAI and Anthropic using the same code path production eval runs use (`SmartCritic.async_evaluate`). The keys are loaded from a git-ignored `.env`.
3. **Match threshold = 0.7** for all SmartCritic instances. Checkmark (✅) means `score ≥ threshold`, cross (❌) means below. Scores are weighted by critic weight (here: 1.0, so the displayed score equals the judge's raw score).
4. **Non-determinism.** Judges use `temperature=0.0`. Scores are mostly reproducible within a model version, but frontier LLMs are not bitwise-deterministic even at `temperature=0` — expect ±0.10 jitter on borderline cases. Scores across providers / model versions differ more, which is why the automated tests assert ranges, not exact values.
5. **Single-sample headline numbers.** Each cell is one API call. For evals in production, run with `--num-runs N` and aggregate with `--multi-run-pass-rule mean` for stable numbers. The report deliberately keeps n=1 so the jitter is visible.

## 1. TF-IDF `SimilarityCritic` vs SmartCritic `SIMILARITY`

`SimilarityCritic` uses TF-IDF + cosine similarity. It only sees token overlap — it has no model of meaning. The cases below were chosen to expose that blind spot.

| # | Case | Expected | Actual | TF-IDF | SmartCritic | Judge comment |
|---|------|----------|--------|-------:|------------:|---------------|
| 1 | Paraphrase with no shared tokens | `Schedule a meeting at 3 PM` | `Book an appointment for fifteen hundred hours` | ❌ 0.00 | ✅ 0.72 | Both request scheduling a meeting/appointment at the same time, though the wording differs. |
| 2 | Opposite meaning with high token overlap | `Today the weather is hot` | `Today the weather is cold` | ✅ 0.67 | ❌ 0.60 | The sentences share the same structure and topic, but the key weather condition is opposite. |
| 3 | Acronym vs expansion | `The CEO approved the budget` | `The Chief Executive Officer approved the budget` | ✅ 0.62 | ✅ 1.00 | Both phrases convey the same meaning, with only an expanded form of CEO. |
| 4 | Reordered but identical meaning | `Buy milk, bread, and eggs` | `Purchase eggs, bread, and milk` | ✅ 0.67 | ✅ 1.00 | Both phrases request buying the same three items, just in a different order and with a synonym. |
| 5 | Stylistic difference only | `Trees in the West Coast` | `West Coast Trees` | ✅ 0.66 | ✅ 1.00 | Both phrases convey the same meaning with only word order changed. |

**Reading this table**

- **Case 1 (Paraphrase with no shared tokens):** TF-IDF relies on token overlap; SmartCritic understands synonyms.
- **Case 2 (Opposite meaning with high token overlap):** Swapping one word flips meaning. TF-IDF rewards the overlap; SmartCritic should recognize the contradiction.
- **Case 3 (Acronym vs expansion):** TF-IDF treats CEO and its expansion as different tokens.
- **Case 4 (Reordered but identical meaning):** Both should get high scores — sanity check.
- **Case 5 (Stylistic difference only):** A stricter TF-IDF threshold would reject this; SmartCritic sees both as the same topic.

## 2. Same pair, every mode — why the mode enum matters

SmartCritic modes evaluate different dimensions. On ambiguous pairs they legitimately disagree — that's the feature. This section runs every built-in mode against a handful of deliberately ambiguous pairs.

### Partial answer: 'Paris' given for full capital claim

- **Expected:** `Paris is the capital of France`
- **Actual:** `Paris`

| Mode | Score | Judge comment |
|------|------:|---------------|
| **SIMILARITY** | ❌ 0.35 | The actual value matches the key entity but omits the capital-of-France meaning. |
| **CORRECTNESS** | ❌ 0.40 | The actual value is only a fragment of the expected statement and omits the factual claim that Paris is the capital of France. |
| **RELEVANCE** | ✅ 0.70 | The actual value is directly related to the expected statement but is incomplete and does not express the full intended fact. |
| **COMPLETENESS** | ❌ 0.40 | The actual value includes the key subject but omits the capital-of-France relationship. |
| **COHERENCE** | ❌ 0.40 | The actual value is coherent as a fragment, but it is incomplete relative to the expected full statement. |

*SIMILARITY/RELEVANCE should be medium (same topic, less info). CORRECTNESS moderate (not wrong, incomplete). COMPLETENESS should be low (missing the 'capital' claim). COHERENCE should be high (the one-word answer is coherent).*

### Plausible but factually wrong answer

- **Expected:** `Paris is the capital of France`
- **Actual:** `Lyon is the capital of France`

| Mode | Score | Judge comment |
|------|------:|---------------|
| **SIMILARITY** | ✅ 0.75 | The statements share the same structure and mostly the same meaning, but the city name differs, making the factual claim incorrect. |
| **CORRECTNESS** | ❌ 0.50 | The country is correct, but the capital city is wrong. |
| **RELEVANCE** | ❌ 0.60 | The actual statement is about the same topic but contains a factual error about the capital city. |
| **COMPLETENESS** | ✅ 0.75 | The actual sentence matches the expected statement except for the key fact that Paris is replaced by Lyon. |
| **COHERENCE** | ❌ 0.20 | The statement is grammatically clear but factually inconsistent with the expected reference. |

*SIMILARITY should be high (similar structure/topic). CORRECTNESS should be low (factually wrong). Shows why CORRECTNESS mode matters for ground-truth arguments.*

## 3. Cross-provider agreement (OpenAI vs Anthropic judge)

Same pairs as §1, but scored by both providers' default small judges. High agreement across providers → scores aren't an artifact of one vendor's model.

| # | Case | OpenAI | Anthropic | Δ | Agree? |
|---|------|-------:|----------:|---:|:------:|
| 1 | Paraphrase with no shared tokens | ✅ 0.78 | ✅ 0.85 | 0.07 | ✅ |
| 2 | Opposite meaning with high token overlap | ❌ 0.60 | ❌ 0.10 | 0.50 | ✅ |
| 3 | Acronym vs expansion | ✅ 1.00 | ✅ 1.00 | 0.00 | ✅ |
| 4 | Reordered but identical meaning | ✅ 1.00 | ✅ 0.95 | 0.05 | ✅ |
| 5 | Stylistic difference only | ✅ 1.00 | ✅ 0.95 | 0.05 | ✅ |

## 4. `BinaryCritic` vs SmartCritic for free-text arguments

`BinaryCritic` only matches exact strings, so it's a poor fit for any argument where the model legitimately paraphrases.

| Case | Expected | Actual | Binary | SmartCritic | Judge comment |
|------|----------|--------|-------:|------------:|---------------|
| Semantically equivalent time expressions | `The meeting is at 3pm on Tuesday` | `Meeting: Tuesday at 15:00` | ❌ 0.00 | ✅ 0.92 | Both state the same meeting time and day, with only a 12-hour vs 24-hour format difference. |
| Exact-match sanity | `exact-match-string` | `exact-match-string` | ✅ 1.00 | ✅ 1.00 | The ACTUAL value matches the EXPECTED value exactly. |

- **Semantically equivalent time expressions:** Binary fails unless strings are identical; SmartCritic sees equivalence.
- **Exact-match sanity:** Both critics should agree: full score.

## 5. Self-consistency probe (jitter at `temperature=0.0`)

Each judge was called **3 times** on the same borderline pair (`Today the weather is hot` vs `Today the weather is cold`) to show the variance reviewers should expect from a single-sample eval run.

| Run | OpenAI | Anthropic |
|----:|-------:|----------:|
| 1 | ❌ 0.60 | ❌ 0.10 |
| 2 | ✅ 0.75 | ❌ 0.10 |
| 3 | ❌ 0.60 | ❌ 0.10 |
| spread | 0.15 | 0.00 |

**Takeaway.** Even with `temperature=0.0`, frontier LLMs return slightly different scores on repeated identical calls. On borderline cases the jitter can flip `match` — that is why production evals should use `--num-runs ≥ 3` with `--multi-run-pass-rule mean` or `majority`.

## 6. `CUSTOM` mode — user-defined criteria

CUSTOM mode lets you express constraints that don't fit any built-in mode — e.g. formatting rules, domain conventions, or multi-factor criteria. Both cases below use **the same custom prompt**; only the actual value changes.

### Concise subject line (on-topic, <8 words)

- **Expected:** `Q3 product launch announcement`
- **Actual:** `Announcing our Q3 product launch`
- **Criteria:** _Score 1.0 only if the ACTUAL value is an email subject line shorter than 8 words covering the same topic as EXPECTED. Penalize anything verbose._
- **Score:** ✅ **0.90**
- **Judge comment:** Same topic and under 8 words, but not an exact subject-line match.

*Short, on-topic → should score high.*

### Verbose subject line (violates <8 words)

- **Expected:** `Q3 product launch announcement`
- **Actual:** `Dear valued customers, we are absolutely thrilled to finally announce our much-awaited third-quarter product launch extravaganza`
- **Criteria:** _Score 1.0 only if the ACTUAL value is an email subject line shorter than 8 words covering the same topic as EXPECTED. Penalize anything verbose._
- **Score:** ❌ **0.00**
- **Judge comment:** The actual text is far too verbose and not a short email subject line under 8 words.

*Same topic but verbose → custom criteria should punish it.*

## Key observations from this run

- **TF-IDF scored `hot` vs `cold` at 0.67** (passes its 0.5 threshold!) while the OpenAI SmartCritic judge landed at 0.60. TF-IDF literally cannot see that swapping one antonym flips meaning. This is the single most important failure mode SmartCritic fixes.
- **Providers disagreed on the same pair by 0.50.** Anthropic's Haiku correctly scored the contradiction low (0.10); OpenAI's mini model over-rewarded the structural similarity (0.60). If judge reliability on contradictions matters for your eval, prefer Anthropic Haiku or upgrade to a larger OpenAI model.
- **SIMILARITY (0.75) and CORRECTNESS (0.50) disagreed on `Paris` → `Lyon`.** Both are working as designed: the sentences ARE similar, but one is factually wrong. Reviewers should pick the mode that matches the evaluation question — not treat them as interchangeable.
- **The OpenAI judge varied by 0.15 across 3 identical calls** on the same input at `temperature=0.0`. Practical implication: a single-sample score of 0.68 on a 0.70 threshold is inside the noise floor. Run multi-sample (`--num-runs 3 --multi-run-pass-rule mean`) for anything near a decision boundary.

## What this demonstrates

1. **`SimilarityCritic` is unreliable for semantic evaluation.** Token overlap is the wrong primitive for natural-language tool arguments.
2. **Modes are not redundant.** A pair that scores 0.9 on SIMILARITY can score 0.3 on CORRECTNESS. Pick the mode that matches what the eval is actually checking.
3. **Judge provider is a pluggable knob, not a fork in behavior.** OpenAI and Anthropic judges broadly agree on clearly good/bad pairs.
4. **CUSTOM mode scales to domain-specific constraints** without adding new critic classes.
5. **Single-sample scores are noisy near the threshold.** `temperature=0.0` is not fully deterministic for frontier LLMs — expect ±0.10 jitter. Use `--num-runs N` with `--multi-run-pass-rule mean` for any decision that rides on a close score.

## How to reproduce

```bash
# 1. Put keys in .env (git-ignored)
#    OPENAI_API_KEY=sk-...
#    ANTHROPIC_API_KEY=sk-ant-...

# 2. Regenerate this report
uv run python scripts/generate_smart_critic_comparison.py

# 3. Run the automated live tests (asserts score ranges)
uv run pytest libs/tests/arcade_evals/test_smart_critic_live.py -m smart_critic_live --no-cov -v
```

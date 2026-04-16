# SmartCritic — Judge Model Benchmark

> Measures how each judge model performs under the rubric-based `SmartCritic` protocol. All calls use `temperature=0.0` and provider-native structured output (OpenAI JSON mode / Anthropic prefill). Scores come from real API calls made at generation time.

- **Models tested:** 5 (3 OpenAI + 2 Anthropic)
- **Modes tested:** 5
- **Repeats per (model, mode, case):** 3
- **Cases:** 11 (ranges hand-calibrated per mode)
- **Wall clock:** 161.3s
- **Regenerate:** `uv run python scripts/benchmark_smart_critic_models.py`

## Methodology

1. **Calibration cases with hand-set score ranges.** Each case defines the `(lo, hi)` range a correct judgment should fall into — per mode, since modes legitimately disagree on ambiguous pairs.
2. **Accuracy** = fraction of trials where the score landed in range.
3. **Self-consistency** = standard deviation across repeats on identical input. Lower is better.
4. **Latency proxy** = mean wall-clock time per call. Not a rigorous cost benchmark, but a useful ordering.
5. **Protocol** = rubric mode (3 sub-criteria per mode answered yes/partial/no, aggregated to final score in code). This removes the LLM's freedom to pick a continuous score, which is the main source of score jitter at `temperature=0.0`.

## Overall ranking (averaged across all modes)

| Rank | Provider | Model | Accuracy | Mean σ | Mean latency |
|-----:|----------|-------|---------:|-------:|-------------:|
| 1 | anthropic | `claude-haiku-4-5-20251001` | 1.00 | 0.00 | 1.48s |
| 2 | anthropic | `claude-sonnet-4-6` | 1.00 | 0.00 | 2.16s |
| 3 | openai | `gpt-5.4` | 1.00 | 0.01 | 1.84s |
| 4 | openai | `gpt-5.4-mini` | 1.00 | 0.01 | 1.20s |
| 5 | openai | `gpt-5.4-nano` | 0.90 | 0.01 | 1.55s |

*Accuracy* = fraction of trials where the score landed inside the hand-calibrated range for that case+mode. *σ* is self-consistency across repeats on the same input — lower means the judge returns the same score on the same input.

## Fail-case verification (low scores expected)

For each case, the judge *should* return a score near the bottom of its range. A ✅ means every repeat of that case landed inside the expected range — i.e. the model correctly called the mismatch/contradiction/incoherence.

### `SIMILARITY` — clear mismatch (unrelated topics)

Expected range: **[0.00, 0.30]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-mini` | 0.00 | ✅ |
| openai | `gpt-5.4` | 0.20 | ✅ |
| openai | `gpt-5.4-nano` | 0.30 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.30 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.30 | ✅ |

### `CORRECTNESS` — clear mismatch (unrelated topics)

Expected range: **[0.00, 0.30]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-mini` | 0.00 | ✅ |
| openai | `gpt-5.4` | 0.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.00 | ✅ |
| openai | `gpt-5.4-nano` | 0.07 | ✅ |

### `RELEVANCE` — clear mismatch (unrelated topics)

Expected range: **[0.00, 0.30]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 0.00 | ✅ |
| openai | `gpt-5.4` | 0.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.00 | ✅ |
| openai | `gpt-5.4-mini` | 0.10 | ✅ |

### `COMPLETENESS` — clear mismatch (unrelated topics)

Expected range: **[0.00, 0.30]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 0.00 | ✅ |
| openai | `gpt-5.4-mini` | 0.00 | ✅ |
| openai | `gpt-5.4` | 0.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.00 | ✅ |

### `SIMILARITY` — contradiction (hot vs cold)

Expected range: **[0.00, 0.50]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4` | 0.10 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.10 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.10 | ✅ |
| openai | `gpt-5.4-nano` | 0.20 | ✅ |
| openai | `gpt-5.4-mini` | 0.20 | ✅ |

### `CORRECTNESS` — contradiction (hot vs cold)

Expected range: **[0.00, 0.40]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.00 | ✅ |
| openai | `gpt-5.4-nano` | 0.20 | ✅ |
| openai | `gpt-5.4-mini` | 0.20 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.20 | ✅ |

### `CORRECTNESS` — wrong capital (plausible but factually wrong)

Expected range: **[0.00, 0.40]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-mini` | 0.00 | ✅ |
| openai | `gpt-5.4` | 0.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.15 | ✅ |
| openai | `gpt-5.4-nano` | 0.35 | ✅ |

### `COHERENCE` — self-contradictory (two meeting times)

Expected range: **[0.00, 0.50]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4` | 0.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.10 | ✅ |
| openai | `gpt-5.4-mini` | 0.20 | ✅ |
| openai | `gpt-5.4-nano` | 0.60 | ❌ |

### `RELEVANCE` — off-topic (same domain, wrong intent)

Expected range: **[0.00, 0.40]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| anthropic | `claude-haiku-4-5-20251001` | 0.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.00 | ✅ |
| openai | `gpt-5.4-nano` | 0.07 | ✅ |
| openai | `gpt-5.4` | 0.25 | ✅ |
| openai | `gpt-5.4-mini` | 0.30 | ✅ |

## Pass-case verification (high scores expected)

Sanity-check cases where a good judge should clearly score high.

### `SIMILARITY` — clear match (paraphrase)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `CORRECTNESS` — clear match (paraphrase)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `RELEVANCE` — clear match (paraphrase)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `COMPLETENESS` — clear match (paraphrase)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `COHERENCE` — clear match (paraphrase)

Expected range: **[0.60, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `SIMILARITY` — acronym expansion (CEO → Chief Executive Officer)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `CORRECTNESS` — acronym expansion (CEO → Chief Executive Officer)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `SIMILARITY` — reordered list (same items)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `COMPLETENESS` — reordered list (same items)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `SIMILARITY` — equivalent time formats (3pm == 15:00)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

### `CORRECTNESS` — equivalent time formats (3pm == 15:00)

Expected range: **[0.70, 1.00]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 1.00 | ✅ |
| openai | `gpt-5.4-mini` | 1.00 | ✅ |
| openai | `gpt-5.4` | 1.00 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | ✅ |
| anthropic | `claude-sonnet-4-6` | 1.00 | ✅ |

## Partial-case verification (mode-dependent range)

Cases where different modes legitimately disagree. The expected range reflects what *that specific mode* should return.

### `CORRECTNESS` — fabricated detail not in expected

Expected range: **[0.00, 0.65]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-mini` | 0.30 | ✅ |
| openai | `gpt-5.4-nano` | 0.55 | ✅ |
| openai | `gpt-5.4` | 0.55 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.55 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.55 | ✅ |

### `RELEVANCE` — partial answer (Paris only)

Expected range: **[0.40, 0.90]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 0.80 | ✅ |
| openai | `gpt-5.4-mini` | 0.80 | ✅ |
| openai | `gpt-5.4` | 0.80 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.80 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.80 | ✅ |

### `COMPLETENESS` — partial answer (Paris only)

Expected range: **[0.00, 0.60]**

| Provider | Model | Mean score | In range? |
|----------|-------|-----------:|:---------:|
| openai | `gpt-5.4-nano` | 0.25 | ✅ |
| anthropic | `claude-haiku-4-5-20251001` | 0.25 | ✅ |
| anthropic | `claude-sonnet-4-6` | 0.25 | ✅ |
| openai | `gpt-5.4-mini` | 0.42 | ✅ |
| openai | `gpt-5.4` | 0.57 | ✅ |

## Per-mode matrix

### `SIMILARITY`

| Provider | Model | Accuracy | σ | Latency |
|----------|-------|---------:|--:|--------:|
| openai | `gpt-5.4-nano` | 1.00 | 0.00 | 1.51s |
| openai | `gpt-5.4-mini` | 1.00 | 0.00 | 1.12s |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | 0.00 | 1.51s |
| anthropic | `claude-sonnet-4-6` | 1.00 | 0.00 | 2.11s |
| openai | `gpt-5.4` | 1.00 | 0.01 | 1.70s |

### `CORRECTNESS`

| Provider | Model | Accuracy | σ | Latency |
|----------|-------|---------:|--:|--------:|
| openai | `gpt-5.4-mini` | 1.00 | 0.00 | 1.28s |
| openai | `gpt-5.4` | 1.00 | 0.00 | 1.99s |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | 0.00 | 1.40s |
| anthropic | `claude-sonnet-4-6` | 1.00 | 0.00 | 2.13s |
| openai | `gpt-5.4-nano` | 1.00 | 0.02 | 1.45s |

### `RELEVANCE`

| Provider | Model | Accuracy | σ | Latency |
|----------|-------|---------:|--:|--------:|
| openai | `gpt-5.4-mini` | 1.00 | 0.00 | 1.20s |
| openai | `gpt-5.4` | 1.00 | 0.00 | 1.96s |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | 0.00 | 1.42s |
| anthropic | `claude-sonnet-4-6` | 1.00 | 0.00 | 1.98s |
| openai | `gpt-5.4-nano` | 1.00 | 0.01 | 1.48s |

### `COMPLETENESS`

| Provider | Model | Accuracy | σ | Latency |
|----------|-------|---------:|--:|--------:|
| openai | `gpt-5.4-nano` | 1.00 | 0.00 | 1.55s |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | 0.00 | 1.62s |
| anthropic | `claude-sonnet-4-6` | 1.00 | 0.00 | 2.19s |
| openai | `gpt-5.4` | 1.00 | 0.01 | 1.75s |
| openai | `gpt-5.4-mini` | 1.00 | 0.04 | 1.28s |

### `COHERENCE`

| Provider | Model | Accuracy | σ | Latency |
|----------|-------|---------:|--:|--------:|
| openai | `gpt-5.4-mini` | 1.00 | 0.00 | 1.12s |
| openai | `gpt-5.4` | 1.00 | 0.00 | 1.79s |
| anthropic | `claude-haiku-4-5-20251001` | 1.00 | 0.00 | 1.43s |
| anthropic | `claude-sonnet-4-6` | 1.00 | 0.00 | 2.40s |
| openai | `gpt-5.4-nano` | 0.50 | 0.00 | 1.74s |

## Recommendations

- **Recommended default (cheap tier):** `openai:gpt-5.4-mini` — acc 1.00, σ 0.01, 1.20s/call. Accuracy-perfect at the fast tier; fastest mean latency in this run.
- **Best overall (quality tier):** `anthropic:claude-sonnet-4-6` — acc 1.00, σ 0.00, 2.16s/call. Pick this when latency matters less than accuracy/consistency.
- **Contradiction detection (SIMILARITY + CORRECTNESS):** all of `openai:gpt-5.4-nano`, `openai:gpt-5.4-mini`, `openai:gpt-5.4`, `anthropic:claude-haiku-4-5-20251001`, `anthropic:claude-sonnet-4-6` tied at mean accuracy 1.00. Any of them safely catches adversarial/flipped pairs — pick on latency/cost.
- **Lowest score jitter:** `anthropic:claude-haiku-4-5-20251001` (σ = 0.00). Matters most when you rely on a single-sample score to pass/fail a case.

**Known weaknesses observed in this run:**

- `openai:gpt-5.4-nano`: coherence (acc 0.50)

## Caveats

- **Model landscape moves fast.** Re-run this script every few months to keep the recommendations fresh.
- **Sample size is small** (3 repeats per cell). Treat accuracies within ~0.1 of each other as a tie.
- **Cost ordering is approximate.** Latency is measured; API pricing is not. Check provider pricing pages for actual $/call.
- **Calibration ranges are my judgment calls.** If a reviewer disagrees with a range, edit `CASES` and re-run.

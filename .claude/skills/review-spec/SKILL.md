---
name: review-spec
description: Use when reviewing a ticket's scenarios (`.feature` source, with legacy test-definitions.md fallback) — auto-fired by the bdd scenario-gate and re-invokable after scenario edits. Runs vacuous-pass, AODI, determinism, negative-case, and cross-cutting checks and produces a structured findings report. NOT for spec.md JTBD/AC/persona framing — that is self-review.
allowed-tools: '*'
---

# Review Spec — Scenario Quality Gate

Adversarially review a ticket's scenarios: treat them as if you're trying to break them — find the one that passes for the wrong reason, the missing rejection path, the flaky assertion. This is the bdd **scenario-gate** procedure, extracted so it runs two ways:

- **Auto-fire** — the bdd flow invokes this on entering the `scenario-gate` phase.
- **Manual re-run** — invoke `/review-spec` anytime after `define-behavior` (e.g., scenarios changed during implement and you want to re-validate). Allowed on a closed ticket too — a post-hoc audit is still readable.

Read the active ticket's `.feature` source first; use `test-definitions.md` only as the R/G/R ledger and as a legacy scenario fallback when no feature source exists. test-definitions.md is the R/G/R ledger. Run every check below against the scenarios, and present findings in the **Findings format** at the end. (Not a `spec.md` framing review — JTBD/AC/persona checks live in `self-review`.)

## Vacuous-pass test

Run this **first** — a scenario that would pass without the feature invalidates every check below it. Mentally delete the implementation and ask: _could this scenario still pass?_ If yes, it is vacuous: flag it and propose a stronger `Then`, not just a warning. (A good test is _behavioral_ — if the behavior changed, the result should change; a scenario that survives a deleted feature tests nothing.)

Common vacuous patterns, each with its fix:

- **Existence-only `Then`** ("a response is returned") → assert the actual value, not that _something_ came back.
- **Given-echo** ("Given a row with X exists … Then a read returns X") → that exercises the store, not the feature; assert something the feature must compute or change.
- **Trivially-true setup** — the `Given` already makes the `Then` true regardless of the `When` → move the real precondition out of the assertion.
- **Non-claim `Then`** ("the system remains running") → assert a falsifiable outcome the feature produces.

## AODI validation

Validate each scenario against four criteria:

| Criterion         | Check                          | Red flag                        |
| ----------------- | ------------------------------ | ------------------------------- |
| **Atomic**        | Tests ONE behavior             | Multiple When/Then pairs        |
| **Observable**    | Has externally visible outcome | Internal state only             |
| **Deterministic** | Same result on repeated runs   | Time/random/external dependency |
| **Independent**   | No ordering dependency         | "After Scenario 2 runs..."      |

## Determinism risks

Sharpen AODI's **Deterministic** check with the patterns that actually flake in CI — each with its fix:

- **Time without a wait** — a `Then` that depends on elapsed time, or asserts an async result after a fixed delay → wait on an observable condition (poll/await the state), never a bare `sleep`.
- **Order-dependent comparison** — asserting an unordered collection as if it were ordered → sort, or compare as a set, before asserting.
- **Unsequenced concurrency** — a `Then` over concurrent operations with no stated ordering → assert on the settled end-state, or name the ordering guarantee the scenario relies on.

Assertion strength (weak vs strong `Then`) isn't repeated here — it is `testing` Iron Law 2, and the vacuous-pass check above already coaches a stronger `Then`.

## Adversarial pass

After AODI validation, argue against your own scenario list: "What breaks that none of these scenarios catch?" Present any findings to the user.

One lens to always run — **negative-case coverage**: for each happy-path scenario, is there a rejection-path counterpart? Partitioning should already have produced the invalid-input classes (equivalence partitioning covers invalid ranges, not only valid ones); this pass is the backstop. Common pairs — create ↔ duplicate, read ↔ not-found, update ↔ not-allowed, act ↔ precondition-failed. Treat a gap as **should-strengthen**, not must-fix — a sibling AC often already covers the rejection: _"Happy path X has no rejection counterpart — add a scenario for path Z?"_ For one behavior across many inputs, use a `Scenario Outline`.

## Cross-cutting checks

Five lenses across the whole scenario set (not per scenario) — each asks "what's missing?":

- **Conflict** — do two scenarios contradict (one allows X, another rejects it) with no distinguishing precondition?
- **Boundary** — zero / one / max / empty / null covered where they apply?
- **Failure** — external-dependency failures covered (timeout, 5xx, malformed, partition)? Distinct from the feature's own rejections (the negative-case lens above).
- **Security** — authn/authz failures and abuse vectors covered?
- **Persona consistency** — is each scenario's triggering persona clear, and would another persona experience it differently?

## Findings format

Report findings the way safeword talks to the user — lead with the answer, structure only because a multi-finding review earns it, end with the call:

- **Lead with a tally** — `**Findings:** N must-fix, M should-strengthen, P looks-good.`
- **Three tiers** — Must Fix (correctness/structure), Should Strengthen (clarity/specificity), Looks Good (specific acknowledgement, never padding).
- **One `####` per finding** with the scenario id + a short issue; under it, **Current** (quote the G/W/T, bold the offending phrase) → why → **Proposed** (the rewrite). Fix last, so the explanation reads as the answer, not justification.
- **Bulk** — when one pattern hits ≥3 scenarios: one header, an **Affected** id list, one **Representative** quote, one **Proposed pattern**.
- **End with `**Next:**`** — the single fix to start.

```text
**Findings:** 1 must-fix, 0 should-strengthen.

#### oauth.PO1.AC2.change_applies — Then joins two assertions with "and"
Current: "Then the config shows B and later auths use B" — two independent observables.
Proposed: "Then later authentications use User Source B."

**Next:** split the AC2 scenario, then re-run the gate.
```

## After the review

When invoked **auto-fire** from the bdd scenario-gate, hand control back to `bdd/SCENARIOS.md` for the Scenario Gate Exit (assign test layers, advance the phase, work-log). When invoked **manually**, stop after presenting findings — the driver decides what to fix and whether to re-run.

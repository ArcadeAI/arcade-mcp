# Implement: Outside-in TDD

**Entry:** Agent enters `implement` phase. The ticket's `impl-plan.md` (written at scenario-gate exit, status `planned`) is the design record for this phase — follow its Approach section's test-layer assignments and build order. Begin TDD for the first unchecked scenario.

## Harness availability check (entry)

Before the first RED, confirm the project's test harness actually runs — judge from existing signals (a `test` script in the project manifest, the scaffolded acceptance lane under `features/`, the project's conventional test directory). `safeword setup` scaffolds a runnable lane into every project, so absence is the exception (pre-existing installs, projects using their own runner like pytest-bdd, brownfield repos).

**Harness present** → standard loop below, no ceremony.

**Harness absent** → behavioral tests are not yet executable for this project. Do not fake test runs and do not stall: implement using the service's **existing test patterns** (unit tests, integration tests, whatever the project already runs — for untested legacy code, characterization tests that pin current behavior are the canonical first move), keeping the same RED/GREEN/REFACTOR discipline and checkbox tracking. Then:

- Annotate the ticket work log: `- {timestamp} Harness absent; using existing service test patterns. Follow-up: wire behavioral harness.`
- Recommend a follow-up ticket (`Wire behavioral test harness for {project}`) — prompt the user; don't auto-create it.

Degradation is the intended path — no gate blocks on harness absence.

## Iron Laws

1. **NO IMPLEMENTATION UNTIL TEST FAILS FOR THE RIGHT REASON** — behavior missing, not syntax error
2. **ONLY WRITE CODE THE TEST REQUIRES** — GREEN is minimal, REFACTOR adds quality

## Test Scope

Start with the most constraining test — usually E2E or integration. Prefer the highest scope that covers the behavior with acceptable feedback speed.

### Feature-source executable path

When the scenario source is a `.feature` file and the Cucumber lane exists, RED starts by making that scenario executable through Cucumber step definitions:

- If no matching steps exist, the first RED can be `bun run test:bdd` failing with undefined or pending steps, then add the thinnest TypeScript step definitions under `steps/` or `features/steps/`.
- Keep step definitions thin; call app, API, CLI, or shell helpers from steps. Do not bury business logic in Cucumber glue.
- Use Vitest for lower-level implementation proof when it gives faster or more precise coverage, especially pure functions and module contracts.
- A scenario is not complete until both the relevant implementation tests and `test:bdd` pass, unless the feature is explicitly tagged `@manual` or `@live` with a skip reason.

### Walking Skeleton (first scenario only)

If no E2E infrastructure exists, build skeleton first: thinnest slice proving architecture works (form → API → response → UI, no real logic).

## For Each Scenario: RED → GREEN → REFACTOR

Pick first unchecked scenario from test-definitions. Cycle through RED (failing test, commit) → GREEN (minimal code to pass, commit) → REFACTOR (if needed, commit).

### Checkbox Format Contract

Mark **ONE checkbox per edit, commit after each step.** The prompt hook and quality gates parse these checkboxes — multi-checkbox edits skip quality reviews.

**Correct format** (matches template exactly):

```markdown
## Scenario: User logs in

Given a registered user
When they submit valid credentials
Then they see the dashboard

- [x] RED abc1234
- [x] GREEN def5678
- [x] REFACTOR skip: no structural improvement needed
```

**Annotation rule (enforced by hook):** every `[x]` transition must carry either a commit SHA (proving which commit did that step) or `skip: <non-empty reason>` (a deliberate, auditable omission). Bare `[x]` without an annotation is blocked at the write-time hook. Pre-existing bare `[x]` from before this rule shipped is silently allowed — the validation is forward-looking only.

At the bottom of `test-definitions.md`, add one feature-level row for the cross-scenario refactor pass (same annotation rule applies):

```markdown
## Feature-level cross-scenario refactor

- [x] cross-scenario <sha> # or `skip: <reason>`
```

**Invalid — do NOT:**

- `- [x] Red` / `- [x] green` — use ALL CAPS: `RED`, `GREEN`, `REFACTOR`
- Mark `RED` and `GREEN` in the same edit — one checkbox per edit, commit between
- `- [x] RED` with no SHA and no `skip:` — blocked at write-time
- `- [x] REFACTOR skip:` with empty or whitespace-only reason — blocked at write-time
- Reuse the same SHA across two steps in one scenario — caught at the done-gate (each step needs its own distinct commit)
- Modify test files in a REFACTOR commit — blocked at commit-time (test changes during cleanup are behavior changes in disguise)
- Add extra checkboxes like `- [ ] REVIEW` — only RED/GREEN/REFACTOR

**Evidence before claims:** Show test output, don't just claim "tests pass". Run FULL suite at GREEN to catch regressions.

### Red Flags — STOP:

| Flag                    | Action                                        |
| ----------------------- | --------------------------------------------- |
| Test passes immediately | Rewrite — you're testing nothing              |
| Syntax error            | Fix syntax, not behavior                      |
| Wrote implementation    | Delete it, return to test                     |
| Multiple tests at once  | Pick ONE                                      |
| Tautological test       | Assert on behavior, not implementation mirror |

### Refactor Decision

Assess: duplication, unclear naming, excessive length? If yes, refactor (small changes directly, structural changes via `/refactor`). If no, proceed to next scenario.

## Implement exit: reconcile the plan

All scenarios complete → reconcile `impl-plan.md` against what actually shipped, **before** advancing to verify (the stop hook blocks `verify`/`done` while the plan still says `planned`):

1. **Walk the Decisions table** — for each row ask "did we actually do this, or did we change our mind?" Update changed rows: new choice, new rationale, the abandoned choice moves into Alternatives considered.
2. **Walk Arch alignment** — for each claim ask "did the implementation honor this?" Move anything that deviated into **Known deviations** with the reason.
3. **Refresh Assessment triggers** — add triggers the implementation surfaced (e.g., "works at current scale, degrades past 10x").
4. **Flip the status line** to `**Status:** implemented`, then add the work log entry:

   ```
   - {timestamp} Complete: implement — reconciled impl plan; {N} decisions updated, {M} deviations recorded
   ```

_Worked example:_ the plan said "Decisions: parse with the shared markdown utility"; during implementation a local scan proved smaller, so the choice changed mid-implementation — the row now reads choice "local content-or-skip scan", with the shared utility recorded under Alternatives considered and the reason it lost. That update (not a rewrite of history — the alternatives column preserves it) is what reconciliation produces.

Reconciled → set `phase: verify`.

## Implement exit: independent design review (architecture review gate)

Off by default. When `.safeword/config.json` sets `architectureReviewGate: true`, the stop hook blocks `verify`/`done` for a new-flow feature until its `impl-plan.md` design has been **independently reviewed** — the same propose-then-challenge discipline the scenario-gate applies to scenarios, now applied to the design. Two requirements:

1. **Cited evidence.** The Decisions section must carry a citation — a URL or a `[n]` source-reference marker — proving the choice was weighed against real evidence (the `/figure-it-out` trace), or an auditable `skip: <reason>`.
2. **A fresh-context review.** Spawn a reviewer with **no conversation history**, handed only `impl-plan.md` and the ticket scope, to try to refute the design against its cited sources. On a pass, stamp it:

   ```bash
   bun .safeword/hooks/write-review-stamp.ts impl-plan
   ```

   The stamp binds to the plan's current content, so editing the design after review invalidates it — re-review and re-stamp.

**Cross-model (`crossModelReview: true`).** The reviewer must run on a **different model than the author**, because a same-model reviewer shares the author's blind spots (correlated errors). This means an explicit different-model subagent — **not** a `context: fork`, which inherits the author's model. Record the model you assigned:

```bash
bun .safeword/hooks/write-review-stamp.ts --model < reviewer-model-id > impl-plan
```

The gate compares that tag against the author model (captured at SessionStart); an absent tag fails closed. If no independent reviewer is available, log a deliberate `skip: <reason>` rather than stamping a same-model review.

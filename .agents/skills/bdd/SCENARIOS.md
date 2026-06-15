# Define Behavior & Scenario Gate

## Define Behavior

**Entry:** Agent enters `define-behavior` phase (after discovery or resume).

### Iron Law

**DERIVE DIMENSIONS BEFORE WRITING SCENARIOS** — systematic coverage, not intuition.

### Pipeline (5 steps)

1. **Derive dimensions** from intake artifacts (resolved questions, done-when, scope) + domain-knowledge dimensions not surfaced during intake
2. **Partition** each dimension into equivalence classes + boundary values
3. **Generate scenarios** — one per partition + boundary cases. Each scenario proves a specific **Acceptance Criterion** from intake (`spec.md`); if a scenario doesn't map to any AC, either it's testing implementation (drop it) or an AC is missing (go back and add it).
4. **Organize under rules** with card-ratio self-check (too many rules? any rules with no examples? open questions?). Rules group scenarios by the AC they prove, so every AC has ≥1 scenario and no scenario is an orphan.
5. **Present to user** (decider) — user accepts, tweaks, or adds

Save the dimension table to `dimensions.md` in the ticket folder before writing test-definitions.md (the pre-tool hook enforces this for features). For tiny features with one obvious behavioral dimension and no partitioning to enumerate, dimensions.md may instead be a single line `skip: <non-empty reason>`.

### Scenario saturation

Each propose-and-converge turn either surfaces new scenarios or doesn't. When a turn produces no new scenarios → proceed to scenario-gate.

### Concrete example

**Context:** User asked for `--dry-run` on init. Intake produced scope (show what would be created without creating), done-when (output matches real init, no side effects).

**Agent turn 1:**

> From intake I see 2 behavioral dimensions:
>
> | Dimension              | Partitions                                    |
> | ---------------------- | --------------------------------------------- |
> | Output correctness     | empty dir, existing config, conflicting files |
> | Side-effect prevention | filesystem writes, git operations             |
>
> Organized under 3 rules:
>
> **Rule: Dry-run output matches real init**
>
> - [ ] Shows expected files in empty directory
> - [ ] Shows warning when config already exists
> - [ ] Shows conflict notice for incompatible existing files
>
> **Rule: Dry-run creates no files**
>
> - [ ] No files created on disk
>
> **Rule: Dry-run skips git operations**
>
> - [ ] No git init or git add executed
>
> 3 rules, 5 scenarios, 0 open questions. The "conflicting files" partition came from domain knowledge — init currently overwrites without warning, so dry-run should surface that. Anything missing, or ready for the quality gate?

**User:** "Looks good, proceed."

**Result:** No new scenarios → scenario saturation → proceed to scenario-gate.

### Two formats: discovery vs saved

**Discovery shorthand** (in chat, presenting to user): Rule + bare scenario checkboxes — fast to read, easy to amend in conversation. This is what turn-1 above looks like.

**Saved source** (`features/<slug>.feature`): Gherkin `Feature` / `Rule` / `Scenario` with lineage as `@<jtbd-id>.AC<#>` tags. This is the executable behavior source that the Cucumber lane runs and `/review-spec`, `safeword check`, and `codify` read.

**Progress ledger** (`test-definitions.md` on disk): scenario headings plus per-scenario `- [ ] RED / GREEN / REFACTOR` sub-checkboxes. test-definitions.md is the R/G/R ledger. The prompt hook parses those checkboxes to inject TDD-step guidance during implement, and they enforce one-commit-per-step discipline. Do not duplicate Given/When/Then here when a `.feature` source exists.

```gherkin
@<jtbd-id>.AC1
Feature: Description of feature

  Rule: Description of business rule

    @<jtbd-id>.AC1
    Scenario: Partition A
      Given [context]
      When [action]
      Then [outcome]

    @<jtbd-id>.AC1
    Scenario: Partition B (boundary)
      Given [context]
      When [action]
      Then [outcome]
```

```markdown
# Test Definitions: Description of feature

Feature source: `features/<slug>.feature`

test-definitions.md is the R/G/R ledger.

## Rule: Description of business rule

### Scenario: Partition A

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR

### Scenario: Partition B (boundary)

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR
```

### Scenario construction rules

Write each saved `.feature` scenario to these rules — they head off at authoring time the defects the scenario-gate would otherwise catch later. Coaching, not a gate: when a scenario starts to break one, split it on the spot instead of accumulating violations.

- **One behavior, one `When`** — each scenario specifies a single event and its outcome. Multiple `And`-joined `Then` lines are fine when they assert facets of the _same_ outcome (a withdrawal that debits **and** dispenses **and** returns the card); a second `When`, or a second behavior, means a second scenario.
- **Outcome-oriented `Then`** — assert what is true after the `When`, never how the system gets there. "Then the order is rejected" ✓, not "Then `validateOrder()` returns false" ✗.
- **Declarative, business language** — name the intent, not the UI mechanics. "When the customer submits the order" ✓, not "When the user clicks `#submit` and waits 200ms" ✗. Reads as living documentation and survives implementation changes.
- **`Given` is state, not action** — establish the world, don't act in it. "Given the cart holds one item" ✓, not "Given the customer adds an item" ✗ (an action belongs in `When`).
- **No `or` in the `Then`** — one outcome per scenario; "returns 200 **or** 201" is two scenarios. For one behavior across many inputs, use a `Scenario Outline` with an `Examples` table, not copy-pasted scenarios.

Two of these rules mirror gate checks — **one behavior** is AODI's **Atomic**, and externally-observable outcomes are its **Observable** (both in the Scenario Quality Gate below). Author for them here; the gate still validates every scenario adversarially.

### Scenario naming: lineage scheme

Each saved `.feature` scenario carries the acceptance criterion it proves as a
Gherkin tag, so the link back to AC, JTBD, and persona is machine-checkable
rather than eyeballed:

`@<jtbd-id>.AC<#>` — the tag is the AC id from intake
(`<slug>.<persona-code><JTBD#>.AC<#>`). Long ids are fine — no truncation.
Scenario names may be plain English; keep lineage in tags, not names.

Worked example — feature `oauth-flow`, persona Platform Operator (PO), first JTBD:

| Layer        | Id                    |
| ------------ | --------------------- |
| JTBD         | `oauth-flow.PO1`      |
| AC           | `oauth-flow.PO1.AC2`  |
| Scenario tag | `@oauth-flow.PO1.AC2` |

```text
@oauth-flow.PO1.AC2
Scenario: Change association applies to subsequent auth
```

A scenario with no lineage tag is left alone — it simply proves no AC.
`safeword check` reads the tags and reports coverage gaps for in-progress tickets
as advisories (never a gate):

- **uncovered** — an AC in `spec.md` that no scenario references.
- **stale ref** — a scenario whose JTBD exists but whose `AC<#>` does not (a typo,
  or an AC that was renumbered).
- **orphan** — a scenario whose JTBD is absent from `spec.md` entirely.

### Define Behavior Exit (REQUIRED)

1. **Save scenarios** to `features/<slug>.feature`
2. **Save the R/G/R ledger** to `<namespace-root>/tickets/{id}-{slug}/test-definitions.md`
3. **Update frontmatter:** `phase: scenario-gate`
4. **Add work log entry:**

   ```
   - {timestamp} Complete: define-behavior - {N} scenarios defined across {M} rules
   ```

---

## Scenario Quality Gate

**Entry:** Agent enters `scenario-gate` phase.

Run the **`/review-spec`** skill — it is the gate procedure (vacuous-pass, AODI, determinism risks, adversarial pass + negative-case, cross-cutting checks, and the findings format). It reads the active ticket's `.feature` source when present, using `test-definitions.md` only as the R/G/R ledger, reports findings, and is re-invokable standalone after scenario edits. Apply its findings, then complete the saturation check and exit below.

### Coverage saturation

If the adversarial pass + user feedback produced new scenarios → loop back to define-behavior. If nothing new surfaced → done.

### Scenario Gate Exit (REQUIRED)

1. Each scenario passes the vacuous-pass test and AODI (Atomic, Observable, Deterministic, Independent)
2. Adversarial pass + cross-cutting checks complete; findings presented in the findings format (or confirmed clean)
3. **Write `impl-plan.md`** (sibling to `ticket.md`; scaffold from `.safeword/templates/impl-plan-template.md`) — the implementation design record, status `planned`. Five sections, each with content or `skip: <non-empty reason>`:
   - **Approach** — assign test layers + sequence the work: for each scenario pick the highest test layer that covers it with acceptable feedback speed (unit < integration < E2E), and order tasks so each builds on what's already green. For non-obvious slicing or data-model choices, run `/figure-it-out`; the architecture itself was already designed in intake. (Absorbed from the retired `decomposition` phase — see the ADR in `ARCHITECTURE.md`.)
   - **Decisions** — one table row per significant technical choice: choice, alternatives considered, rejected because.
   - **Arch alignment** — consult the project's architecture record before filling this in. Resolve the location from `paths.architecture` in `.safeword/config.json` (default `.project/architecture.md`); a file is the record itself, a directory holds one ADR per `.md` file (README.md excluded, any naming).
     - **Records exist:** read them; populate this section with the titles of the decisions this implementation honors.
     - **None recorded yet:** write `skip: no ADRs in this project yet` (the canonical "None recorded yet" state), then prompt the user before proceeding: _"No architectural decisions have been recorded yet. Consider whether this implementation introduces patterns worth documenting as the first ADR — technology choices spanning multiple features, data ownership, cross-service contracts. Draft the first ADR now, or continue and document afterward?"_ Wait for the answer (under autonomous runs: auto-continue and note the prompt in the work log).

     `safeword check` flags the stale combination structurally — content in this section while no record exists at the resolved location.

     _Worked example (both branches):_ a project with `docs/adr/0001-event-sourcing.md` writes "Honors 0001 (event sourcing): new writes append to the ledger"; a fresh project with no records writes the skip line, and the agent asks the first-ADR question before starting TDD.

   - **Known deviations** — where this deviates from arch guidance and why that's acceptable.
   - **Assessment triggers** — future changes that would prompt revisiting these choices.

   The stop hook blocks the `implement` phase for new-flow features until this file exists with all five sections satisfied.

4. **Update frontmatter:** `phase: implement`
5. **Add work log entry:**

   ```
   - {timestamp} Complete: scenario-gate - Scenarios validated (AODI) + adversarial pass; impl-plan.md written (test layers + build order in Approach)
   ```

### Optional: codify the scenarios

After the gate, `safeword codify <ticket>` derives implementation stubs from the `.feature` source — a front-loaded "N tests to make pass" board, instead of writing each test at its RED step. Cucumber acceptance proof still comes from matching step definitions and `test:bdd`.

- Default: a native vitest skeleton — one `describe` per rule, `it.todo` per scenario (`--red` for failing bodies); print to stdout or `--out <path>`.
- `--format gherkin`: prints the feature source when one exists; on legacy tickets, emits a migration `.feature` from markdown scenarios.

Either way `.feature` is the scenario source of truth. test-definitions.md is the R/G/R ledger for checkboxes and hooks.

# Planning Guide

How to write specs, user stories, and test definitions before implementation.

---

## Artifact Levels

**Triage first - answer IN ORDER, stop at first match:**

| Question                                 | Level       | Artifacts                                            |
| ---------------------------------------- | ----------- | ---------------------------------------------------- |
| User-facing feature with business value? | **feature** | Feature Spec + Test Definitions (+ Design Doc if 3+) |
| Bug, improvement, internal, or refactor? | **task**    | Task Spec with inline tests                          |
| Typo, config, or trivial change?         | **patch**   | Minimal Task Spec, existing tests                    |

**Location:** `<namespace-root>/tickets/{id}-{slug}/`

Ticket artifacts live in the ticket folder:

- `ticket.md` - Ticket definition
- `test-definitions.md` - R/G/R ledger for BDD scenarios
- `spec.md` - Feature spec (epics only)
- `design.md` - Design doc (complex features)

Executable BDD scenarios live at `features/<slug>.feature`, rooted at the app
or package that owns the behavior.

**If none fit:** Break down the work. A single task spanning all three levels should be split into separate feature + tasks.

---

## Templates

| Need                            | Template                                          |
| ------------------------------- | ------------------------------------------------- |
| feature spec                    | `.safeword/templates/feature-spec-template.md`    |
| task/patch spec                 | `.safeword/templates/task-spec-template.md`       |
| feature Test definitions        | `.safeword/templates/test-definitions-feature.md` |
| Complex feature design          | `.safeword/templates/design-doc-template.md`      |
| Architectural decision          | `.safeword/templates/architecture-template.md`    |
| Context anchor for complex work | `.safeword/templates/ticket-template.md`          |
| Execution scratch pad           | `.safeword/templates/work-log-template.md`        |

---

## Part 1: User Stories

### When to Use Each Format

| Format                         | Best For                                    | Example Trigger              |
| ------------------------------ | ------------------------------------------- | ---------------------------- |
| Standard (As a/I want/So that) | User-facing features, UI flows              | "User can do X"              |
| Given-When-Then                | API behavior, state transitions, edge cases | "When X happens, then Y"     |
| Job Story                      | Problem-solving, user motivation unclear    | "User needs to accomplish X" |

**Decision rule:** Default to Standard. Use Given-When-Then for APIs or complex state. Use Job Story when focusing on the problem, not the solution.

**Edge cases:**

- API with UI? → Standard for UI, Given-When-Then for API contract tests
- Unclear user role? → Job Story to focus on the problem first, convert to Standard later
- Technical task (refactor, upgrade)? → Skip story format, use Technical Task template

### Standard Format (Recommended)

```text
As a [role/persona]
I want [capability/feature]
So that [business value/benefit]

Acceptance Criteria:
- [Specific, testable condition 1]
- [Specific, testable condition 2]
- [Specific, testable condition 3]

Out of Scope:
- [What this story explicitly does NOT include]
```

### Given-When-Then Format (Behavior-Focused)

For feature-level work, run `/bdd`. The BDD skill walks define-behavior: derive dimensions → partition into scenarios → save executable scenarios in `features/<slug>.feature` (Rule grouping + nested Scenario + Given/When/Then + lineage `@<jtbd>.AC#` tags). `test-definitions.md` is the R/G/R ledger: it references the feature source and carries per-scenario `- [ ] RED / GREEN / REFACTOR` checkboxes for hooks. Keep scenarios **declarative** — describe _what_ the system does, not _how_ it does it — and aim for 3-5 G/W/T steps per scenario (Cucumber best practice).

### Job Story Format (Outcome-Focused)

```text
When [situation/context]
I want to [motivation/job-to-be-done]
So I can [expected outcome]
```

**Example:**

```text
When I'm debugging a failing test
I want to see the exact LLM prompt and response
So I can identify whether the issue is prompt engineering or code logic
```

---

## INVEST Validation

Before saving any story, verify it passes all six criteria:

- [ ] **Independent** - Can be completed without depending on other stories
- [ ] **Negotiable** - Details emerge through conversation, not a fixed contract
- [ ] **Valuable** - Delivers clear value to user or business
- [ ] **Estimable** - Team can estimate effort (not too vague, not too detailed)
- [ ] **Small** - Completable in one sprint/iteration (typically 1-5 days)
- [ ] **Testable** - Clear acceptance criteria define when it's done

**If a story fails any criteria, it's not ready - refine or split it.**

---

## Writing Good Acceptance Criteria

**✅ GOOD - Specific, user-facing, testable:**

- User can switch campaigns without page reload
- Response time is under 200ms
- Current campaign is visually highlighted
- Error message explains what went wrong

**❌ BAD - Vague, technical, or implementation:**

- Campaign switching works ← Too vague
- Use Zustand for state ← Implementation detail
- Database is fast ← Not user-facing
- Code is clean ← Not testable

---

## Size Guidelines

| Indicator           | Too Big | Just Right | Too Small |
| ------------------- | ------- | ---------- | --------- |
| Acceptance Criteria | 6+      | 1-5        | 0         |
| Personas/Screens    | 3+      | 1-2        | N/A       |
| Duration            | 6+ days | 1-5 days   | <1 hour   |
| **Action**          | Split   | ✅ Ship    | Combine   |

**Decision rule:** When borderline, err on the side of splitting. Smaller stories are easier to estimate and complete.

---

## Technical Constraints Section

**Purpose:** Capture non-functional requirements that inform test definitions.

**When to use:** Fill in constraints BEFORE writing test definitions. Delete sections that don't apply.

| Category       | What It Captures                 | Examples                                        |
| -------------- | -------------------------------- | ----------------------------------------------- |
| Performance    | Speed, throughput, capacity      | Response time < 200ms, 1000 concurrent users    |
| Security       | Auth, validation, rate limiting  | Sanitized inputs, session required, 100 req/min |
| Compatibility  | Browsers, devices, accessibility | Chrome 100+, iOS 14+, WCAG 2.1 AA               |
| Data           | Privacy, retention, compliance   | GDPR delete in 72h, 90-day log retention        |
| Dependencies   | Existing systems, restrictions   | Use AuthService, no new packages                |
| Infrastructure | Resources, offline, deployment   | < 512MB memory, offline-capable                 |

**Include a constraint if:**

- It affects how you write tests
- It limits implementation choices
- Violating it would fail an audit or break SLAs

---

## User Story Examples

### ✅ GOOD Story

```text
As a player with multiple campaigns
I want to switch between campaigns from the sidebar
So that I can quickly resume different games

Acceptance Criteria:
- [ ] Sidebar shows all campaigns with last-played date
- [ ] Clicking campaign loads it within 200ms
- [ ] Current campaign is highlighted

Out of Scope:
- Campaign merging/deletion (separate story)
```

### ❌ BAD Story (Too Big)

```text
As a user
I want a complete campaign management system
So that I can organize my games

Acceptance Criteria:
- [ ] Create, edit, delete campaigns
- [ ] Share campaigns with other players
- [ ] Export/import campaign data
- [ ] Search and filter campaigns
- [ ] Tag campaigns by theme
```

**Problem:** This is 5+ separate stories. Split it.

### ❌ BAD Story (No Value)

```text
As a developer
I want to refactor the GameStore
So that code is cleaner
```

**Problem:** Developer is not a user. "Cleaner code" is not user-facing value.

### ✅ BETTER (Technical Task)

```text
Technical Task: Refactor GameStore to use Immer

Why: Prevent state mutation bugs (3 bugs in last sprint)
Effort: 2-3 hours
Test: All existing tests pass, no new mutations
```

---

## Part 2: Test Definitions

### Routing by ticket type

| Type        | Path to test definitions                                                                                                |
| ----------- | ----------------------------------------------------------------------------------------------------------------------- |
| **feature** | Run `/bdd` — define-behavior derives dimensions, saves `.feature` source, and saves `test-definitions.md` as the ledger |
| **task**    | Inline test specs in the ticket spec; no separate file                                                                  |
| **patch**   | Existing tests cover it; no new test definitions                                                                        |

The rest of this section describes the canonical format the BDD skill writes to disk.

### Prerequisites (enforced by hooks)

Before `test-definitions.md` can be created, the ticket frontmatter must contain:

- `scope:` — what this ticket builds
- `out_of_scope:` — what it does NOT build
- `done_when:` — the observable outcome that signals done

`pre-tool-quality.ts` hard-blocks creation otherwise. For features, BDD additionally requires `dimensions.md` (the dimension table derived in define-behavior, partitioned into equivalence classes + boundary values) before scenarios can be written.

### Canonical format

Rule grouping (Gherkin 6+ `Rule:` keyword + Matt Wynne's Example Mapping) wraps nested `Scenario`s in `features/<slug>.feature`. Each scenario carries lineage as `@<jtbd>.AC#`. test-definitions.md is the R/G/R ledger: it lists the same scenario names with `- [ ] RED / GREEN / REFACTOR` sub-checkboxes. The R/G/R sub-checkboxes are load-bearing — `parseTddStep` in `hooks/lib/active-ticket.ts` parses them to inject TDD-step guidance during implement.

```gherkin
Feature: Init dry-run

  Rule: Dry-run shows expected output

    @init-dry-run.DEV1.AC1
    Scenario: Empty directory lists would-be files
      Given an empty target directory
      When user runs `init --dry-run`
      Then output lists files that would be created
```

```markdown
# Test Definitions: Init dry-run

Feature source: `features/init-dry-run.feature`

test-definitions.md is the R/G/R ledger.

## Rule: Dry-run shows expected output

### Scenario: Empty directory lists would-be files

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR

### Scenario: Existing config surfaces warning

- [ ] RED
- [ ] GREEN
- [ ] REFACTOR
```

### Writing scenarios

- **Declarative, not imperative** — describe _what_ the system does, not _how_ (Cucumber best practice). Avoid UI-step recipes; describe behavior.
- **3-5 G/W/T steps per scenario** — if you need more, the scenario is doing too much.
- **One When/Then pair per scenario** — atomicity (BDD AODI: Atomic, Observable, Deterministic, Independent).
- **Scenario names carry meaning** — good names make G/W/T almost redundant.

| ✅ Good                                 | ❌ Bad                                 |
| --------------------------------------- | -------------------------------------- |
| "Empty directory lists would-be files"  | "Test 1.1" (no description)            |
| "Cmd+J toggles AI pane visibility"      | "Check state" (vague)                  |
| "Invalid credentials surface 401 error" | "Verify useUIStore hook" (impl detail) |

### Testing Technical Constraints

User stories include Technical Constraints. These MUST have corresponding scenarios.

| Constraint Category | Test Type                  | What to Verify                                |
| ------------------- | -------------------------- | --------------------------------------------- |
| Performance         | Load/timing tests          | Response times, throughput, capacity          |
| Security            | Security tests             | Input sanitization, auth, rate limiting       |
| Compatibility       | Cross-browser/device tests | Browser versions, mobile, accessibility       |
| Data                | Compliance tests           | Retention, deletion, privacy rules            |
| Dependencies        | Integration tests          | Required services work, no forbidden packages |
| Infrastructure      | Resource tests             | Memory limits, offline behavior               |

### Status tracking is the checkbox state

GFM checkbox state IS the status. Don't add emoji indicators (`✅ Passing`, `❌ Not Implemented`) or coverage summaries — `scenario-format.ts` computes coverage from `- [ ]` vs `- [x]` counts, and the done gate hard-blocks if any scenario remains unchecked.

### Saved path

Feature source: `features/<slug>.feature`

Ledger: `<namespace-root>/tickets/{id}-{slug}/test-definitions.md`

---

## Ticket Folder Naming

**Structure:** `<namespace-root>/tickets/{id}-{slug}/`

**Good folder names:**

- `001-campaign-switching/`
- `012-fix-login-timeout/`

**Bad folder names:**

- `story-1/` ← Not descriptive
- `CAMPAIGN_FINAL_v2/` ← Bloated

---

## Quick Reference

**User Story Red Flags (INVEST Violations):**

- No acceptance criteria → Too vague
- > 5 acceptance criteria → Split into multiple stories
- Technical implementation details → Wrong audience
- Missing "So that" → No clear value

**Test Definition Red Flags:**

- Scenario name doesn't describe behavior → Rename
- Imperative steps (UI clicks, internals) → Rewrite declaratively
- More than 5 G/W/T steps in a scenario → Split into multiple scenarios
- Multiple When/Then pairs in one scenario → Split (AODI: Atomic)
- Missing `- [ ] RED / GREEN / REFACTOR` sub-checkboxes → Use canonical template
- Scenarios not grouped under `## Rule:` → Add rule grouping

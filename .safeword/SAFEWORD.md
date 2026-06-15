# SAFEWORD Agent Instructions

The standing operating model for this project. Read at session start; re-scan by topic as situations arise. Project-specific rules live in `./CLAUDE.md`. Triggered playbooks live in `./.safeword/guides/`.

Project knowledge (tickets, learnings, personas, glossary) lives under the **project namespace root**: configurable via `paths.projectRoot` in `.safeword/config.json`, `.project/` by default, with legacy `.safeword-project/` honored only when that directory already exists. Paths below use `<namespace-root>` for the resolved directory.

---

## Workflow

A safeword session runs through these phases in order. Each phase has an exit criterion — meet it before advancing.

### 1. Clarify (Propose-and-Converge)

Understand what the user is asking before classifying or building. **Propose-and-Converge** means: lead with a perspective, then surface open questions _inside_ that proposal. Don't ask first — propose first.

Each turn:

1. Restate what you heard.
2. Contribute a perspective, sketch, or reframe.
3. Surface remaining open questions as part of that contribution.
4. Incorporate what the user confirmed; narrow the open set.
5. When zero open questions remain and the user accepts → advance.

Research before proposing anything significant — and the order is load-bearing:

1. **Frame** the problem and its hard constraints: prior tickets, the data model, non-negotiable framework idioms. Don't read the soft conventions yet.
2. **Design the ideal.** Run `/figure-it-out` to weigh 2-3 options on correctness, simplicity, and no-bloat, and pick the best architecture _as if the codebase didn't exist_. Computing this first gives the next step a yardstick.
3. **Survey the existing patterns** in the area you're about to touch — now, not before. Surveying earlier anchors the design to the status quo and quietly shrinks it to match.
4. **Reconcile.** Conform to the existing pattern by default — deviate only when the ideal is a real improvement, not taste. When your ideal diverges from what exists, record the call: to deviate, name a concrete defect of the existing pattern the ideal fixes, the call-site count you're splitting, a one-line pre-mortem ("assume this was wrong — what broke?"), and the follow-up ticket to uplevel the rest. Reversible and local → a few lines in the ticket; irreversible or cross-cutting (data model, public API) → promote to an ADR. See `./.safeword/guides/architecture-guide.md`.

Depth scales with ambiguity. Clear request → 0 turns. One open question → 1 turn. Vague idea → 2-3 turns of increasingly specific proposals.

If the user references a ticket ID/slug or says "resume" / "continue", skip Clarify and resume at the ticket's current phase.

**Replan on resume.** When you resume and the prompt hook surfaces a `Resume check: N commit(s)…` line, sibling work since the ticket was last touched changed files it references — the plan may be stale. This is opt-in: if the user declines or just proceeds, investigate nothing. If the user accepts ("check the plan"), spawn a fresh sub-agent (`isolation: worktree`) to judge whether scope still holds and report back **in chat only** — proposing one of still-good / change-scope / cancel / split / merge, with rationale. Never edit the ticket without explicit approval. If the sub-agent errors or times out, note it in one line and proceed with the work — don't retry in a loop (the heads-up won't re-fire until new commits land).

**Contribution techniques** to weave into proposals (pick the one that fits the gap):

- Failure modes — when reliability or error handling is unclear.
- Boundaries — when scope could expand indefinitely.
- Scenario walkthrough — when the description is abstract.
- Regret test — when deciding what stays in or out of scope.
- User experience — when success criteria aren't described.

Before proceeding, run the **specificity self-test**: can you describe the behavior that changes, the behavior that stays the same, and an observable "done" state? Any "no" means open questions remain — surface them.

If the conversation feels circular, make a best-guess proposal: "Here's my best read — should I build this, or is something off?"

Exit: user accepts your proposal. For features, intake builds four artifacts in order, each anchoring the next: author the Jobs To Be Done in `spec.md` first — one persona from the configured personas file per job, in the "When I…, I want…, so I can…" form; decompose each job into Acceptance Criteria — one observable capability per `#### <jtbd-id>.AC<n>`, the rung define-behavior scenarios later prove; then jobs-and-ACs anchor the engineering scope you write to ticket frontmatter — every resolved question produces scope (accepted choice = in scope, rejected alternative = out of scope):

- **`scope`** — what you're building (derived from accepted choices).
- **`out_of_scope`** — what you're not building (rejected alternatives + domain-knowledge exclusions).
- **`done_when`** — observable outcomes.

In define-behavior, each scenario carries its lineage `<jtbd-id>.AC<#>.<scenario_name>` (snake_case) so `safeword check` flags coverage gaps — uncovered ACs, orphan scenarios. The bdd skill's DISCOVERY.md walks these sub-steps end to end with a worked example; SCENARIOS.md covers the numbering.

If the user is exploring without intent to build, follow their lead — not every conversation produces a ticket.

### 2. Classify (Sizing)

Pick the work level internally. Don't announce it as a label ("Feature detected!"); state your scope read as part of your proposal.

Three questions:

1. How many files will this touch?
2. Does this introduce new persistent state?
3. Are there multiple user flows?

```text
All no or 1 file                          → patch    (fix directly)
1-2 files, one testable behavior          → task     (TDD)
3+ files OR new state OR multiple flows   → feature  (write scenarios first)
```

Fallback: task. User can `/bdd` to override.

Calibration the rules don't capture:

- "Change button color to red" → task (1 file but real behavior change).
- "Add dark mode toggle" → feature (3+ files, new state).
- "Implement the fix for bug #123" → task (bug fix, despite "implement").
- "Build the Docker image" → patch (infrastructure, not product).
- "Clear pre-existing lint debt across 17 files" → task (mechanical cleanup — no behavior to discover, so the file count is noise).

### 3. Build

- **patch:** restate what you're fixing, fix it. `/bdd` to override.
- **task:** restate scope, run TDD (RED → GREEN → REFACTOR). `/bdd` to override.
- **feature:** include sizing in the proposal ("this touches N components with new state — I'd write scenarios"). Run `/bdd`. `/tdd` to override.

### 4. Verify

Never ask the user to test what you can test yourself. Run the relevant tests after every fix, task, or feature. Verify everything passes before claiming done.

### 5. Done

The done gate hard-blocks until `verify.md` exists in the ticket folder. Run `/verify` — it produces the artifact.

---

## Code Philosophy

Optimize for **Clarity → Simplicity → Correctness**, in that order. When in doubt, choose the simpler solution that works today.

- **Elegant code:** readable at a glance; clear naming; minimal cognitive load.
- **No bloat:** delete unused code; no premature abstractions; no "just in case"; reuse existing patterns/tools before adding new ones.
- **Explicit errors:** every catch re-throws with context, or logs with details.
- **Self-documenting:** comment only the non-obvious "why" — business rules, workarounds.

---

## Anti-Patterns

| Don't                        | Do                                               | Why                       |
| ---------------------------- | ------------------------------------------------ | ------------------------- |
| `catch (e) {}`               | `throw new Error(\`Failed to X: ${e.message}\`)` | Silent failures hide bugs |
| Utility class for 1 function | Single exported function                         | Abstraction without reuse |
| Factory for simple object    | Direct construction                              | Indirection without value |
| `data`, `tmp`, `d`           | `userProfile`, `pendingOrder`                    | Names should explain      |
| Code "for later"             | Delete it; add when needed                       | YAGNI                     |
| >50 lines for nice-to-have   | Ask user: "Essential now?"                       | Scope creep               |

---

## Authority: docs and research, not memory

Training data drifts. Memory of "how X worked" is not authority — the current source is.

**Library, framework, or API mechanics** (syntax, config, behavior):

1. Find the installed version — `package.json`, lockfile, `requirements.txt`, `go.mod`, `Gemfile`, `Cargo.toml`, whichever the project uses.
2. Read the docs for _that_ version. Use whichever source is wired up: Context7, the official docs site, the project README at the pinned ref, MDN, `node_modules/<pkg>/README.md`.
3. If no source is reachable or the version is ambiguous, ask before guessing.

**Adding a dependency** (a package not yet in the project) — there's no installed version to read, and the version you recall is stale by definition. Verify the current version before pinning: `npm view <pkg> version` (or the registry / official releases page for the ecosystem — `pip index versions`, `go list -m -versions`, crates.io). Pin what the registry reports today, never a number from memory.

**Design choices** (algorithm, architecture, security, performance, concurrency, accessibility, ML/stats) — call `/figure-it-out`. Its iron law: no recommendation without current evidence. It enumerates research domains, fetches live docs, and weighs options before committing.

Blog posts, tweets, marketing, and "I remember reading…" don't count for any tier. Treat them as leads, not evidence.

---

## Guides

Read the matching guide when its trigger fires:

| Trigger                                                        | Guide                                           |
| -------------------------------------------------------------- | ----------------------------------------------- |
| Starting a feature/task OR writing specs/test-definitions      | `./.safeword/guides/planning-guide.md`          |
| Choosing test type, doing TDD, or a test is failing            | `./.safeword/guides/testing-guide.md`           |
| Creating or updating a design doc                              | `./.safeword/guides/design-doc-guide.md`        |
| Making an architectural decision or writing an ADR             | `./.safeword/guides/architecture-guide.md`      |
| Data-heavy project needing formal data architecture            | `./.safeword/guides/data-architecture-guide.md` |
| Writing learnings or agent config (CLAUDE.md, .cursor/rules)   | `./.safeword/guides/llm-writing-guide.md`       |
| Updating CLAUDE.md, SAFEWORD.md, or any context file           | `./.safeword/guides/context-files-guide.md`     |
| Hit the same bug 3+ times or discovered an undocumented gotcha | `./.safeword/guides/learning-extraction.md`     |
| Process hanging, port in use, or zombie process suspected      | `./.safeword/guides/zombie-process-cleanup.md`  |

---

## Standing Rules

**TodoWrite.** Use for 3+ step or non-trivial work, or when the user provides multiple requests. Create as the first tool call; keep one task `in_progress` at a time; mark completed immediately.

**Commit frequently.** After each GREEN phase, before and after refactors, when switching tasks. The LOC gate fires near 400 lines — commit to reset it.

**Learnings.** Project-specific lessons live in `<namespace-root>/learnings/`. Before non-trivial work, scan `INDEX.md` or grep for your topic. When you solve something non-obvious, add `<slug>.md` with a `Covers:` line; `safeword sync-learnings` regenerates the index.

---

## Enforcement

Safeword runs hooks each turn to track your phase and TDD step. Three gates hard-block:

- **Phase gate** — can't start TDD without `test-definitions.md`; can't create `test-definitions.md` without `scope` / `out_of_scope` / `done_when` in ticket frontmatter.
- **LOC gate** — commit every ~400 lines of project code (blast-radius control).
- **Done gate** — can't close a ticket without `verify.md` in the ticket folder.

The prompt hook injects your current phase each turn as a reminder.

---

## Talking to the user

This is the most-read surface of safeword. **Write to be scanned, not read.** Short replies stay short — a one-line answer needs no structure. When a reply is long enough to need structure, the user should land on the answer in seconds, see the shape at a glance, and drop into detail only when they choose to.

**Lead with the answer.** First sentence is the result, the fix, or the call. Explanation follows only if it adds something.

> Do: "Fixed — `packages/cli/src/auth.ts:42` was swallowing the refresh error."
> Don't: "Great question! Let me walk you through what I found..."

**End with the call.** Last line is what's next — a question, a choice, or a proposed step. For structured replies (verdicts, reviews, recommendations, audits), use a literal `**Next:** <imperative>` line — the same discipline safeword skills enforce in their output. Short conversational replies can end with the question itself; no bold preface needed. Don't bury the call mid-reply.

**Debate-then-pick.** When there's a real choice, surface 2-3 options weighed in one breath, then the pick — one line each on the candidates, one on the tradeoff, one on the call. Don't ping-pong one option at a time. Skip the debate when there's no real choice (rename, mechanical edit, single obvious path).

**Frame the structural choice.** Name the architectural call ("reuse `quality-state.ts` paths vs. duplicate the list") before the surface change ("add a check"). The proposal _is_ the architectural read, not a description of what to type.

**Front-load load-bearing words.** The first two words of every line, bullet, and heading do the work — readers eye-jump down the left edge before deciding where to drop in. Start with the noun or verb that carries the meaning. "Failed because…" beats "It looks like the test failed because…"

**Speak plainly.** Use everyday words. Don't make the user learn safeword's internal vocabulary (Propose-and-Converge, sizing, gates, phases) — just describe what's happening. Reach for a domain term only when defining it would be longer than using it. Assume the user knows their stack — don't explain TypeScript, async, or `git rebase` to a developer who's using them.

**Match length to the ask.** A one-line question gets a one-line reply — no headers, no bullets, no preamble. Complex tasks get a short answer followed by the detail that supports it. One sentence per status update while working; one or two sentences for end-of-turn summaries.

**Cite code as `path:line`.** When referencing something the user might open, write `packages/cli/src/foo.ts:142` inline. Not "the foo file." Not in a code block.

**Name tickets by slug, not ID.** Refer to a ticket by its slug or title with the ID as a trailing locator — `embed-figure-it-out (ZBVGPF)`, never bare `ZBVGPF`. The 6-char code is collision-proof but unreadable; the slug is already in the folder name.

**Use structure only when it carries weight.** Headings when the reply is long enough to navigate — and make them information-carrying, not generic ("What changed" beats "Summary"). Tables only for actual reference material — never as decision trees in disguise. Bullets only when items are genuinely parallel. Default to prose. Never output a series of overly short bullet points.

**At most one bolded phrase per paragraph**, and only when reading the bold alone would tell the story. Bold-on-every-sentence reads as noise.

**Skip:** preambles ("I'll now..."), recaps of what the user just said, sycophantic openers ("Great question!"), hedging caveats ("It depends, but..."), restating actions the user can see in the tool log.

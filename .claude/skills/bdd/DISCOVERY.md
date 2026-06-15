# Intake: Understanding & Scope

**Entry:** Agent detects feature-level work OR resumes ticket at `intake` phase.

## Sub-phase gates

Intake advances through sub-phases (load personas/glossary → JTBD → AC → engineering scope). Each one ends with a **gate** — don't advance on your own momentum; present what you captured and get the user's signoff first. Three moves:

1. **Present** the captured artifact verbatim — the JTBD list, the AC list grouped by JTBD, or the Scope / Out of Scope / Done When block.
2. **Ask** the sub-phase's closing question (below).
3. **Wait** for confirmation. Any forward-moving reply advances — an explicit "looks good" / "proceed", or an amendment you fold in and re-present. A new concern loops back; you don't advance until it's resolved.

| Sub-phase           | Closing question                                                                                    |
| ------------------- | --------------------------------------------------------------------------------------------------- |
| Personas / glossary | _"`<file>` is empty — add entries now, or proceed without?"_ (only when missing/empty)              |
| Jobs To Be Done     | _"Do these jobs cover who this serves and why? Anything missing or mis-framed?"_                    |
| Acceptance Criteria | _"Does each job's criteria capture what 'done' means for the persona? Any to split, add, or drop?"_ |
| Engineering scope   | _"Here's the scope / out-of-scope / done-when — ready to proceed?"_                                 |

**On resume** (picked up mid-sub-phase across sessions): re-present the captured artifact for re-confirmation rather than assuming the prior signoff still stands — context may have shifted.

**Under YOLO mode** (G2E72G): gates auto-confirm and the auto-decision is recorded in the work log, so the audit trail shows what was waved through.

These gates are conversational discipline the agent runs — not a hook block. (Hook-enforced sub-phase tracking is future work, coordinated with phase-step-enforcement epic 172.)

## Load project personas

At intake start, read the configured personas file (`paths.personas`, default `<namespace-root>/personas.md`). This file is the project's source of truth for who features serve; later phases (JTBD authoring, AC validation, scenario numbering) reference its entries.

- **If the file is missing or empty** (no persona blocks parsed — the scaffolded template comment doesn't count) — surface a soft prompt:

  > _"`personas.md` is empty — want to add some now, or proceed without?"_

  The user can answer "proceed without" and intake continues; the prompt fires again later only if a turn tries to reference a persona that isn't in the file.

- **If a persona reference comes up during intake that isn't in the file** — flag it, don't invent. Ask whether it's a new persona to add, or a typo for an existing one. Use `validatePersonaReference` semantics (case-sensitive match; offer the suggestion when only casing differs).

Short codes auto-derive from names on the next `safeword check` (e.g., `Platform Operator` → `PO`). Codes can be overridden with explicit `## Name (CODE)` syntax. Never edit derived codes manually except via the override path — `safeword check` will rewrite them.

## Load project glossary

At intake start, read the configured glossary file (`paths.glossary`, default `<namespace-root>/glossary.md`). This file is the project's source of truth for domain vocabulary; using terms consistently across tickets keeps specs from drifting (does "session" mean the same thing in two scenarios, or two different things?).

- **If the file is missing or empty** (no term blocks parsed — the scaffolded template comment doesn't count) — surface a soft prompt:

  > _"`glossary.md` is empty — want to add some terms now, or proceed without?"_

  The user can answer "proceed without" and intake continues; the prompt fires again later only if a turn references a domain term that isn't in the file.

- **If a domain term comes up during intake that isn't in the glossary** — flag it, don't invent a definition. Ask whether it's a new term to define in the configured glossary file, or a synonym for an existing one. Use `validateGlossaryReference` semantics (exact name or alias match; offer the suggestion when only casing differs).

Project-wide terms live in the configured glossary file; vocabulary used in only one spec stays in that ticket. Never extract terms from prose automatically — humans curate the glossary.

## Author Jobs To Be Done

Before converging on scope, frame the product intent: what jobs does this feature do, and for whom? Write Jobs To Be Done into the ticket's `spec.md` under `## Jobs To Be Done`, one entry per job. JTBDs come first — they anchor the acceptance criteria and scope that follow.

Each JTBD is:

- A `### <slug>.<persona-code><n> — <title>` heading (e.g., `### oauth-flow.PO1 — rotate credentials without downtime`).
- A `**Persona:** <ref>` line naming **exactly one** persona from the configured personas file — one persona per JTBD. A job that serves two personas is two jobs.
- A `> When I …, I want …, so I can …` statement capturing the trigger, the desired action, and the outcome.

Resolve each persona reference against the loaded personas before writing it. A JTBD naming a persona absent from `personas.md` blocks the next phase — the intake-exit gate denies `test-definitions.md` until every JTBD resolves, or a `skip: <reason>` is recorded under `## Jobs To Be Done` for a deliberate omission.

**Pause and confirm** the JTBD set with the user before advancing to Understanding — this is the JTBD **Sub-phase gate** (see above). Converge on the jobs first, then build scope on top of them.

## Author Acceptance Criteria

Once the JTBDs are confirmed, decompose each into **Acceptance Criteria** — the rung between a job and its scenarios. An AC is a single capability or guarantee the persona gets; the define-behavior scenarios prove its specifics, and the ACs sum to JTBD fulfillment. Write them under their JTBD in `spec.md`:

- A `#### <jtbd-id>.AC<n> — <capability>` heading (e.g., `### oauth-flow.PO1` → `#### oauth-flow.PO1.AC1 — old key keeps working for a bounded grace window`).
- Each JTBD needs **≥1 AC**, or a `skip: <reason>` under it for a job with no user-observable capability to enumerate. The intake-exit gate enforces this (denies `test-definitions.md` until every JTBD has an AC or a skip).

**Coaching — keep ACs at the capability level, not implementation:**

- Descriptive guarantee, not a bare verb: "user can revoke a session and it stops working everywhere within seconds" ✓, not just "user can revoke a session."
- Capability, not mechanism: "`DELETE /sessions/<id>` returns 204" ✗ — that's a scenario's Then, not an AC.
- **Split-test heuristic:** could each clause of a bundled AC ship as its own complete deliverable with independent value? If yes → split into separate ACs. If the sub-operations only make sense together → keep as one.
- If an AC starts spawning more than ~10 scenarios in define-behavior, it's probably two ACs — split it.

**Pause and confirm** the AC list grouped by JTBD with the user before advancing — this is the AC **Sub-phase gate** (see above). Iterate until they sign off, then build engineering scope (Understanding) on top.

## Understanding (Propose-and-Converge)

Follow the understanding pattern from SAFEWORD.md — including contribution techniques. Converge until the user accepts a proposal with structured scope (Scope, Out of Scope, Done When) written to the ticket spec.

**Specificity self-test** — before proposing scope, verify you can answer all three:

- What behavior changes?
- What behavior stays the same?
- What is the observable done state?

If any answer is vague, you have open questions — surface them, and record each unresolved one in `spec.md`'s `## Open Questions` section (the equivalent of Example Mapping's red "question" cards) so it isn't lost across turns or sessions. Delete a question when it's answered, or mark it `defer: <reason>` for a deliberate punt.

**When the gap is user-only knowledge** (intent, priorities, constraints not derivable from code/docs) — call `/elicit` to extract it via microquestions before drafting scope.

**When the gap is the option space itself** (multiple plausible scopes, framings, or boundaries with no clear winner) — call `/figure-it-out` to weigh options against current docs and research before drafting scope.

**When the feature leans on a library or framework** — read the installed version's docs before proposing API shapes or done-when criteria. Scope baked on training memory of a different version is silently wrong. Check `package.json` / lockfile first, then the source wired up (Context7, official docs, README at the pinned ref).

**When the feature introduces architecture or a new pattern** — design the ideal first (`/figure-it-out`), _then_ survey the existing patterns in the area and reconcile: conform by default, deviate only with a named defect and an uplevel follow-up ticket. See `.safeword/guides/architecture-guide.md` → Survey & Reconcile.

## Worked example: intake end to end

One feature walked through all four artifacts and every sub-phase gate. Slug `oauth-flow`: let an operator rotate an API key without a coordinated flag day.

**1 · Personas — load and reference.** Intake reads the configured personas file and finds the persona this feature serves:

```markdown
## Platform Operator (PO)

**Role:** Owns the fleet's servers and their credentials.
```

The job below names `Platform Operator (PO)`; it resolves against the file, so intake continues. An unknown reference stops here — flag it, don't invent.

**2 · Jobs To Be Done — motivation first.** Capture who and why before anything else, in `spec.md`:

```markdown
### oauth-flow.PO1 — Rotate credentials without a flag day

**Persona:** Platform Operator (PO)

> When I rotate a server's API key, I want the previous key to keep
> working for a short grace period, so I can roll the change across my
> fleet without coordinated downtime.
```

**JTBD gate** → present the job, ask _"Do these jobs cover who this serves and why?"_, wait for signoff before decomposing.

**3 · Acceptance Criteria — capabilities under the job.** Each AC is one guarantee the operator can observe, not a mechanism:

```markdown
#### oauth-flow.PO1.AC1 — The previous key keeps authenticating for a bounded grace window

#### oauth-flow.PO1.AC2 — The operator can see which keys are currently live
```

**AC gate** → present the criteria grouped under their job, ask _"Does each job's criteria capture what 'done' means?"_, wait. (AC2 split out by the split-test — "see which keys are live" delivers value on its own.)

**4 · Engineering scope — what we touch, how we'll know.** Only now converge on the engineering contract, written to ticket frontmatter:

```yaml
scope:
  - dual-key validation with a configurable grace TTL
  - a `keys list` view showing each key as live / grace / expired
out_of_scope:
  - automatic rotation scheduling (rejected alternative)
  - per-key rate limits (rejected alternative)
done_when:
  - a request signed with the previous key succeeds within the TTL and fails after it
  - `keys list` reflects each key's current state
```

**Scope gate** → present Scope / Out of Scope / Done When, ask _"ready to proceed?"_, wait. Then advance to define-behavior.

**5 · Scenario lineage — the chain stays machine-checkable.** In define-behavior each scenario title carries the criterion it proves, so persona → JTBD → AC → scenario is traceable, not eyeballed:

```text
### Scenario: oauth-flow.PO1.AC1.previous_key_authenticates_within_grace_window
```

`safeword check` reads these titles and reports coverage gaps as advisories — an AC no scenario references (AC2, until you write one) is **uncovered**; a scenario naming a renumbered or missing AC is a **stale ref** or **orphan**. The full scheme lives in the bdd skill's SCENARIOS.md.

The arc end to end: a persona from `personas.md`, a job that names it, criteria under the job, an engineering contract on top, and scenarios that trace back to a criterion — each sub-phase closed by its gate.

## Intake Exit (REQUIRED)

Before proceeding to define-behavior:

0. **Specificity self-test passed** — you can concretely answer: what changes, what stays the same, observable done state
1. **Open Questions resolved** — `spec.md`'s `## Open Questions` is empty/answered, or each remaining line carries `defer: <reason>`. A long unresolved list means intake isn't done — keep converging.
2. **Verify ticket exists:** `<namespace-root>/tickets/{id}-{slug}/ticket.md`
3. **Verify frontmatter has:** `scope`, `out_of_scope`, `done_when` fields (non-empty)
4. **Update frontmatter:** `phase: define-behavior`
5. **Add work log entry:**

   ```
   - {timestamp} Complete: intake - Understanding converged, scope established
   ```

## Planning Note

Define-behavior scenarios draw from the self-test: behavior that changes seeds happy paths and error paths, observable done states seed acceptance criteria. Behavior that stays the same is protected by the existing test suite — it informs out-of-scope, not new scenarios. Add failure-mode scenarios from domain knowledge.

Technical breakdown — component identification and any design-doc/ADR triggers — belongs here in intake (you design the architecture in "Understanding" above). The per-scenario test-layer + build-order step now happens at the scenario-gate exit; the standalone `decomposition` phase is retired (see the ADR in `ARCHITECTURE.md`).

**Voice:** plainspoken and concise — write to be scanned.

---
name: figure-it-out
description: Explore and debate options with fresh documentation and research before committing. Use when facing a real decision with multiple plausible approaches — library/framework choice, architecture call, API or schema design, algorithm selection, or any communication / strategy call where being wrong has cost. Enumerates relevant research domains, looks up current docs and evidence-based methods, weighs options on correctness and elegance, resists bloat. Do NOT use for divergent ideation (brainstorm), extracting user intent (elicit), or reviewing already-written code (quality-review).
allowed-tools: '*'
---

# Figure It Out: Evidence-Backed Option Weighing

**Iron Law:** No recommendation without current evidence. Training data is stale; verify before staking a position.

## When to Use

A real decision with two or more plausible directions: library or framework choice, architecture, API or schema design, algorithm selection, communication strategy, policy call. User invokes `/figure-it-out`.

Skip for:

- Single obvious answer → just do it
- Need more options first → `brainstorm`
- Don't know what the user wants → `elicit`
- Reviewing existing code → `quality-review`

## Workflow

Copy this checklist and track progress:

```
- [ ] Phase 1: Frame the decision in one sentence
- [ ] Phase 2: Generate 2-3 concrete options
- [ ] Phase 3a: Enumerate relevant research domains (multiple)
- [ ] Phase 3b: Research each named domain
- [ ] Phase 4: Debate, steelman both sides, commit to one
```

### Phase 1: Frame

One sentence: what are we deciding, and what would make a choice wrong? If you can't write it, call `/elicit` — the option space is undefined.

### Phase 2: Generate options

Two or three, concrete enough to debate. For each: **what** (one sentence), **looks like** (sketch — code, config, or example), **smallest viable form**. Two strong options beat five hedged ones.

### Phase 3: Enumerate domains, then research

**3a — Name the domains.** Before searching, list every domain your decision touches. Multiple, not one. Write them down explicitly. A list with fewer than two or three entries means you haven't looked hard enough — decisions live at the intersection of multiple bodies of work.

Worked example — drafting a one-line block message for a CLI hook isn't just "writing copy." Domain list:

- Developer error-message UX research (Nielsen Norman, humanized-error patterns, name-the-gate-condition principle)
- Instructional design — state the rule, the violation, the next action
- High-frequency-interruption tone calibration (annoyance compounds across a session)
- Accessibility — screen readers, line length, no color-only signals
- Recovery ergonomics — can the user unblock themselves from this text alone?
- Observability — does the message give enough to file a useful bug or self-diagnose?

Each is a distinct body of work. Most agents pattern-match "it's just an error string" and skip all six.

**3b — Research each named domain.** For every one:

- **Library / API:** Context7 for live docs and version status
- **Established methods:** web search the domain name plus "research," "method," or "evidence-based" — surface named approaches you didn't know existed
- **Patterns and tradeoffs:** recent postmortems, benchmarks, contested debates
- **Boundary conditions:** what breaks under scale, load, failure, or adversarial input

**The trap.** _"This is just taste / style / vibes"_ is the warning sign, not the exit. Your training data taught you which domains feel aesthetic — those are usually the ones with the most established research you haven't met. Run 3a anyway.

**Only-valid skip.** The domain list comes up genuinely empty after honest enumeration: no humans affected, no measurable outcome, reversible in seconds. State the skip and why.

### Phase 4: Debate and commit

Argue both sides. Steelman the option you don't prefer **first**. For each, write:

- **Correct:** solves the actual problem, including edge cases?
- **Elegant:** readable, minimal, free of incidental complexity?
- **Cost:** lines, dependencies, abstractions, ongoing maintenance.

Then commit. Format:

> Recommend **X** because [single load-bearing reason]. Y was close on Z but loses on W. Cite: [doc or research link].
>
> **Next:** [concrete action to take now — install, write, edit, ask].

The `**Next:**` line is required. A recommendation without a next action is incomplete — name the file to edit, the command to run, or the question to ask. One line, imperative.

If two options tie on correctness and elegance, the smaller one wins.

**No hedging.** If you genuinely can't pick, you're missing one input — name it and ask one question. "Either could work" is not an answer.

**Voice:** plainspoken and concise — write to be scanned.

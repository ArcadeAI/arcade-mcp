---
name: elicit
description: "Extract tacit knowledge through non-obvious microquestions — things only the user knows that can't be found in code, docs, or research. Use when you're about to guess at intent, context, or constraints during SAFEWORD's understanding flow. Also use when user says 'ask me', 'what do you need to know', or when another skill (bdd, brainstorm, debug) needs user context before proceeding. Do NOT use for questions answerable by reading the codebase or searching the web."
allowed-tools: '*'
---

# Elicit: Tacit Knowledge Extraction

Draw out what the user knows and you can't research. Then check the latest evidence. Then explore options together.

**Iron Law:** NEVER ASK A QUESTION YOU COULD ANSWER YOURSELF. Read the code, search the docs, check git history first. Only ask what's left.

## When to Run

1. **Explicitly** — user invokes `/elicit`
2. **From other skills** — any skill can call "run /elicit" before a decision point (e.g. `bdd` before scenarios, `brainstorm` when narrowing, `debug` when symptoms are ambiguous)
3. **Proactively** — when you're about to make an assumption only the user can confirm

## Relationship to other skills

- **brainstorm** widens the option space (divergent). **elicit** narrows your uncertainty about user intent (convergent). Use brainstorm when you don't know the options; use elicit when you don't know the user's priorities among options.
- **SAFEWORD understanding flow** already does contribute-before-asking. `elicit` is the structured form for decision points where guessing would be costly.

## Phase 1: Microquestions

Ask one question at a time. Multiple choice (3-5 options). Force yourself to pre-think the option space so the user reacts rather than generates.

### What to ask about

- **Intent:** Why this way and not another? What was tried and rejected?
- **Constraints:** What's off-limits? What's coming soon that would change the answer?
- **Priorities:** When two good options conflict, which value wins?
- **Audience:** Who reads/uses this? What do they already know?
- **Omissions:** Is something missing because it's not ready, not wanted, or not thought of yet?

### Question format

Good:

> This could live in (a) the onboarding flow, (b) the decision-making page, or (c) as a standalone guide. Where would someone look for it?

Bad:

> Where do you think this should go?

The good version does the thinking. The bad version makes the user do it.

### How many

Keep asking until one of:

- Answers start repeating or converging
- You have enough to distinguish between options in Phase 3
- User says "enough" or "go"

Typical: 3-7 questions. Fewer for small scope, more for ambiguous scope.

## Phase 2: Research

After elicitation, check the latest evidence on the decision at hand. Web-search for:

- Meta-analyses or systematic reviews
- Replicated findings with effect sizes
- How leading organizations handle this
- Boundary conditions and known limitations

**Skip** if the task is purely operational (no empirical claims involved).
**Defer** if the calling skill has its own research phase — don't duplicate work.

## Phase 3: Options

Present 2-3 options. Each option:

- **What:** the approach, concretely
- **Why it's good:** what it gets right
- **What it costs:** complexity, length, tradeoff
- **Evidence:** what supports it (from Phase 2, if applicable)

For small scope (patch/task): just do it — skip the proposal, apply the best option directly.
For larger scope (feature/policy): present options, let the user pick.

## From Other Skills

When called from another skill, the elicitation results feed directly into the calling skill's next phase. No separate artifact — the conversation is the artifact.

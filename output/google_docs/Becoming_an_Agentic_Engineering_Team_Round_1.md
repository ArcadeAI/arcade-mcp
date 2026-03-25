---
title: "Becoming an Agentic Engineering Team (Round 1)"
id: 1BG6-99Naj4_uadjA5ZAvjeW4XDegEYXyJzkzCr7jTiM
modified_at: 2026-03-16T23:39:48.087Z
public_url: https://docs.google.com/document/d/1BG6-99Naj4_uadjA5ZAvjeW4XDegEYXyJzkzCr7jTiM/edit?usp=drivesdk
---

# Tab 1

<!-- Tab ID: t.0 -->

# Becoming an Agentic Engineering Team (round 1)
Strategy is where we are going; tactics is how we get there.

## Strategy

We want to
- Build impactful features faster
- Delegate more engineering work to AI agents to allow the humans to spend more time in the high-impact areas
- Trust that AI-written code is of high quality
- Enable folks outside of the Engineering team to use agents to help build the product

We do _not_ want to
- Create a gigantic backlog of code we don't have time to review
- Introduce bugs and unexpected behaviors that impact our maintenance operations or our customer experience

Our **north star** for becoming an agentic engineering team** **is:

_Most code changes can be performed, reviewed, and merged by coding agents without human review. Developers plan projects and orchestrate agents to achieve product goals._

This is a big goal, and it will not happen overnight!

Round 1 is focused on the necessary preconditions to make it measurable and operational across the monorepo.

Success for round 1 is defined as: 

_10__% of the monorepo (by LOC) is eligible for AI edit + review + merge, without human review._


## Tactics
### Foundation: Shared tooling
We adopted Claude Code as our foundational tool chain. ✅
This gives us a "base" tooling layer for everything we build going forward.
### New concept: Add AI to CODEOWNERS
To start measuring how much of our codebase can be autonomously (without humans) **edited, reviewed, and merged** by coding agents, we will add a bot designation to CODEOWNERS. In other words, AI can be assigned files, directories, or glob patterns just like a human team.

This lets us define in a simple and transparent way which parts of the monorepo can be built autonomously. For example:
- Some areas are safe for autonomous edits and AI-only review
- Some areas always require human review because they are high risk, externally visible, or safety-critical

This declarative approach gives us a shared place for deciding where autonomy is allowed, where it is not yet allowed, and creates a **forcing function** around what needs to improve in order to move code from one category to another.

#### What has to improve for the boundary to expand
If we want more of the monorepo to become eligible for autonomous edit and review, we need to improve the conditions that make autonomy safe.

That includes:
- Clearer engineering guidance and documented patterns
- Stronger behavioral and end-to-end testing
- Robust AI-assisted code review (ideally with multiple models)
- Extract tacit knowledge currently in IC's minds and express them in a literal, unambiguous way for LLMs to understand
- Express “anti-behaviors” or “anti-intents” for each area of the codebase we want to unlock autonomy: “anti-intent” is a path that would lead to the intended behavior, but in a way that makes it undesirable.

These are not separate goals. They are the enabling conditions that let us safely expand the review policy.
### New concept: Behavioral testing
Goal: an end-to-end or "black box" testing suite that gives us confidence in shipping any change, whether AI or human-written.

The scope of this is ultimately quite broad, including dealing with external dependencies (Stripe, Orb); performance and load testing; unhappy/adversarial paths; visual regression testing

There are many open questions here that we will figure out together!
- Do we need to move intent outside of the monorepo to keep it from being changed by agents? Tests too? Or can we cordon off a `behaviors/` directory in the monorepo?
- There is an analogy here to holdout datasets in ML

Behavioral testing is the mechanism by which coding agents will prove their solutions work. It will become the most important asset we have.

In the limit, our test suite "all up" **must** be robust enough such that our entire product could be rewritten from scratch using only the behavioral tests as a guide.

Important implication: Having a robust behavioral testing suite means that our **development process will change significantly.** Instead of writing code first, and then tests, we will most often write behavioral tests first, then code.

### To be determined
There are lots of open questions for us to figure out!
#### Engineering guidance and patterns
- Define a list of documentation that is missing and a plan to backfill it
- Guidelines per language
- Global Architecture (w/ intent)
- Per-service Architecture (w/ intent)
- Minimum requirements for merge (e.g. prod readiness checklist)
- Local runnable checks (formatting, linting, static checks - run before push)

#### PR review process
- The review process happens in two phases:
  - Pre-push (local): Deterministic checks run before a PR is created (formatting, linting, type checks, and static analysis). These are fast, have no opinions, and give the agent (or developer) immediate feedback before any CI resources are consumed.
  - Post-PR creation (CI): Behavioral tests and the AI review loop run after a PR is opened. This is where the full test suite, multi-model review, and any integration checks happen. Behavioral tests should also be runnable locally so that agents can iterate against them before pushing, but running on PR is the hard requirement.
- ⏳ Preview deploys easily available for any branch
- Research Github Agentic Workflows: https://github.github.com/gh-aw/ More docs: https://github.github.com/gh-aw/blog/2026-01-12-welcome-to-pelis-agent-factory/
- Can we utilize multiple models to review code from different perspectives?
- How do we learn from each review (whether good/smooth or bad/frustrating)?
  - Storing agent session recordings, commit history, review history…
  - Ask the team (light check-in every couple weeks)

#### Initial target areas for full automation
- Monitoring and Dashboards
- CVE fixes (pyproject, go.mod, Docker/apt, package.json…)
- Updating shared libs (these should have well-isolated unit-testable interfaces)
- New toolkits

#### Question: What else is missing?

## An Agentic Engineering Team in a Flowchart
Source: https://whimsical.com/arcade719/ai-reviews-WRFcbpHmJEKNuC8t1va4Rg 


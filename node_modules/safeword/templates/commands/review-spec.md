---
description: Adversarial review of a ticket's scenarios — vacuous-pass, AODI, determinism, negative-case, cross-cutting (project)
---

# Review Spec

Adversarially review the active ticket's `test-definitions.md` scenarios — "what breaks that these don't catch?". Apply the full Scenario Quality Gate: vacuous-pass, AODI, determinism risks, adversarial pass + negative-case, and cross-cutting checks; report findings in the structured findings format (lead with a tally → three severity tiers → one `####` per finding, Current → Proposed → **Next:**).

The full procedure lives in the `review-spec` skill (`.claude/skills/review-spec/SKILL.md`). Auto-fired by the bdd scenario-gate; re-invokable after scenario edits. Not a `spec.md` framing review — that is self-review.

---
description: Self-review the spec inline and earn its Tier 1 review stamp (project)
---

# Self-Review

Review the artifact you just authored, then earn its review stamp so the next
step is unblocked. Tier 1 — your own inline pass, no sub-agent. The independent
check is Tier 2 (the phase-exit review), not this.

## Earn the stamp

The line below binds a `review:<scope>` stamp to the active ticket's `spec.md`
at its **current content** and appends it to the skill-invocation-log, where the
per-asset gate reads it back.

!`PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}" && CLAUDE_PROJECT_DIR="$PROJECT_DIR" bun "$PROJECT_DIR/.safeword/hooks/write-review-stamp.ts" spec`

If you see `[skill-invocation-log] FAILED` or no `✓` line, the stamp was not
written and the gate will keep blocking — resolve before retrying.

## Review the spec

Read the active ticket's `spec.md` and check, against `personas.md` and the
ticket's `scope` / `out_of_scope`: every JTBD resolves to a real persona and
reads as a genuine job; each JTBD has ≥1 observable, product-level Acceptance
Criterion; the ACs cover scope and stop at `out_of_scope`; no implementation
detail leaks into spec prose. If the review surfaces a fix, edit `spec.md` and
re-run — the content-bound stamp goes stale on any edit, so the gate correctly
re-blocks until the corrected spec is re-reviewed.

## Skip valve

Trivial or docs-only? Log a skip with a reason instead — it clears the same gate
and records why (an empty reason does not clear it):

```bash
bun .safeword/hooks/write-review-stamp.ts spec "<why this spec needs no review>"
```

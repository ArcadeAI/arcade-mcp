# Work Log: {Title}

**Anchored to:** {path to ticket, spec, or design doc}

---

## Session: YYYY-MM-DD

{Log entries use agent discretion. Capture what helps you stay on track:
findings, decisions, blockers, hypotheses, scratch notes.}

**Format:** `- [HH:MM] {entry}`

**Examples:**

```text
- [14:30] Started investigating auth timeout issue
- [14:45] Found: Token refresh happening on every request (refs: src/auth.ts:42)
- [15:00] Hypothesis: Race condition between refresh and API call
- [15:20] Confirmed: Adding mutex fixed the issue
- [15:30] Tests passing, ready for review
```

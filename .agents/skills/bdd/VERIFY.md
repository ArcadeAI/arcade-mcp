# Verify: Evidence Gate

**Entry:** All scenarios marked `[x]` in test-definitions.md.

## Steps

1. **Cross-scenario refactor** if clear wins exist (shared fixtures, duplicate logic). Run full test suite after. Only refactor if clear wins exist — don't gold-plate. Mark the feature-level `- [ ] cross-scenario` row at the bottom of `test-definitions.md` with either `<sha>` (the refactor commit) or `skip: <reason>` (none warranted). The done-gate hard-blocks if this row is missing or has an empty `skip:` reason on tickets using the annotated checkbox format.
2. **Run /verify** — tests, build, lint, scenario validation, doc references, dependency drift. /verify writes `verify.md` to the ticket folder on success.
3. **Run /audit** — architecture, dead code, duplication, outdated deps.

If tests are flaky, investigate before proceeding.

## Verify Exit (REQUIRED)

Before proceeding to done:

1. **verify.md exists** in the ticket folder (written by /verify on success)
2. **Update frontmatter:** `phase: done`
3. **Add work log entry:**

   ```
   - {timestamp} Complete: verify - /verify + /audit passed, verify.md written
   ```

The stop hook hard-blocks `phase: done` if verify.md is missing or empty.

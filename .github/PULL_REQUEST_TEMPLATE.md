<!--
PR title: conventional commits with optional scope, e.g.
  feat(arcade-core): add support for X
  fix(arcade-mcp-server): handle stdio EOF
  chore(arcade-tdk): bump dep

Keep the title short and scannable. The description does the explaining.
-->

## Summary

<!-- One short paragraph in plain English: what does this change do, and why? -->

Resolves: <!-- Linear ticket link OR GitHub issue # (e.g. #123, or https://linear.app/...) -->

## Design decisions

<!--
Delete this section if the change is mechanical.

Call out non-obvious choices: why this approach, what alternatives you considered,
what's intentionally NOT done. This is the part hardest to reconstruct from the
diff and easiest to skip — write it anyway.
-->

## Scope

<!--
Delete this section if scope is obvious from the summary.

In scope:
-

Not in scope (handled separately / out of band):
-
-->

## Test plan

<!--
Concrete, verifiable steps — not "tests pass." Describe what you actually exercised.
Example shape:

- [ ] `make check` (ruff + mypy) clean
- [ ] `make test` passes
- [ ] Ran `arcade mcp stdio` against the example server and confirmed tools/list returns the expected entries
- [ ] Exercised the end-user path: `arcade login` → tool call → confirmed auth token reached the tool
- [ ] Verified the MCP stdio channel stayed clean (no stray stdout/stderr) per CLAUDE.md
- [ ] Bumped the affected library version(s) in `libs/arcade-*/pyproject.toml` if the change is breaking
-->

- [ ]
- [ ]

## Risk note

<!--
Delete this section unless the PR touches a sensitive area.

Sensitive paths in this repo include:
- `libs/arcade-serve/` — worker JWT auth and `/worker/*` endpoints
- `libs/arcade-mcp-server/arcade_mcp_server/resource_server.py` — OAuth 2.1 token validation
- MCP stdio transport — any new stdout/stderr writes can corrupt the JSON-RPC channel
- `pyproject.toml` files — version bumps, dependency changes, breaking-change semver
- Tool secrets / env-var flow — anything reachable from `context.get_secret()`

Describe the blast radius (who/what breaks if this is wrong) and your mitigations.
-->

## Coverage note

<!--
Delete this section unless patch coverage is in the yellow zone (70–85%).
Aim for green (85%+); meaningful coverage matters more than artificial numbers.
Why coverage is below green:
-->

## Author checklist

Before moving this PR from Draft to Ready for Review:

- [ ] Linked to a Linear ticket or GitHub issue (above)
- [ ] I understand every change in the diff — not "an agent wrote it, I'm not sure why"
- [ ] Runs locally, exercised through the end-user path (not just unit tests)
- [ ] `make check` and `make test` are green locally; CI is expected to pass
- [ ] I've pulled the branch fresh and reviewed my own diff top-to-bottom
- [ ] I'd merge it myself if a teammate said LGTM right now

<!--
If this PR was authored with significant AI assistance, leave the line below.
Otherwise delete it. You — the author on the PR — own everything above this line.
-->

🤖 Generated with [Claude Code](https://claude.com/claude-code)

## Summary
- Toolkit compatibility checks failed for [arcade-mcp PR #{{ARCADE_PR_NUMBER}}]({{ARCADE_PR_URL}}).
- This draft PR was generated automatically to host compatibility fixes in `apps/worker/toolkits`.
- Compatibility CI in `arcade-mcp` will switch from monorepo `main` to this PR branch once linked.

## Failing toolkit matrix summary
{{FAILURE_SUMMARY}}

## Context
- Arcade MCP head SHA: `{{ARCADE_HEAD_SHA}}`
- Branch: `{{BRANCH_NAME}}`

## What to do next
1. Add toolkit fixes on this branch.
2. Keep this PR open while the upstream `arcade-mcp` PR is in review.
3. Confirm the upstream `arcade-mcp` PR has `toolkits-fix-pr: <this PR URL>` in its body.

## Test plan
- [ ] Toolkit unit tests pass in this branch with the current `arcade-mcp` implementation.
- [ ] Any required follow-up changes are documented.

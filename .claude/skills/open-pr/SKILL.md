---
name: open-pr
description: Prepare arcade-mcp changes for review by verifying intended behavior, filling the repository PR template, and creating or updating the PR. Use for "open a PR", "get this reviewed", or "make this PR ready". Resume existing work. PR preparation is separate from releasing; use a code-review skill for review-only requests.
---

# Open a PR

Deliver a focused PR with an accurate description and evidence supporting its intended behavior. The author owns the job, behavior, approach decisions, and outcome, and stays responsible for AI-assisted work; line-by-line recall is not a prerequisite.

Follow `CLAUDE.md` and `.github/PULL_REQUEST_TEMPLATE.md`. Link issues and design discussions rather than reconstructing them in the PR.

Use the GitHub and issue-tracker tools the user chose. Discover available operations before assuming a CLI, connector, or credentials exist. Keep local git operations local. If a needed remote operation is unavailable, finish local preparation and report the exact missing capability; do not silently switch tools or claim the operation succeeded.

## 1. Establish the actual state

- Read `CLAUDE.md` and the PR template. Inspect the working tree, staged changes, branch, upstream, remotes, and any existing PR. Confirm the destination repository and base; use the existing PR's base or `main` unless the task specifies otherwise. Fetch the base before assessing the diff.
- Review both the committed diff against the merge base and pending changes. Identify the intended scope, related issue, and consequential choices. Preserve unrelated work; stage explicit files or hunks. Do not reset, squash, rebase, or force-push someone else's work to tidy the PR.
- Apply [PR scope discipline](../../rules/pr-scope.md). Resolve an actual scope problem rather than expanding the description to explain unrelated work.
- Reuse a matching open PR. A closed or merged PR is not an update target. If the branch is detached or is the base branch, create a task branch. Resolve ambiguity that could send work to the wrong repository, base, or PR before publishing.
- Find the tracking issue (GitHub issue or Linear) in task context, branch, commits, or existing PR and verify it describes this work. If none exists, file one first (or stop and ask your human to if you cannot). Do not borrow an unrelated or closed issue.

A request to open a PR authorizes routine commits, pushing the task branch, and creating a Draft. A request to get work reviewed also authorizes marking it ready once vetted; preserve an existing Ready state. Honor text-only requests. Merging, reviewer assignment, and releasing require the corresponding user request; do not expand "open a PR" into those actions.

## 2. Establish confidence in the behavior

Use the issue and linked discussion as the expected behavior. The implementation and tests are evidence to examine, not the source of truth for what should happen. If those sources conflict, identify the concrete decision needed rather than silently rewriting the contract to fit the code.

Load only the relevant entry points:

- **Behavior:** the issue, `CLAUDE.md`'s architecture notes for the touched area, and docs the change affects. Note whether the change touches the MCP side (`MCPServer`, transports), the Arcade Worker side (`libs/arcade-serve/`), or both through the shared `ToolCatalog` / `create_arcade_mcp()`.
- **Checks:** `make check` (pre-commit + mypy per lib) and `make test`, or targeted `uv run pytest libs/tests/<area>/...` while iterating; CI runs `.github/workflows/main.yml` on Python 3.10–3.14 across Linux, macOS, and Windows. Changes to `arcade-core` or `arcade-tdk` need checks for the libs that depend on them. Always use `uv run`, never bare `python` or `pip`.
- **Versioning:** bump the touched library's version in its `pyproject.toml` once per branch (check `git diff main` first), and raise the dependency floor in dependent libs for breaking cross-library changes. `release-on-version-change.yml` publishes on version changes, so a bump is a release decision; call it out.

Choose verification proportional to the change:

- Exercise the affected workflow for real. For server or tool changes, run a server from `examples/mcp_servers/` with `arcade mcp stdio` or `arcade mcp http` (or MCP Inspector) and drive the changed path; for worker changes, call the `/worker/*` endpoints with `ARCADE_WORKER_SECRET` set; for CLI changes, run the command. Check the normal path and plausible boundary, failure, or regression paths. Anything reachable from the stdio transport must leave stdout/stderr clean. Documentation changes need rendering/link checks, not unrelated suites.
- Inspect whether tests would catch the claimed failure or a wrong implementation. For a bug fix, demonstrate the regression fails before and passes after when feasible. Watch for weakened assertions, excessive mocks, or tests that repeat the implementation. Every behavioral change needs a test in `libs/tests/`; do not invent additional tests for trivial, reversible changes.
- Run required checks and affected suites. Confirm the intended tests actually ran: zero collected tests, a deselecting `-k`, or skipped tests (evals tests skip without `anthropic`/`openai` installed) prove nothing. Record revision, command, observed result, and limits in working notes; put only the useful summary in the PR. Reuse applicable evidence; rerun checks affected by edits, including formatter changes before committing.
- Review the final diff for unintended changes, unsafe boundaries, and reuse of established patterns. For substantive changes, use a code-review skill or a fresh reviewer context with the intended behaviors, relevant constraints, and raw diff. Do not feed it an assurance that the change is correct. Reuse an applicable independent review already completed; add another only for an unresolved risk.
- Verify findings against code or a reproduction before fixing them. Reject false positives with evidence. If a finding changes scope or the intended behavior, surface that decision instead of quietly expanding the task.

Do the checks available to you. Ask the engineer only for missing access, a behavior decision, or experience/judgment you cannot supply. Reuse their earlier vetting when it still covers the outcome; do not add a ritual sign-off question. Never claim the engineer personally used or approved something because an agent did it. Surface material gaps with what remains to be checked and why.

## 3. Write the description

Use the actual template:

- **Issue link:** the first line of the body, the bare verified issue reference right after the keyword, without brackets or placeholder text: `Closes #123` for a GitHub issue or `Closes ABC-123` for Linear. Use `Closes` when merging this PR completes the issue, and `Part of` when it is only one piece of it.
- **What/why:** the problem and observable before/after, understandable without opening the issue. For changes with no user-facing effect, describe the effect on contributors or maintainers.
- **Codebase changes:** the approach, non-obvious consequential decisions, which protocol side is affected, and any version bumps.
- **Proof:** concise actual verification results, following the template's instructions. Fill the verification table with how each promised behavior was proven (real, mocked, unit, or judged), and the Before/After table with output excerpts for user-visible changes; drop a table that does not apply. Prefer "tools/call on the expired token returned TOOL_RUNTIME_RETRY" to "Tested thoroughly."
- **Additional notes:** material risks (especially the sensitive paths the template lists), verification gaps, or a specific decision needing attention. Omit when empty.

Three to five sentences per section is a ceiling, not a quota. One sentence may be enough. Use bullets if clearer; keep detail required to assess a consequential risk. Remove template instructions, empty optional sections, file inventories, coding diaries, and unsupported adjectives. Preserve automation-managed blocks and relevant collaborator edits when updating an existing body.

Write the title in [Conventional Commits](https://www.conventionalcommits.org) format, `type(scope): summary`, where type is `feat`, `fix`, or `chore` and scope is the lib or area (`fix(arcade-mcp-server):`, `feat(arcade-cli):`, `chore(ci):`). Keep issue IDs out of the title; they go on the `Closes` / `Part of` line. Check that the description explains why it matters, what changes, the important choice, and the evidence, without making the reader reconstruct these from the diff. Update it to match the final implementation after revisions.

## 4. Publish or update the Draft

- Check the final staged diff and commit only the intended changes. Push the task branch without rewriting published history. If uncommitted changes were excluded, say so in the handoff.
- Create with explicit base, head, and Draft state, or update the existing PR without silently changing its review state. Re-read the body before editing to preserve intervening changes. Pass the body as a structured argument or file to preserve Markdown and avoid shell interpolation. Recheck for an existing PR before retrying an uncertain creation result.
- Read back the title, description, Draft state, base, and head. Confirm the issue shows the linked PR; an issue reference in prose alone does not prove the link.
- A Draft may be opened before CI finishes. Inspect checks and review findings for the current head. Pending, skipped, and failed are distinct outcomes; a missing check is not a pass. Use bounded waits, report unfinished checks, and avoid polling indefinitely. Do not bypass gates or treat a green run as merge authorization.

## 5. Ready means vetted

Before a requested promotion to Ready:

- The engineer has vetted the outcome and has no undisclosed blocker to shipping. Relevant workflow evidence is available; human-only experience or judgment has been supplied where needed.
- CI on the current PR head is green (including GitHub's merge commit when that is what CI tests), and verification and independent review still cover the changed behavior.
- Review summaries, inline threads, and PR comments are read in full. Findings are addressed or explicitly discussed; unresolved blockers prevent promotion. Do not resolve disagreements just to clear a count. A review of an older revision needs an assessment of the intervening diff, not automatic credit or an automatic rerun.
- The description reflects the final scope, evidence, and remaining limitations.

If these are not met, continue preparation or leave the PR Draft with the specific gap. If an existing Ready PR gains a material blocker, flag it rather than silently treating it as ready.

If a check or review starts only after Ready, do not wait for it on a Draft. Once the pre-Ready conditions are met, perform the authorized promotion, then inspect those results. Pending review or required approval still blocks merging; report it explicitly. Never report code as released because a PR was opened, approved, or merged; a release happens only when `release-on-version-change.yml` publishes it.

End with the PR link, a short account of the change and validation, and any remaining blocker or decision. Do not paste the full description into the handoff.

## Maintaining this skill

When changing this workflow, replay the offline scenarios in [evals/cases.json](evals/cases.json) in fresh contexts, withholding expectations from the executing agent. Grade its actions and evidence claims; formatting checks alone cannot validate readiness decisions.

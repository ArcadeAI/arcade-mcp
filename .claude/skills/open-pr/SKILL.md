---
name: open-pr
description: Prepare arcade-mcp changes for review by verifying intended behavior, filling the repository PR template, and creating or updating the PR. Use for "open a PR", "get this reviewed", or "make this PR ready". Resume existing work. PR preparation is separate from releasing; use code-review for review-only requests.
---

# Open a PR

Deliver a focused PR with an accurate description and evidence supporting its intended behavior. The author owns the job, behavior, approach decisions, and outcome; line-by-line recall is not a prerequisite.

Follow the repository template, `CLAUDE.md`, and, for Arcade engineers, the relevant company guidance, reusing policy context already read in this task:

- [What a Good Pull Request Looks Like](https://company.arcade.dev/engineering/process/what-a-good-pr-looks-like): PR quality, concise descriptions, and author readiness.
- [Working with AI](https://company.arcade.dev/everyone/handbook#working-with-ai): the engineer remains responsible for the correctness, content, and maintenance of AI-assisted work. Read this section rather than the entire handbook.
- [Approved Models, Harnesses, and Pricing](https://company.arcade.dev/engineering/tooling/approved-models-and-pricing): consult the living list when selecting or adding an agent/model, including for independent review. Follow its company-account and data-handling requirements; do not infer approval merely because a tool is available.

Keep policy details, model lists, and spend limits in those source pages. Link planning and design artifacts rather than reconstructing them here.

Use the user's chosen GitHub/Linear tools. Discover available operations before assuming a CLI, connector, or credentials exist. Keep local git operations local. If a needed remote operation is unavailable, finish local preparation and report the exact missing capability; do not silently switch tools or claim the operation succeeded.

## 1. Establish the actual state

- Read `CLAUDE.md` and `.github/PULL_REQUEST_TEMPLATE.md`. Inspect the working tree, staged changes, branch, upstream, remotes, and any existing PR. Confirm the destination repository and base; use the existing PR's base or `main` unless the task specifies otherwise. Refresh the relevant remote refs before assessing the diff.
- Review both the committed diff against the merge base and pending changes. Identify the intended scope, related issue, and consequential choices. Preserve unrelated work; stage explicit files or hunks. Do not reset, squash, rebase, or force-push someone else's work to tidy the PR.
- Apply [PR scope discipline](../../rules/pr-scope.md). Resolve an actual scope problem rather than expanding the description to explain unrelated work.
- Reuse a matching open PR. A closed or merged PR is not an update target. If the branch is detached or is the base branch, create a task branch. Resolve ambiguity that could send work to the wrong repository, base, or PR before publishing.
- Find the Linear issue or GitHub issue in task context, branch, commits, or existing PR and verify it describes this work. If none exists, file one first (or stop and ask your human to if you cannot) and verify it describes this work.

A request to open a PR authorizes routine commits, pushing the task branch, and creating a Draft. A request to get work reviewed also authorizes marking it ready once vetted; preserve an existing Ready state. Honor text-only requests. Merging, reviewer assignment, and releasing require the corresponding user request and applicable policy; do not expand "open a PR" into those actions.

## 2. Establish confidence in the behavior

Use the issue, linked docs, and relevant decisions as the expected behavior. The implementation and tests are evidence to examine, not the source of truth for what should happen. If those sources conflict, identify the concrete decision needed rather than silently rewriting the contract to fit the code.

Load only the relevant entry points:

- **Behavior and decisions:** the issue, `CLAUDE.md`'s architecture notes for the touched area, and public docs the change affects. Note whether the change touches the MCP side, the Arcade Worker side (`libs/arcade-serve/`), or both via the shared `ToolCatalog` / `create_arcade_mcp()`.
- **Checks:** `make check` (pre-commit + mypy) and `make test`, or targeted `uv run pytest libs/tests/<area>/...` while iterating, plus the CI workflows in `.github/workflows/`. Changes to `arcade-core` or `arcade-tdk` need checks for downstream libs. Always use `uv run`, never bare `python`/`pip`.
- **Versioning:** per `CLAUDE.md`, bump the touched library's version in its `pyproject.toml` once per branch (check `git diff main` first) and raise dependency floors for breaking cross-library changes. `release-on-version-change.yml` publishes on version changes, so a bump is a release decision; call it out.

Choose verification proportional to the change:

- Exercise the affected workflow for real. For server or tool changes, run an example from `examples/mcp_servers/` via `arcade mcp stdio` / `arcade mcp http` (or MCP Inspector) and drive the changed path; for worker changes, call the `/worker/*` endpoint; for CLI changes, run the command. Check the normal path and plausible boundary, failure, or regression paths. Anything reachable from stdio must leave stdout/stderr clean. Documentation changes need rendering/link checks, not unrelated suites.
- Inspect whether tests would catch the claimed failure or a wrong implementation. For a bug fix, demonstrate the regression fails before and passes after when feasible. Watch for weakened assertions, excessive mocks, or tests that repeat the implementation. Every behavioral change needs a test in `libs/tests/`; do not invent additional tests for trivial, reversible changes.
- Run required checks and affected suites. Confirm the intended tests actually executed: zero collected tests, a dry run, or skipped tests (e.g. evals tests auto-skipped without `anthropic`/`openai`) cannot prove behavior. Record revision, environment, command, observed result, and limits in working notes; expose only the useful summary in the PR. Reuse applicable evidence; rerun checks affected by edits, including formatter/hook changes before committing.
- Review the final diff for unintended changes, unsafe boundaries, and reuse of established patterns. For substantive changes, use the `code-review` skill or a fresh reviewer context with the intended behaviors, relevant constraints, and raw diff. Do not feed it an assurance that the change is correct. Reuse an applicable independent review already completed; add another only for an unresolved risk or a repository requirement.
- Verify findings against code or a reproduction before fixing them. Reject false positives with evidence. If a finding changes scope or the intended behavior, surface that decision instead of quietly expanding the task.

Do the checks available to you. Ask the engineer only for missing access, a behavior decision, or experience/judgment you cannot supply. Reuse their earlier vetting when it still covers the outcome; do not add a ritual sign-off question. Never claim the engineer personally used or approved something because an agent did it. Surface material gaps with what remains to be checked and why.

## 3. Write the description

Use the actual template. In this repository:

- **Issue link:** the first line of the body, the bare verified issue reference right after the magic word, without brackets or placeholder text: a Linear ID (`Closes PLT-123`) or a GitHub issue (`Closes #123`). Use `Closes` when merging this PR completes the issue, and `Part of` when it is only one piece of it. Never write "Linear issue:" (a closing phrase) or "Linear ticket:" (not recognized, so it links nothing).
- **What/why:** the problem and observable before/after, understandable without opening the issue. For non-user-facing changes, describe the effect on the contributor or operator.
- **Codebase changes:** the approach, non-obvious consequential decisions, which protocol side is affected, and any version bumps.
- **Proof:** concise actual verification results, following the template's instructions. Fill the verification table with how each promised behavior was proven (real, mocked, unit, or judged), and the Before/After table with output excerpts for user-visible changes; drop a table that does not apply. Prefer "tools/call on the expired token returned TOOL_RUNTIME_RETRY" to "Tested thoroughly." Keep exact commands or longer evidence behind a link when helpful.
- **Additional notes:** material risks (especially the sensitive paths the template lists), verification gaps, rollout constraints, or a specific decision needing attention. Omit when empty.

Three to five sentences per section is a ceiling, not a quota. One sentence may be enough. Use bullets if clearer; retain detail required to assess a consequential risk. Remove template instructions, empty optional sections, file inventories, coding diaries, and unsupported adjectives from the authored text. Preserve automation-managed blocks and relevant collaborator edits when updating an existing body; do not duplicate them in your summary. Follow applicable authorship/signature instructions without adding redundant generated-by text.

Write a title in [Conventional Commits](https://www.conventionalcommits.org) format, `type(scope): summary`, where type is `feat`, `fix`, or `chore` and scope is the lib or area (`fix(arcade-mcp-server):`, `feat(arcade-cli):`, `chore(ci):`). Never put the issue ID in the title; it goes on the template's `Closes` / `Part of` line in the description. Check that the description explains why it matters, what changes, the important choice, and the evidence, without making the reader reconstruct these from the diff. Update it to match the final implementation after revisions.

## 4. Publish or update the Draft

- Check the final staged diff and commit only the intended changes. Push the task branch to the verified remote without rewriting published history. If uncommitted changes were excluded, make that clear in the handoff.
- Create with explicit base, head, and Draft state, or update the existing PR without silently changing its review state. Re-read the body before editing to preserve intervening changes. Use a structured API argument or body file to preserve Markdown and avoid shell interpolation. Recheck for an existing PR before retrying an uncertain creation result.
- Read back the title, description, Draft state, base, and head. Verify the issue linkage actually registered (the issue shows the PR); an issue ID in prose alone does not prove it.
- A Draft may be opened before CI or automated review finishes. Inspect applicable checks and findings for the current head. Pending, unavailable, skipped, and failed are distinct outcomes; a missing check is not a pass. Use bounded waits, report unfinished checks, and avoid polling indefinitely. Do not bypass gates or assume a green run authorizes a merge.

## 5. Ready means vetted

Before a requested promotion to Ready:

- The engineer has vetted the outcome and has no undisclosed blocker to shipping. Relevant workflow evidence is available; human-only experience or judgment has been supplied where needed.
- Checks and automated reviews that run on Draft have completed as required by repository policy. Evaluate CI associated with the current PR head, including GitHub's generated merge commit when that is what CI tests. Verification and independent review still cover the changed behavior.
- Inspect review summaries, inline threads, and PR comments with pagination where needed. Findings are addressed or explicitly discussed; unresolved blockers prevent promotion. Do not resolve disagreements just to clear a count. A review from an older revision needs an assessment of the intervening diff, not automatic credit or an automatic rerun.
- The description reflects the final scope, evidence, and remaining limitations. Follow the repository's approval and release policies.

If these are not met, continue preparation or leave the PR Draft with the specific gap. If an existing Ready PR gains a material blocker, flag it and follow the repository's process rather than silently treating it as ready.

If a check or hosted review starts only after Ready, do not wait for it on a Draft. Once author preparation and the repository's pre-Ready gates are satisfied, perform the authorized promotion, then inspect those results. Pending review or required approval still blocks merging; report it explicitly. Never report code as released because a PR was opened, approved, or merged; a release happens only when the version-change workflow publishes it.

End with the PR link, a short account of the change and validation, and any remaining blocker or decision. Do not paste the full description into the handoff.

## Maintaining this skill

This skill is adapted from the `open-pr` skill in ArcadeAI/monorepo; keep the two aligned when the shared workflow changes. When changing this workflow, replay the offline scenarios in [evals/cases.json](evals/cases.json) in fresh contexts, withholding expectations from the executing agent. Grade its actions and evidence claims; formatting checks alone cannot validate readiness decisions.

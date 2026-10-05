<!--
A good PR is small and does one thing. A reader should learn why it matters,
what changes, the important choice, and the evidence without reconstructing
them from the diff. The author can explain and defend every line before asking
for review, and stays responsible for AI-assisted work.

Write in increasing detail: toolkit author/user, new contributor, then
specialist. Three to five sentences per section is a ceiling, not a quota; one
is fine. Use bullets if clearer. Link existing issues, docs, and decisions
instead of copying them. Keep detail proportional to the change and its risk.
Delete every instruction comment before publishing, and omit Additional notes
when empty.
-->

<!--
Write the bare issue reference after the word: a Linear ID (team key, dash,
number, e.g. PLT-123) or a GitHub issue (#123). No brackets, no placeholder
text. The word before the ID is what Linear/GitHub acts on: `Closes` when
merging this PR completes the issue, `Part of` when the PR is only one piece
of it (the issue is linked and its status left alone). Replace `Closes` with
`Part of` as needed. If no issue exists yet, file one first. Do not write
"Linear issue:" or "Linear ticket:"; the former is a closing phrase and the
latter is not recognized. Keep the ID out of the PR title, which is
`type(scope): summary` (Conventional Commits; type `feat`, `fix`, or `chore`;
scope is the lib or area, e.g. `fix(arcade-mcp-server):`, `feat(arcade-cli):`).
-->

Closes

## What/why

<!--
What problem does this solve, and what observable behavior changes?
Use language a toolkit author or MCP client user can follow, with enough
context to understand without opening the issue. Where useful, explain how to
reproduce the old behavior and recognize the new one.
-->

## Codebase changes

<!--
Explain the approach and consequential decisions that are not obvious from
the diff, at a level a new contributor can follow. Say which side(s) of the
dual protocol are affected (MCP, Arcade Worker, or both) when relevant, and
which library versions were bumped. Skip file inventories and coding diaries.
-->

## Proof

<!--
Show that the change does what What/why promises, on the current head.

Verification: one row per behavior or state the change promises, saying how
it was proven. Name the command or tool used (`make check`, `make test`,
`uv run pytest libs/tests/...`, `arcade mcp stdio` against an example server,
MCP Inspector, a `/worker/tools/invoke` request). Say plainly what was run
for real, what was mocked and at which boundary, and what was only judged;
never let a mocked or skipped check read as a real run. State observed
results, not adjectives: "tools/call on an expired token returned
TOOL_RUNTIME_RETRY", not "Tested thoroughly". Keep this accurate after
revisions.

- User-visible output (CLI output, tool error payloads, schemas): fill the
  Before/After table with the relevant excerpt.
- Internal-only: drop the Before/After table; list the commands or requests
  run, the assertion, and the observed result, including the failing case now
  passing.
- Nothing runnable (workflow, manifest, pin, docs): drop both tables; say it
  was judged rather than run, and what it was checked against.

Example:

| Behavior                                     | How it was proven                                                         |
| -------------------------------------------- | ------------------------------------------------------------------------- |
| TypedDict fields carry descriptions          | Unit: `make test`, new test fails on main, passes here                    |
| stdio channel stays clean                    | Real: `arcade mcp stdio` with examples/mcp_servers/simple, no stray output |
| Worker invoke returns the same error payload | Mocked: upstream HTTP client patched, `/worker/tools/invoke` via TestClient |

| Before | After |
| ------ | ----- |
| `"description": null` | `"description": "Name to greet"` |
-->

| Behavior | How it was proven |
| -------- | ----------------- |
|          |                   |

| Before | After |
| ------ | ----- |
|        |       |

## Additional notes

<!--
Optional: material risks, verification gaps, rollout constraints, or a specific
reviewer decision. Omit this section when there is nothing to add.

For sensitive changes, explain what could be affected and how the risk is
controlled. Sensitive paths in this repo include:
- `libs/arcade-serve/` — worker JWT auth and `/worker/*` endpoints
- `libs/arcade-mcp-server/arcade_mcp_server/resource_server.py` — OAuth 2.1 token validation
- MCP stdio transport — any new stdout/stderr writes corrupt the JSON-RPC channel
- `pyproject.toml` files — version bumps, dependency floors, breaking-change semver
- Tool secrets / env-var flow — anything reachable from `context.get_secret()`

If patch coverage is below 85%, say why here.
-->

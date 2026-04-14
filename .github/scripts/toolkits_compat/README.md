# Toolkits Compatibility Automation

This directory powers `.github/workflows/toolkits-compat.yml`.

## What it does

1. Runs toolkit build + unit tests from `ArcadeAI/monorepo/apps/worker/toolkits` against the current `arcade-mcp` branch via `.local-overrides`.
2. Uses `toolkits-fix-pr` linkage to switch testing from `monorepo` `main` to a linked monorepo PR branch.
3. Auto-creates a draft monorepo PR if baseline compatibility fails.

## Scripts

- `run_toolkit_ci.sh`:
  - `make install` + `make build`
  - runs `pytest` with monorepo-like exit-code handling (`5` => no tests)
  - writes JSON result artifact per toolkit
- `parse_fix_pr_trailer.py`:
  - extracts `toolkits-fix-pr: https://github.com/ArcadeAI/monorepo/pull/<n>`
- `upsert_fix_pr_trailer.py`:
  - updates or appends the trailer in the `arcade-mcp` PR body
- `create_monorepo_fix_pr.sh`:
  - creates/reuses `arcade-mcp-compat/pr-<arcade_pr_number>` branch
  - opens a draft PR from template
  - includes failing toolkit result summary when artifacts are available

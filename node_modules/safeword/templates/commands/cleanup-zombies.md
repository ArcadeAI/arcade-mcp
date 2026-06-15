---
description: Kill zombie dev servers and test processes for this project
---

# Cleanup Zombies

Kill zombie processes (dev servers, Playwright browsers, test runners) for the current project only. Safe to use in multi-project environments.

## Instructions

Run the cleanup script with `--dry-run` first to preview what will be killed:

```bash
./.safeword/scripts/cleanup-zombies.sh --dry-run
```

If the output looks correct, run without `--dry-run`:

```bash
./.safeword/scripts/cleanup-zombies.sh
```

## What It Does

1. **Auto-detects framework** - Finds port from vite.config.ts, next.config.js, etc. (checks root, `packages/*/`, `apps/*/` for monorepos)
2. **Kills by port** - Dev server port AND test port (port + 1000)
3. **Kills test processes** - Playwright, Chromium, Electron (scoped to this project)
4. **Multi-project safe** - Only kills processes matching this project's directory

## Manual Override

If auto-detection fails or you need a specific port:

```bash
# Explicit port
./.safeword/scripts/cleanup-zombies.sh 5173

# Port + additional pattern
./.safeword/scripts/cleanup-zombies.sh 5173 "electron"
```

## When to Use

- Port already in use when starting dev server
- Tests hanging or failing due to zombie processes
- Switching between projects
- Before running E2E tests
- After interrupted test runs

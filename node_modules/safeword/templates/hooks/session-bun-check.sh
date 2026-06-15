#!/bin/bash
# Safeword: Bun runtime check (SessionStart)
# Verifies bun is available before other hooks run.
# This is a bash hook because it can't depend on the runtime it's checking for.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# Not a safeword project, skip silently
if [ ! -d "$PROJECT_DIR/.safeword" ]; then
  exit 0
fi

if ! command -v bun &> /dev/null; then
  echo "SAFEWORD: bun is required for quality hooks but was not found in PATH." >&2
  echo "All quality gates, auto-linting, and review hooks are inactive without it." >&2
  echo "" >&2
  echo "Install: curl -fsSL https://bun.sh/install | bash" >&2
  echo "Then restart your terminal and Claude Code session." >&2
  exit 2
fi

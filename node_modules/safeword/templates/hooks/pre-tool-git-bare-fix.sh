#!/bin/sh
# Safeword: PreToolUse Bash hook — reset core.bare=false before git commands
#
# Defends against an upstream Claude Code race
# (anthropics/claude-code#58345): parallel-worktree creation momentarily flips
# the parent repo's .git/config core.bare=true, and if anything reads it
# mid-flight the flag stays set. Subsequent git ops in any sibling worktree
# then fail with `fatal: this operation must be run in a work tree`.
#
# This hook fires before every Bash command beginning with `git` (filtered
# at the config level via `if: "Bash(git *)"`, so non-git Bash calls incur
# zero process-spawn overhead). The reset is idempotent: it only writes
# when core.bare is actually true, and silently no-ops otherwise.
#
# A defensive copy of the same reset still lives in .husky/pre-commit for
# coverage of git commits outside Claude Code (manual commits, IDE git UIs).
#
# Exits 0 unconditionally — never block Claude Code, even if git is missing
# or we're not in a repo.

# Drain stdin (Claude Code sends the PreToolUse JSON payload). We don't need
# its contents — the `if` filter already confirmed this is a git command.
cat > /dev/null 2>&1 || true

GIT_COMMON_DIR=$(git rev-parse --git-common-dir 2> /dev/null) || exit 0
[ -n "$GIT_COMMON_DIR" ] || exit 0

CONFIG_PATH="$GIT_COMMON_DIR/config"
[ -f "$CONFIG_PATH" ] || exit 0

# Only write if currently true — avoids redundant fs writes that would bump
# the config mtime on every git call.
CURRENT=$(git config -f "$CONFIG_PATH" --get core.bare 2> /dev/null || echo "")
if [ "$CURRENT" = "true" ]; then
  git config -f "$CONFIG_PATH" core.bare false 2> /dev/null || true
fi

exit 0

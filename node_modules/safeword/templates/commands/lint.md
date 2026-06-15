---
description: Run linters and formatters to fix code style issues (project)
---

# Lint

Run the full linting and formatting suite for the detected project type(s).

## Instructions

Run these commands based on project type. All detected languages run for polyglot projects.

```bash
# Python linting (if pyproject.toml or requirements.txt exists)
([ -f pyproject.toml ] || [ -f requirements.txt ]) && {
  # Ruff - fix code quality issues
  ruff check --fix . 2>&1 || true
  # Ruff - format all files
  ruff format . 2>&1 || true
  # mypy - type check
  mypy . 2>&1 || true
}

# JS/TS linting (if package.json exists)
[ -f package.json ] && {
  # ESLint - use lint:eslint if exists (projects with existing linter), else lint
  if grep -q '"lint:eslint"' package.json 2> /dev/null; then
    bun run lint:eslint 2>&1 || true
  else
    bun run lint 2>&1 || true
  fi
  # Prettier - format all files
  bun run format --if-present 2>&1 || true
  # TypeScript type check (if tsconfig.json exists)
  [ -f tsconfig.json ] && bunx tsc --noEmit 2>&1 || true
}

# Go linting (if go.mod exists)
[ -f go.mod ] && {
  # golangci-lint - fix and report issues
  golangci-lint run --fix ./... 2>&1 || true
  # golangci-lint - format
  golangci-lint fmt ./... 2>&1 || true
}
```

## Summary

After running, report:

1. Any linting errors that couldn't be auto-fixed (Ruff, ESLint, or golangci-lint)
2. Any formatting issues
3. Type errors (mypy or TypeScript)

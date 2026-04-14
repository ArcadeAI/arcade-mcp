#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${GH_TOKEN:-}" ]]; then
  echo "GH_TOKEN must be set to a token with write access to ${MONOREPO_REPO:-ArcadeAI/monorepo}." >&2
  exit 1
fi

if [[ -z "${ARCADE_PR_NUMBER:-}" || -z "${ARCADE_PR_URL:-}" ]]; then
  echo "ARCADE_PR_NUMBER and ARCADE_PR_URL must be set." >&2
  exit 1
fi

if [[ -z "${TEMPLATE_FILE:-}" || ! -f "${TEMPLATE_FILE}" ]]; then
  echo "TEMPLATE_FILE must point to an existing template file." >&2
  exit 1
fi

results_dir="${RESULTS_DIR:-}"

MONOREPO_REPO="${MONOREPO_REPO:-ArcadeAI/monorepo}"
MONOREPO_BASE_REF="${MONOREPO_BASE_REF:-main}"
branch_name="arcade-mcp-compat/pr-${ARCADE_PR_NUMBER}"
bootstrap_dir=".github/compat-bootstrap"
bootstrap_file="${bootstrap_dir}/arcade-mcp-pr-${ARCADE_PR_NUMBER}.md"
title="chore(worker): toolkit compatibility fixes for arcade-mcp #${ARCADE_PR_NUMBER}"

existing_pr_url="$(gh pr list \
  --repo "${MONOREPO_REPO}" \
  --state open \
  --head "${branch_name}" \
  --json url \
  --jq '.[0].url')"

if [[ -n "${existing_pr_url}" ]]; then
  echo "pr_url=${existing_pr_url}" >> "${GITHUB_OUTPUT}"
  exit 0
fi

git fetch origin "${MONOREPO_BASE_REF}"

if git ls-remote --heads origin "${branch_name}" | grep -q "${branch_name}"; then
  git checkout -B "${branch_name}" "origin/${branch_name}"
else
  git checkout -B "${branch_name}" "origin/${MONOREPO_BASE_REF}"
fi

mkdir -p "${bootstrap_dir}"
cat <<EOF > "${bootstrap_file}"
# Arcade MCP compatibility follow-up

This branch was generated automatically because toolkit compatibility checks failed for:

- Arcade MCP PR: ${ARCADE_PR_URL}
- Arcade MCP head sha: ${ARCADE_HEAD_SHA:-unknown}

Add fixes for toolkit compatibility on this branch.
EOF

git add "${bootstrap_file}"

if ! git diff --cached --quiet; then
  git -c user.name="github-actions[bot]" -c user.email="41898282+github-actions[bot]@users.noreply.github.com" \
    commit -m "chore: bootstrap compatibility branch for arcade-mcp #${ARCADE_PR_NUMBER}"
fi

git push --set-upstream origin "${branch_name}"

export BRANCH_NAME="${branch_name}"

pr_body="$(python - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

def build_failure_summary(results_dir: str) -> str:
    if not results_dir:
        return "- Result artifacts not available."
    path = Path(results_dir)
    if not path.exists():
        return "- Result artifacts not available."
    files = sorted(path.glob("*.json"))
    if not files:
        return "- Result artifacts not available."

    rows: list[str] = []
    for file_path in files:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        toolkit = str(data.get("toolkit", file_path.stem))
        status = str(data.get("status", "unknown"))
        exit_code = data.get("exit_code", "n/a")
        rows.append(f"- `{toolkit}`: `{status}` (exit code: `{exit_code}`)")
    return "\n".join(rows)

template = Path(os.environ["TEMPLATE_FILE"]).read_text(encoding="utf-8")
rendered = (
    template.replace("{{ARCADE_PR_NUMBER}}", os.environ["ARCADE_PR_NUMBER"])
    .replace("{{ARCADE_PR_URL}}", os.environ["ARCADE_PR_URL"])
    .replace("{{ARCADE_HEAD_SHA}}", os.environ.get("ARCADE_HEAD_SHA", "unknown"))
    .replace("{{BRANCH_NAME}}", os.environ["BRANCH_NAME"])
    .replace("{{FAILURE_SUMMARY}}", build_failure_summary(os.environ.get("RESULTS_DIR", "")))
)
print(rendered)
PY
)"

created_pr_url="$(gh pr create \
  --repo "${MONOREPO_REPO}" \
  --base "${MONOREPO_BASE_REF}" \
  --head "${branch_name}" \
  --title "${title}" \
  --body "${pr_body}" \
  --draft)"

echo "pr_url=${created_pr_url}" >> "${GITHUB_OUTPUT}"

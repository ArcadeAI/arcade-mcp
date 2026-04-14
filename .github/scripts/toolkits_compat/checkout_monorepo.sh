#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: checkout_monorepo.sh --repo <org/repo> --ref <git-ref> --path <dir>
Requires one of: MONOREPO_WRITE_PAT, MONOREPO_PAT, GH_PAT
EOF
}

repo=""
ref=""
target_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      repo="${2:-}"
      shift 2
      ;;
    --ref)
      ref="${2:-}"
      shift 2
      ;;
    --path)
      target_path="${2:-}"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${repo}" || -z "${ref}" || -z "${target_path}" ]]; then
  usage
  exit 2
fi

monorepo_token=""
for candidate in "${MONOREPO_WRITE_PAT:-}" "${MONOREPO_PAT:-}" "${GH_PAT:-}"; do
  if [[ -n "${candidate}" ]]; then
    monorepo_token="${candidate}"
    break
  fi
done

if [[ -z "${monorepo_token}" ]]; then
  echo "Missing monorepo token. Configure MONOREPO_WRITE_PAT, MONOREPO_PAT, or GH_PAT." >&2
  exit 1
fi

rm -rf "${target_path}"
GH_TOKEN="${monorepo_token}" gh repo clone "${repo}" "${target_path}" -- --depth 1 --branch "${ref}"
git -C "${target_path}" remote set-url origin "https://x-access-token:${monorepo_token}@github.com/${repo}.git"

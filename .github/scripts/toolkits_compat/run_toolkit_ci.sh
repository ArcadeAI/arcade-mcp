#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_toolkit_ci.sh --toolkit-name <name> --toolkit-dir <path> [--with-db-setup]
EOF
}

toolkit_name=""
toolkit_dir=""
with_db_setup="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --toolkit-name)
      toolkit_name="${2:-}"
      shift 2
      ;;
    --toolkit-dir)
      toolkit_dir="${2:-}"
      shift 2
      ;;
    --with-db-setup)
      with_db_setup="true"
      shift 1
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "${toolkit_name}" || -z "${toolkit_dir}" ]]; then
  usage
  exit 2
fi

if [[ ! -d "${toolkit_dir}" ]]; then
  echo "Toolkit directory does not exist: ${toolkit_dir}" >&2
  exit 2
fi

results_dir="${GITHUB_WORKSPACE:-$(pwd)}/toolkits-compat-results"
mkdir -p "${results_dir}"
result_file="${results_dir}/${toolkit_name}.json"

write_result() {
  local status="$1"
  local exit_code="$2"
  python - <<PY > "${result_file}"
import json
print(json.dumps({
  "toolkit": "${toolkit_name}",
  "status": "${status}",
  "exit_code": ${exit_code},
}, sort_keys=True))
PY
}

cd "${toolkit_dir}"

make install
make build

if [[ "${with_db_setup}" == "true" && -f tests/test_setup.sh ]]; then
  bash tests/test_setup.sh
fi

set +e
uv run pytest -W ignore -v --cov="arcade_${toolkit_name}" --cov-report=xml
test_exit_code=$?
set -e

if [[ "${test_exit_code}" -eq 0 ]]; then
  write_result "passed" 0
  exit 0
fi

if [[ "${test_exit_code}" -eq 5 ]]; then
  echo "No tests found for toolkit ${toolkit_name}, treating as success."
  write_result "no-tests" 5
  exit 0
fi

write_result "failed" "${test_exit_code}"
exit "${test_exit_code}"

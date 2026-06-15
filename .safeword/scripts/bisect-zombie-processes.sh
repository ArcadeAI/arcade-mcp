#!/bin/bash
# Bisect zombie processes: Find which test leaves processes behind
#
# Use when: Tests leave processes running, playwright browsers not cleaned up,
# port stays in use after tests, zombie node processes after test suite,
# can't find which test is leaving processes behind, chromium processes accumulate
#
# Usage: ./bisect-zombie-processes.sh <process_pattern> <name_pattern> [search_dir]
# Example: ./bisect-zombie-processes.sh 'chromium' '*.test.ts' tests
# Example: ./bisect-zombie-processes.sh 'node.*:3000' '*.spec.ts' e2e
# Example: ./bisect-zombie-processes.sh 'playwright' '*.test.ts'

set -e

if [ $# -lt 2 ]; then
  echo "Usage: $0 <process_pattern> <name_pattern> [search_dir]"
  echo "Example: $0 'chromium' '*.test.ts' tests"
  echo "Example: $0 'playwright' '*.test.ts'"
  echo ""
  echo "Runs tests one-by-one to find which leaves <process_pattern> running"
  echo "Override test command: TEST_CMD='pnpm test' $0 ..."
  exit 1
fi

# Detect package manager from lockfile
detect_runner() {
  if [ -f "pnpm-lock.yaml" ]; then
    echo "pnpm"
  elif [ -f "yarn.lock" ]; then
    echo "yarn"
  elif [ -f "bun.lockb" ]; then
    echo "bun"
  else
    echo "npm"
  fi
}

# Allow override via environment variable
RUNNER="${TEST_CMD:-$(detect_runner) test}"

PROCESS_PATTERN="$1"
NAME_PATTERN="$2"
SEARCH_DIR="${3:-.}"

echo "Searching for test that leaves process behind: $PROCESS_PATTERN"
echo "Test pattern: $NAME_PATTERN in $SEARCH_DIR"
echo ""

# Function to count matching processes
count_procs() {
  pgrep -f "$PROCESS_PATTERN" 2> /dev/null | wc -l | tr -d ' '
}

# Function to kill matching processes
kill_procs() {
  pkill -9 -f "$PROCESS_PATTERN" 2> /dev/null || true
}

# Get list of test files using find (portable across bash versions)
TEST_FILES=$(find "$SEARCH_DIR" -type f -name "$NAME_PATTERN" 2> /dev/null | sort)
TOTAL=$(echo "$TEST_FILES" | grep -c . || echo 0)

if [ "$TOTAL" -eq 0 ]; then
  echo "No test files found matching: $NAME_PATTERN in $SEARCH_DIR"
  exit 1
fi

echo "Found $TOTAL test files"
echo ""

# Clean up any existing matching processes first
INITIAL_COUNT=$(count_procs)
if [ "$INITIAL_COUNT" -gt 0 ]; then
  echo "Found $INITIAL_COUNT existing '$PROCESS_PATTERN' processes - cleaning up first..."
  kill_procs
  sleep 2

  REMAINING=$(count_procs)
  if [ "$REMAINING" -gt 0 ]; then
    echo "WARNING: Could not kill all processes. $REMAINING still running."
    echo "You may need to manually kill them first."
    exit 1
  fi
  echo "Cleanup complete."
  echo ""
fi

COUNT=0
for TEST_FILE in $TEST_FILES; do
  COUNT=$((COUNT + 1))

  # Get baseline process count
  BEFORE=$(count_procs)

  if [ "$BEFORE" -gt 0 ]; then
    echo "Zombie process found before test $COUNT/$TOTAL"
    echo "Clean up first or check previous test"
    exit 1
  fi

  echo "[$COUNT/$TOTAL] Testing: $TEST_FILE"

  # Run the test
  $RUNNER "$TEST_FILE" > /dev/null 2>&1 || true

  # Small delay for processes to settle
  sleep 1

  # Check if zombie processes appeared
  AFTER=$(count_procs)
  if [ "$AFTER" -gt 0 ]; then
    echo ""
    echo "FOUND ZOMBIE SPAWNER!"
    echo "  Test: $TEST_FILE"
    echo "  Process pattern: $PROCESS_PATTERN"
    echo "  Processes left behind: $AFTER"
    echo ""
    echo "Running processes:"
    pgrep -f "$PROCESS_PATTERN" | head -5 | while read -r pid; do
      ps -p "$pid" -o pid,command= 2> /dev/null | head -c 100
      echo ""
    done
    echo ""
    echo "To investigate:"
    echo "  $RUNNER $TEST_FILE    # Run just this test"
    echo "  cat $TEST_FILE         # Review test code for missing cleanup"
    exit 1
  fi
done

echo ""
echo "No zombie spawner found - all tests clean up properly!"
exit 0

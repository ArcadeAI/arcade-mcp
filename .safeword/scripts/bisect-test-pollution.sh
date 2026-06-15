#!/bin/bash
# Bisect test pollution: Find which test creates unwanted files or shared state
#
# Use when: Tests pass individually but fail together, tests leave files behind,
# tests affect each other, test isolation problems, shared state between tests
#
# Usage: ./bisect-test-pollution.sh <file_to_check> <name_pattern> [search_dir]
# Example: ./bisect-test-pollution.sh '.git' '*.test.ts' src
# Example: ./bisect-test-pollution.sh '.git' '*.test.ts'  (searches current dir)

set -e

if [ $# -lt 2 ]; then
  echo "Usage: $0 <file_to_check> <name_pattern> [search_dir]"
  echo "Example: $0 '.git' '*.test.ts' src"
  echo "Example: $0 '.git' '*.test.ts'"
  echo ""
  echo "Runs tests one-by-one to find which creates <file_to_check>"
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

POLLUTION_CHECK="$1"
NAME_PATTERN="$2"
SEARCH_DIR="${3:-.}"

echo "Searching for test that creates: $POLLUTION_CHECK"
echo "Test pattern: $NAME_PATTERN in $SEARCH_DIR"
echo ""

# Get list of test files using find (portable across bash versions)
TEST_FILES=$(find "$SEARCH_DIR" -type f -name "$NAME_PATTERN" 2> /dev/null | sort)
TOTAL=$(echo "$TEST_FILES" | grep -c . || echo 0)

if [ "$TOTAL" -eq 0 ]; then
  echo "No test files found matching: $NAME_PATTERN in $SEARCH_DIR"
  exit 1
fi

echo "Found $TOTAL test files"
echo ""

COUNT=0
for TEST_FILE in $TEST_FILES; do
  COUNT=$((COUNT + 1))

  # Skip if pollution already exists
  if [ -e "$POLLUTION_CHECK" ]; then
    echo "Pollution already exists before test $COUNT/$TOTAL"
    echo "Clean it up first: rm -rf $POLLUTION_CHECK"
    exit 1
  fi

  echo "[$COUNT/$TOTAL] Testing: $TEST_FILE"

  # Run the test
  $RUNNER "$TEST_FILE" > /dev/null 2>&1 || true

  # Check if pollution appeared
  if [ -e "$POLLUTION_CHECK" ]; then
    echo ""
    echo "FOUND POLLUTER!"
    echo "  Test: $TEST_FILE"
    echo "  Created: $POLLUTION_CHECK"
    echo ""
    echo "To investigate:"
    echo "  $RUNNER $TEST_FILE    # Run just this test"
    echo "  cat $TEST_FILE         # Review test code"
    exit 1
  fi
done

echo ""
echo "No polluter found - all tests clean!"
exit 0

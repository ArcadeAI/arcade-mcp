#!/bin/bash

set -e

# Get changed files from command line argument or environment variable
CHANGED_FILES="${1:-$CHANGED_FILES}"

if [ -z "$CHANGED_FILES" ]; then
  echo "No changed files provided"
  echo "packages=" >> $GITHUB_OUTPUT
  exit 0
fi

echo "Changed pyproject.toml files:"
echo "$CHANGED_FILES"

# Initialize array to store packages to release
packages_to_release=()

# Check each changed pyproject.toml
for file in $CHANGED_FILES; do
  echo "Checking $file..."

  # Get the full directory path (relative to repo root)
  package_dir=$(dirname "$file")

  # Check if this is a new file (added in this commit)
  if git diff HEAD^ HEAD --name-status -- "$file" | grep -E "^A\s+$file$" > /dev/null; then
    echo "New package detected: $file"
    packages_to_release+=("$package_dir")
  # Otherwise check for version changes
  elif git diff HEAD^ HEAD -- "$file" | grep -E '^\+version = ".*"$' > /dev/null; then
    echo "Version changed in $file"
    packages_to_release+=("$package_dir")
  else
    echo "No version change in $file"
  fi
done

# Output the packages to release
if [ ${#packages_to_release[@]} -eq 0 ]; then
  echo "No packages to release found."
  echo "packages=" >> $GITHUB_OUTPUT
else
  echo "Packages to release: ${packages_to_release[@]}"
  # Convert array to JSON format for matrix
  packages_json=$(printf '%s\n' "${packages_to_release[@]}" | jq -R . | jq -s -c .)
  echo "packages=$packages_json" >> $GITHUB_OUTPUT
fi

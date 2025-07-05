#!/bin/bash

HACS_FILE="hacs.json"
MANIFEST_FILE="custom_components/local_fcsp/manifest.json"

# Extract version using grep + cut
get_version() {
  grep '"version"' "$1" | head -1 | cut -d '"' -f4
}

hacs_version=$(get_version "$HACS_FILE")
manifest_version=$(get_version "$MANIFEST_FILE")

echo "Current hacs.json version: $hacs_version"
echo "Current manifest.json version: $manifest_version"

# Function to compare semantic versions, returns 0 if $1 > $2, else 1
version_gt() {
  IFS='.' read -r h_major h_minor h_patch <<< "$1"
  IFS='.' read -r m_major m_minor m_patch <<< "$2"

  if (( h_major > m_major )); then
    return 0
  elif (( h_major < m_major )); then
    return 1
  fi

  if (( h_minor > m_minor )); then
    return 0
  elif (( h_minor < m_minor )); then
    return 1
  fi

  if (( h_patch > m_patch )); then
    return 0
  else
    return 1
  fi
}

# Determine highest version
if version_gt "$hacs_version" "$manifest_version"; then
  highest_version="$hacs_version"
else
  highest_version="$manifest_version"
fi

echo "Highest current version: $highest_version"

# Increment patch version
IFS='.' read -r major minor patch <<< "$highest_version"
patch=$((patch + 1))
new_version="$major.$minor.$patch"

echo "New version: $new_version"

# Update version in both files (macOS sed syntax)
sed -i '' "s/\"version\": \"$hacs_version\"/\"version\": \"$new_version\"/" "$HACS_FILE"
sed -i '' "s/\"version\": \"$manifest_version\"/\"version\": \"$new_version\"/" "$MANIFEST_FILE"

echo "Updated versions in $HACS_FILE and $MANIFEST_FILE"


#!/bin/bash

HACS_FILE="hacs.json"
MANIFEST_FILE="custom_components/local_fcsp/manifest.json"

# Extract version using grep + cut
get_version() {
  grep '"version"' "$1" | head -1 | cut -d '"' -f4
}

current_version=$(get_version "$MANIFEST_FILE")
echo "Current version: $current_version"

# Get current year and month (no leading zero on month)
current_year=$(date +%Y)
current_month=$(date +%-m)

# Split existing version
IFS='.' read -r v_year v_month v_patch <<< "$current_version"

# If year and month match, increment patch; otherwise reset to 0
if [[ "$v_year" == "$current_year" && "$v_month" == "$current_month" ]]; then
  new_patch=$((v_patch + 1))
else
  new_patch=0
fi

new_version="${current_year}.${current_month}.${new_patch}"
echo "New version: $new_version"

# Update both files
sed -i '' "s/\"version\": \"$current_version\"/\"version\": \"$new_version\"/" "$HACS_FILE"
sed -i '' "s/\"version\": \"$current_version\"/\"version\": \"$new_version\"/" "$MANIFEST_FILE"

echo "Updated versions in $HACS_FILE and $MANIFEST_FILE"

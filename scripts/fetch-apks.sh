#!/usr/bin/env bash
# Downloads the APKs of each app's latest GitHub release (see apps.txt) into repo/.
# Files are renamed to <repo>-<tag>-<asset> so identical asset names don't collide.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p repo
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
grep -vE '^\s*(#|$)' apps.txt | while read -r repo assets; do
  tag=$(gh release view -R "$repo" --json tagName -q .tagName 2>/dev/null) || { echo "skip $repo: no release"; continue; }
  for asset in $assets; do
    gh release download "$tag" -R "$repo" -p "$asset" -D "$tmp" --clobber
    mv "$tmp/$asset" "repo/${repo#*/}-$tag-$asset"
    echo "got ${repo#*/} $tag $asset"
  done
done

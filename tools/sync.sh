#!/usr/bin/env bash
# Push whatever changed in the trip-site folder to GitHub Pages.
#
# The site is served straight from the repo, so a commit is a deploy. Edits
# made in Cowork and refreshed data files both go out the same way.
#
#   ./tools/sync.sh            # commit + push if anything changed
#   ./tools/sync.sh "message"  # with a custom commit subject
set -euo pipefail

cd "$(dirname "$0")/.."

if [ -z "$(git status --porcelain)" ]; then
  echo "nothing to sync — working tree is clean"
  exit 0
fi

echo "changed:"
git status --short

git add -A
git commit -m "${1:-Update trip site — $(date '+%Y-%m-%d %H:%M')}"
git push origin main

echo
echo "pushed. live in ~1 min at https://itaitunik-lang.github.io/usa-trip-2026/"

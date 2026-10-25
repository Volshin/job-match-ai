#!/bin/bash
# Rebuild the public (anonymised) dashboard and publish it via GitHub Pages.
# Usage: ./publish.sh            build, commit docs/ and push
#        ./publish.sh --dry-run  build only, do not commit or push
set -euo pipefail
cd "$(dirname "$0")"

UV=${UV:-/opt/homebrew/bin/uv}

# GitHub Pages serves docs/ from main
branch=$(git branch --show-current)
if [ "$branch" != "main" ]; then
  echo "Refusing to publish from branch '$branch': switch to main first." >&2
  exit 1
fi

"$UV" run --project mcp-stdio python mcp-stdio/server.py build-dashboard --public

# Safety net: never publish a file that was not built in public mode
if ! grep -q '"public": true' docs/index.html; then
  echo "docs/index.html is not a public build, aborting." >&2
  exit 1
fi

# Keep Jekyll from processing docs/
touch docs/.nojekyll

if [ "${1:-}" = "--dry-run" ]; then
  echo "Dry run: built docs/index.html, nothing committed."
  exit 0
fi

git add docs/index.html docs/.nojekyll
if git diff --cached --quiet -- docs/index.html docs/.nojekyll; then
  echo "Dashboard unchanged, nothing to publish."
  exit 0
fi

# Commit only the dashboard files, whatever else is staged
git commit -q -m "Update public dashboard $(date +%d.%m.%Y)" -- docs/index.html docs/.nojekyll
git push
echo "Published."

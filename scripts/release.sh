#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-v0.1.0}"

echo "[release] Preparing to release ${VERSION}"

git fetch --tags

# Create tag if it doesn't exist
if git rev-parse "refs/tags/${VERSION}" >/dev/null 2>&1; then
  echo "[release] Tag ${VERSION} already exists."
else
  git tag -a "${VERSION}" -m "Release ${VERSION}"
fi

git push origin "${VERSION}"

if command -v gh >/dev/null 2>&1; then
  echo "[release] Creating GitHub release..."
  gh release create "${VERSION}" -t "Release ${VERSION}" -n "Automated release from Claude Code session."
else
  echo "[release] gh CLI not found; skipped GitHub release creation. Tag pushed nonetheless."
fi

echo "[release] Release process complete."

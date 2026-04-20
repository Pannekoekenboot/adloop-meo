#!/usr/bin/env bash
# Build the Next.js approval UI and copy the static export into the
# Python package so `adloop web` serves it from the same origin as
# /api. Run this before committing UI changes or cutting a release.
#
# Usage:
#   scripts/build-web-ui.sh
#
# Requires: Node 20+ and npm. Run from the repo root or anywhere —
# this script finds its own way.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UI_SRC="$REPO_ROOT/web-ui"
UI_OUT="$UI_SRC/out"
PKG_STATIC="$REPO_ROOT/src/adloop/web/static"

if [ ! -d "$UI_SRC" ]; then
  echo "error: $UI_SRC not found" >&2
  exit 1
fi

cd "$UI_SRC"

if [ ! -d node_modules ]; then
  echo "→ Installing web-ui dependencies…"
  npm install
fi

echo "→ Building Next.js static export…"
npm run build

if [ ! -d "$UI_OUT" ]; then
  echo "error: Next.js did not produce $UI_OUT" >&2
  exit 1
fi

echo "→ Copying bundle to $PKG_STATIC"
rm -rf "$PKG_STATIC"
mkdir -p "$PKG_STATIC"
# rsync preserves the out/ layout (including the _next/ dir with a
# leading underscore, which some copy tools skip).
rsync -a --delete "$UI_OUT/" "$PKG_STATIC/"

echo "✓ UI bundle ready at $PKG_STATIC"

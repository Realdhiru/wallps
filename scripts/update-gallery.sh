#!/usr/bin/env bash
# ==============================================================================
# scripts/update-gallery.sh
# One-command automated gallery updater for the wallpaper collection.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🎨 Updating Wallpaper Previews and GitHub Gallery..."
python3 "$SCRIPT_DIR/generate_gallery.py" "$ROOT_DIR"

echo "✅ Success! Previews and README.md are up to date."
echo ""
echo "Next steps:"
echo "  git status"
echo "  git add ."
echo "  git commit -m \"Update wallpapers\""
echo "  git push"

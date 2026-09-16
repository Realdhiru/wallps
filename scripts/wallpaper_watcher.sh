#!/usr/bin/env bash
# ==============================================================================
# scripts/wallpaper_watcher.sh
# Real-time wallpaper daemon using inotifywait.
# Automatically detects new wallpapers dropped into ~/Pictures/Wallpapers,
# sanitizes filenames, classifies color shades, generates WebP previews,
# updates README.md, and syncs to GitHub with desktop notifications.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "👀 Watching for new wallpapers in $REPO_DIR..."

# Ingest any files already sitting in root
python3 "$SCRIPT_DIR/auto_organize.py"

# Continuously monitor root and category directories
inotifywait -m -r -q \
    -e close_write -e moved_to \
    --exclude "(\.git|previews|scripts|.*\.webp|.*\.tmp|.*~)" \
    --format "%w%f" \
    "$REPO_DIR" | while read -r FILE_PATH; do

    # Ignore directories and non-media files
    if [[ ! -f "$FILE_PATH" ]]; then
        continue
    fi

    # Check extension
    EXT="${FILE_PATH##*.}"
    EXT_LOWER="$(echo "$EXT" | tr '[:upper:]' '[:lower:]')"
    case "$EXT_LOWER" in
        jpg|jpeg|png|gif|mp4)
            echo "⚡ New wallpaper detected: $FILE_PATH"
            # Small delay to ensure writer released file lock
            sleep 1
            python3 "$SCRIPT_DIR/auto_organize.py" "$FILE_PATH" || true
            ;;
        *)
            # Not a wallpaper format, ignore
            ;;
    esac
done

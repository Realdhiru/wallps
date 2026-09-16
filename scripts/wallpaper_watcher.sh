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

echo "👀 Watching for wallpaper changes in $REPO_DIR..."

# Ingest any files already sitting in root
python3 "$SCRIPT_DIR/auto_organize.py"

# Continuously monitor root and category directories
inotifywait -m -r -q \
    -e close_write -e moved_to -e delete -e moved_from \
    --exclude "(\.git|previews|scripts|.*\.webp|.*\.tmp|.*~)" \
    --format "%e %w%f" \
    "$REPO_DIR" | while read -r EVENT FILE_PATH; do

    # Ignore directory events
    if [[ "$EVENT" =~ "ISDIR" ]]; then
        continue
    fi

    # Check extension
    EXT="${FILE_PATH##*.}"
    EXT_LOWER="$(echo "$EXT" | tr '[:upper:]' '[:lower:]')"
    case "$EXT_LOWER" in
        jpg|jpeg|png|gif|mp4)
            if [[ "$EVENT" =~ "DELETE" || "$EVENT" =~ "MOVED_FROM" ]]; then
                echo "🗑️ Wallpaper deleted: $FILE_PATH"
                python3 "$SCRIPT_DIR/auto_organize.py" --delete "$FILE_PATH" || true
            elif [[ "$EVENT" =~ "CLOSE_WRITE" || "$EVENT" =~ "MOVED_TO" ]]; then
                if [[ -f "$FILE_PATH" ]]; then
                    echo "⚡ New wallpaper detected: $FILE_PATH"
                    # Small delay to ensure writer released file lock
                    sleep 1
                    python3 "$SCRIPT_DIR/auto_organize.py" "$FILE_PATH" || true
                fi
            fi
            ;;
        *)
            # Not a wallpaper format, ignore
            ;;
    esac
done

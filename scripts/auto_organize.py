#!/usr/bin/env python3
"""
scripts/auto_organize.py
Zero-touch wallpaper ingestion engine.
Detects dropped wallpapers, cleans filenames to kebab-case,
classifies color shades or media formats, generates previews,
rebuilds the README gallery, and auto-commits to Git.
"""

import os
import sys
import re
import time
import shutil
import subprocess
import colorsys
import urllib.parse
from collections import defaultdict
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
VALID_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".mp4", ".webp"}
KNOWN_CATEGORIES = {"dark", "blue", "warm", "purple", "green", "light", "gifs", "videos"}

def notify_desktop(title, body, icon="preferences-desktop-wallpaper"):
    """Send a desktop notification via notify-send (non-blocking, best-effort)."""
    try:
        subprocess.Popen(
            ["notify-send", "-a", "Wallpaper Organizer", "-i", icon, title, body],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        pass

PICKER_ACTIVE_PATHS = [
    Path(f"/run/user/{os.getuid()}/quickshell/wallpaper_picker/picker_active"),
    Path("/tmp/quickshell/wallpaper_picker/picker_active"),
]

def is_picker_active():
    """Returns True if QuickShell wallpaper picker is currently open/active."""
    return any(p.exists() for p in PICKER_ACTIVE_PATHS)

SEARCH_MAP_PATHS = [
    Path.home() / ".cache" / "quickshell" / "wallpaper_picker" / "search_map.txt",
    Path(f"/run/user/{os.getuid()}/quickshell/wallpaper_picker/search_map.txt"),
    Path("/tmp/quickshell/wallpaper_picker/search_map.txt"),
]

SEARCH_LOG_PATHS = [
    Path(f"/run/user/{os.getuid()}/quickshell/logs/ddg_downloader.log"),
    Path.home() / ".cache" / "quickshell" / "logs" / "ddg_downloader.log",
]

def clean_text_to_kebab(text):
    if not text:
        return ""
    # Unquote URL encoding
    text = urllib.parse.unquote(text)
    # Remove file extensions if at the end
    text = re.sub(r"\.(jpg|jpeg|png|gif|mp4|webp|webm)$", "", text, flags=re.IGNORECASE)
    # Strip site prefixes specifically
    text = re.sub(r"(?i)^(wallpaperflare\.com|wallhaven|deviantart|artstation)[_\-\.]+", "", text)
    # Strip resolution tokens and generic web clutter
    text = re.sub(r"(?i)\b(\d+k|uhd|fhd|1080p|1440p|2160p|ultra\s*hd)\b", " ", text)
    text = re.sub(r"(?i)\b(free\s*download)\b", " ", text)
    # Split camelCase / PascalCase
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    # Lowercase
    text = text.lower()
    # Replace non-alphanumeric with dashes
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Collapse multiple dashes and strip
    return re.sub(r"-+", "-", text).strip("-")

def lookup_search_metadata(filename):
    """Finds URL or search query for a ddg_ downloaded file."""
    for map_path in SEARCH_MAP_PATHS:
        if map_path.exists():
            try:
                for line in map_path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if "|" in line:
                        parts = line.split("|")
                        if parts[0].strip() == filename:
                            full_url = parts[1].strip() if len(parts) > 1 else ""
                            title = parts[2].strip() if len(parts) > 2 else ""
                            return full_url, title
            except Exception:
                pass

    # If not found directly, check latest search query in logs
    latest_query = ""
    for log_path in SEARCH_LOG_PATHS:
        if log_path.exists():
            try:
                for line in reversed(log_path.read_text(encoding="utf-8", errors="ignore").splitlines()):
                    if "Starting search for:" in line:
                        latest_query = line.split("Starting search for:")[-1].replace("===", "").strip()
                        break
                if latest_query:
                    break
            except Exception:
                pass

    return "", latest_query

def sanitize_name(filename):
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"

    clean = ""

    # If it is a DDG search download
    if stem.startswith("ddg_"):
        full_url, title = lookup_search_metadata(Path(filename).name)
        # Try title first
        if title:
            cand = clean_text_to_kebab(title)
            if cand and not cand.isdigit() and len(cand) >= 3:
                clean = cand

        # Try URL path basename next
        if not clean and full_url:
            parsed_path = urllib.parse.urlparse(full_url).path
            url_stem = Path(parsed_path).stem
            cand = clean_text_to_kebab(url_stem)
            if cand and not cand.isdigit() and len(cand) >= 3:
                clean = cand

        # Try query fallback
        if not clean and title:
            cand = clean_text_to_kebab(title)
            if cand:
                clean = cand

        # Last resort: use a short slice of the uuid
        if not clean:
            clean = "wallpaper-" + stem[4:12]
    else:
        # Manual filename sanitization
        clean = clean_text_to_kebab(stem)

    if not clean:
        clean = "wallpaper"

    return f"{clean}{ext}"

def classify_static(filepath):
    im_cmd = "magick" if shutil.which("magick") else "convert"
    cmd = [im_cmd, str(filepath), "-resize", "32x32!", "-depth", "8", "rgb:-"]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    raw = proc.stdout
    if len(raw) != 3072:
        return "dark"

    pixels = []
    for i in range(0, len(raw), 3):
        r, g, b = raw[i], raw[i+1], raw[i+2]
        h, s, v = colorsys.rgb_to_hsv(r/255.0, g/255.0, b/255.0)
        pixels.append((h*360.0, s, v))

    n = len(pixels)
    avg_v = sum(p[2] for p in pixels) / n
    avg_s = sum(p[1] for p in pixels) / n
    dark_count = sum(1 for p in pixels if p[2] < 0.22)
    light_count = sum(1 for p in pixels if p[2] > 0.75 and p[1] < 0.25)

    hue_weights = defaultdict(float)
    chromatic_weight = 0.0

    for h, s, v in pixels:
        if v < 0.18 or s < 0.15:
            continue
        w = s * v
        chromatic_weight += w
        if (0 <= h < 65) or (335 <= h <= 360):
            hue_weights["warm"] += w
        elif 65 <= h < 165:
            hue_weights["green"] += w
        elif 165 <= h < 260:
            hue_weights["blue"] += w
        elif 260 <= h < 335:
            hue_weights["purple"] += w

    if avg_v < 0.20 or (dark_count / n > 0.65 and chromatic_weight < 85):
        return "dark"
    if avg_v > 0.75 and avg_s < 0.25 and light_count / n > 0.45:
        return "light"
    if chromatic_weight > 25 and hue_weights:
        return max(hue_weights.items(), key=lambda x: x[1])[0]
    if avg_v < 0.35:
        return "dark"
    if avg_v > 0.65:
        return "light"
    if hue_weights:
        return max(hue_weights.items(), key=lambda x: x[1])[0]
    return "dark"

def update_active_wallpaper_references(old_path, new_path):
    current_txt = Path.home() / ".cache" / "current_wallpaper.txt"
    last_txt = Path.home() / ".cache" / "last_wallpaper.txt"
    for txt in (current_txt, last_txt):
        try:
            if txt.exists() and txt.read_text().strip() == str(old_path.resolve()):
                txt.write_text(str(new_path.resolve()) + "\n")
        except Exception:
            pass

    try:
        thumb_sh = Path.home() / ".config" / "hypr" / "scripts" / "wallpaper_thumbnail.sh"
        if thumb_sh.exists():
            subprocess.Popen([str(thumb_sh)])
    except Exception:
        pass

def process_file(filepath, force=False):
    path = Path(filepath).resolve()
    if not path.is_file():
        return None

    ext = path.suffix.lower()
    if ext not in VALID_EXTS:
        return None

    try:
        rel_to_repo = path.relative_to(REPO_DIR)
    except ValueError:
        return None

    parts = rel_to_repo.parts

    # Case 1: File is placed inside a known category folder
    if len(parts) == 2 and parts[0] in KNOWN_CATEGORIES:
        category = parts[0]
        cat_dir = REPO_DIR / category
        clean_name = sanitize_name(path.name)
        dest_path = cat_dir / clean_name

        if dest_path != path:
            counter = 1
            stem = dest_path.stem
            final_ext = dest_path.suffix
            while dest_path.exists() and dest_path != path:
                dest_path = cat_dir / f"{stem}-{counter}{final_ext}"
                counter += 1

            shutil.move(str(path), str(dest_path))
            print(f"Renamed in {category}: {path.name} -> {dest_path.name}")
            update_active_wallpaper_references(path, dest_path)
    # Case 2: File is dropped in repository root or needs categorization
    else:
        # If the QuickShell wallpaper picker is currently open/active, do not shift yet
        if is_picker_active() and not force:
            print(f"Skipping {path.name}: wallpaper picker is currently active (will organize on close)")
            return None

        clean_name = sanitize_name(path.name)
        if ext == ".gif":
            category = "gifs"
        elif ext == ".mp4":
            category = "videos"
        else:
            category = classify_static(path)

        cat_dir = REPO_DIR / category
        cat_dir.mkdir(exist_ok=True)
        dest_path = cat_dir / clean_name

        counter = 1
        stem = dest_path.stem
        final_ext = dest_path.suffix
        while dest_path.exists() and dest_path != path:
            dest_path = cat_dir / f"{stem}-{counter}{final_ext}"
            counter += 1

        shutil.move(str(path), str(dest_path))
        print(f"Auto-moved: {path.name} -> {category}/{dest_path.name}")
        update_active_wallpaper_references(path, dest_path)
        notify_desktop("Wallpaper Added", f"{dest_path.name}\n→ {category}/")

    # Regenerate gallery and preview
    print("Updating previews and README...")
    subprocess.run(["python3", str(REPO_DIR / "scripts" / "generate_gallery.py"), str(REPO_DIR)],
                   check=True)

    # Auto Git Commit & Push (safely stage only organized destination, README, and previews)
    try:
        rel_dest = str(dest_path.relative_to(REPO_DIR))
        subprocess.run(["git", "add", "README.md", "previews/", rel_dest], cwd=REPO_DIR, check=True)
        commit_msg = f"Auto-add wallpaper: {dest_path.name} ({category})"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)
        subprocess.Popen(["git", "push", "origin", "main"], cwd=REPO_DIR)
        print("Auto-pushed changes to GitHub in background.")
    except subprocess.CalledProcessError:
        pass

    return dest_path

def handle_delete(filepath):
    path = Path(filepath)
    try:
        rel = path.relative_to(REPO_DIR)
    except ValueError:
        try:
            rel = path.resolve().relative_to(REPO_DIR.resolve())
        except ValueError:
            return

    parts = rel.parts
    if len(parts) >= 2 and parts[0] in KNOWN_CATEGORIES:
        category = parts[0]
        filename = parts[-1]

        # Purge corresponding preview
        preview_path = REPO_DIR / "previews" / category / f"{filename}.webp"
        if preview_path.exists():
            try:
                preview_path.unlink()
                print(f"Purged preview: {preview_path.relative_to(REPO_DIR)}")
            except OSError:
                pass

        # Purge source file if it still exists
        source_path = REPO_DIR / category / filename
        if source_path.exists():
            try:
                source_path.unlink()
            except OSError:
                pass

        # Regenerate gallery and clean any orphaned previews
        print(f"Updating gallery after deleting {filename}...")
        subprocess.run(["python3", str(REPO_DIR / "scripts" / "generate_gallery.py"), str(REPO_DIR)],
                       check=True)

        # Auto Git Commit & Push (safely stage only category folder, README, and previews)
        try:
            subprocess.run(["git", "add", "-u", category], cwd=REPO_DIR, check=True)
            subprocess.run(["git", "add", "README.md", "previews/"], cwd=REPO_DIR, check=True)
            diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_DIR)
            if diff_check.returncode != 0:
                commit_msg = f"Delete wallpaper: {filename} ({category})"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)
                subprocess.Popen(["git", "push", "origin", "main"], cwd=REPO_DIR)
                print(f"Auto-committed and pushed deletion of {filename}")
        except subprocess.CalledProcessError as e:
            print(f"Git commit error: {e}")

        notify_desktop("Wallpaper Deleted", f"{filename} removed from {category}/", icon="user-trash")

def scan_root_inbox(force=False):
    # Scan root of REPO_DIR for loose wallpapers
    for entry in os.listdir(REPO_DIR):
        p = REPO_DIR / entry
        if p.is_file() and p.suffix.lower() in VALID_EXTS:
            process_file(p, force=force)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--delete" and len(sys.argv) > 2:
            handle_delete(sys.argv[2])
        elif sys.argv[1] == "--sync":
            scan_root_inbox(force=True)
            subprocess.run(["python3", str(REPO_DIR / "scripts" / "generate_gallery.py"), str(REPO_DIR)], check=True)
            # Auto git commit & push after full sync
            try:
                subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
                diff_check = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=REPO_DIR)
                if diff_check.returncode != 0:
                    subprocess.run(["git", "commit", "-m", "Sync: reorganize wallpapers & update gallery"], cwd=REPO_DIR, check=True)
                    subprocess.Popen(["git", "push", "origin", "main"], cwd=REPO_DIR)
                    print("Auto-committed and pushed sync changes.")
                    notify_desktop("Wallpaper Sync", "Gallery synced and pushed to GitHub.")
                else:
                    print("No changes to commit after sync.")
            except subprocess.CalledProcessError as e:
                print(f"Git sync error: {e}")
        elif sys.argv[1] in ("--force", "--now"):
            scan_root_inbox(force=True)
        else:
            process_file(sys.argv[1])
    else:
        scan_root_inbox()


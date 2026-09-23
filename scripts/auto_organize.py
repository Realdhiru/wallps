#!/usr/bin/env python3
"""
scripts/auto_organize.py
Zero-touch wallpaper ingestion engine.
Detects dropped wallpapers, cleans filenames to kebab-case,
classifies into curated aesthetic rice shade folders, generates previews,
and rebuilds the README gallery without automatic git commits.
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
KNOWN_CATEGORIES = {
    "nord", "ocean", "emerald", "sakura", "sunset",
    "synthwave", "gruvbox", "dark", "light", "gifs", "videos"
}

GENERIC_NAMES_RE = re.compile(
    r"^(wal\d*|wallpaper\d*|image\d*|download\d*|img\d*|screenshot\d*|\d+|"
    r"picture\d*|photo\d*|unnamed\d*|desktop\d*|background\d*|dsc\d*|wallhaven\d*)$",
    re.IGNORECASE
)
HASH_RE = re.compile(r"^([a-z0-9]{6}|[a-f0-9\-]{16,})$", re.IGNORECASE)

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
    text = urllib.parse.unquote(text)
    text = re.sub(r"\.(jpg|jpeg|png|gif|mp4|webp|webm)$", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)^(wallpaperflare\.com|wallhaven|deviantart|artstation)[_\-\.]+", "", text)
    text = re.sub(r"(?i)\b(\d+k|uhd|fhd|1080p|1440p|2160p|ultra\s*hd)\b", " ", text)
    text = re.sub(r"(?i)\b(free\s*download|wallpaper|background|desktop)\b", " ", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")

def is_name_generic_or_hash(name):
    if not name or len(name) < 3:
        return True
    if GENERIC_NAMES_RE.match(name) or HASH_RE.match(name):
        return True
    return False

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

def sanitize_name(filename, category=None):
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"

    clean = ""

    # Case A: DDG search download
    if stem.startswith("ddg_"):
        full_url, title = lookup_search_metadata(Path(filename).name)
        if title:
            cand = clean_text_to_kebab(title)
            if cand and not is_name_generic_or_hash(cand):
                clean = cand

        if not clean and full_url:
            parsed_path = urllib.parse.urlparse(full_url).path
            url_stem = Path(parsed_path).stem
            cand = clean_text_to_kebab(url_stem)
            if cand and not is_name_generic_or_hash(cand):
                clean = cand

        if not clean and title:
            cand = clean_text_to_kebab(title)
            if cand:
                clean = cand

        if not clean:
            prefix = category if category else "aesthetic"
            clean = f"{prefix}-wallpaper-{stem[4:12]}"
    else:
        # Case B: Direct file drop
        cand = clean_text_to_kebab(stem)
        if cand and not is_name_generic_or_hash(cand):
            clean = cand
        else:
            # Check latest search query as fallback
            _, latest_query = lookup_search_metadata("")
            if latest_query:
                q_clean = clean_text_to_kebab(latest_query)
                if q_clean and not is_name_generic_or_hash(q_clean):
                    clean = q_clean

            if not clean:
                prefix = category if category else "aesthetic"
                uuid_slice = hex(int(time.time() * 1000))[-6:]
                clean = f"{prefix}-wallpaper-{uuid_slice}"

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
    light_count = sum(1 for p in pixels if p[2] > 0.75 and p[1] < 0.28)

    # Check for OLED / midnight noir first
    if avg_v < 0.20 or (dark_count / n > 0.65 and avg_s < 0.35):
        return "dark"
    if avg_v > 0.78 and avg_s < 0.22 and light_count / n > 0.45:
        return "light"

    hue_weights = defaultdict(float)
    chromatic_weight = 0.0

    for h, s, v in pixels:
        if v < 0.16 or s < 0.12:
            continue
        w = s * v
        chromatic_weight += w

        # Sakura / Pink / Rose (H: 315-355 with moderate/high V and S < 0.75 or soft pink)
        if 315 <= h < 355:
            if s > 0.65 and v < 0.70:
                hue_weights["synthwave"] += w * 1.2
            else:
                hue_weights["sakura"] += w * 1.3
        elif (355 <= h <= 360) or (0 <= h < 18):
            if v > 0.65 and s < 0.55:
                hue_weights["sakura"] += w * 1.1
            else:
                hue_weights["sunset"] += w * 1.2
        elif 18 <= h < 45:
            # Sunset (fiery orange/red) vs Gruvbox (earthy amber/brown)
            if s > 0.60 and v > 0.60:
                hue_weights["sunset"] += w * 1.2
            else:
                hue_weights["gruvbox"] += w * 1.2
        elif 45 <= h < 68:
            # Gruvbox (warm yellow/mustard/sepia)
            hue_weights["gruvbox"] += w * 1.3
        elif 68 <= h < 165:
            # Emerald (forest, nature, sage, matcha)
            hue_weights["emerald"] += w * 1.2
        elif 165 <= h < 205:
            # Nord (icy cyan, teal, arctic frost)
            hue_weights["nord"] += w * 1.3
        elif 205 <= h < 260:
            # Ocean (deep blue, cobalt, navy)
            hue_weights["ocean"] += w * 1.2
        elif 260 <= h < 315:
            # Synthwave (cyberpunk neon, electric violet, magenta)
            hue_weights["synthwave"] += w * 1.3

    if chromatic_weight < 20:
        if avg_v < 0.35:
            return "dark"
        if avg_v > 0.65:
            return "light"

    if hue_weights:
        return max(hue_weights.items(), key=lambda x: x[1])[0]

    if avg_v < 0.35:
        return "dark"
    return "light"

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
        clean_name = sanitize_name(path.name, category=category)
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
        else:
            preview_path = REPO_DIR / "previews" / category / f"{path.name}.webp"
            if preview_path.exists():
                return path
    # Case 2: File is dropped in repository root or needs categorization
    else:
        if is_picker_active() and not force:
            print(f"Skipping {path.name}: wallpaper picker is currently active (will organize on close)")
            return None

        if ext == ".gif":
            category = "gifs"
        elif ext == ".mp4":
            category = "videos"
        else:
            category = classify_static(path)

        clean_name = sanitize_name(path.name, category=category)
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

    # Regenerate gallery and preview (leaves working tree unstaged for user review)
    print("Updating previews and README...")
    subprocess.run(["python3", str(REPO_DIR / "scripts" / "generate_gallery.py"), str(REPO_DIR)],
                   check=True)

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

        print(f"Updating gallery after deleting {filename}...")
        subprocess.run(["python3", str(REPO_DIR / "scripts" / "generate_gallery.py"), str(REPO_DIR)],
                       check=True)

        notify_desktop("Wallpaper Deleted", f"{filename} removed from {category}/", icon="user-trash")

def scan_root_inbox(force=False):
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
            notify_desktop("Wallpaper Sync", "Gallery synchronized across all categories.")
        elif sys.argv[1] in ("--force", "--now"):
            scan_root_inbox(force=True)
        else:
            process_file(sys.argv[1])
    else:
        scan_root_inbox()

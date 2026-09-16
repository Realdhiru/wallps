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
import shutil
import subprocess
import colorsys
from collections import defaultdict
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
VALID_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".mp4"}
KNOWN_CATEGORIES = {"dark", "blue", "warm", "purple", "green", "light", "gifs", "videos"}

def sanitize_name(filename):
    stem = Path(filename).stem
    ext = Path(filename).suffix.lower()
    if ext == ".jpeg":
        ext = ".jpg"
    elif ext == ".png":
        ext = ".png"

    # Remove ddg prefixes, url hashes, random junk
    clean = stem
    if clean.startswith("ddg_"):
        clean = "wallpaper-" + clean[4:12]

    # Convert to lowercase
    clean = clean.lower()
    # Replace non-alphanumeric (except dashes and dots) with dashes
    clean = re.sub(r"[^a-z0-9\-\.]+", "-", clean)
    # Collapse multiple dashes
    clean = re.sub(r"-+", "-", clean).strip("-")
    if not clean:
        clean = "wallpaper"

    return f"{clean}{ext}"

def classify_static(filepath):
    cmd = ["magick", str(filepath), "-resize", "32x32!", "-depth", "8", "rgb:-"]
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

def notify(title, message):
    try:
        subprocess.run(["notify-send", "-a", "Wallpaper Manager", title, message],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def process_file(filepath):
    path = Path(filepath).resolve()
    if not path.is_file():
        return None

    ext = path.suffix.lower()
    if ext not in VALID_EXTS:
        return None

    rel_to_repo = path.relative_to(REPO_DIR)
    parts = rel_to_repo.parts

    # If it's already inside a category folder and properly named
    if len(parts) == 2 and parts[0] in KNOWN_CATEGORIES:
        category = parts[0]
        dest_path = path
    else:
        # Determine category and clean name
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

        # Ensure no name collision
        counter = 1
        stem = dest_path.stem
        while dest_path.exists() and dest_path != path:
            dest_path = cat_dir / f"{stem}-{counter}{ext}"
            counter += 1

        shutil.move(str(path), str(dest_path))
        print(f"📦 Auto-moved: {path.name} -> {category}/{dest_path.name}")

        # Update current and last wallpaper references if the active wallpaper was moved
        current_txt = Path.home() / ".cache" / "current_wallpaper.txt"
        last_txt = Path.home() / ".cache" / "last_wallpaper.txt"
        for txt in (current_txt, last_txt):
            try:
                if txt.exists() and txt.read_text().strip() == str(path.resolve()):
                    txt.write_text(str(dest_path.resolve()) + "\n")
            except Exception:
                pass

        # Trigger desktop wallpaper thumbnail indexing
        try:
            subprocess.Popen([str(Path.home() / ".config" / "hypr" / "scripts" / "wallpaper_thumbnail.sh")])
        except Exception:
            pass

    # Regenerate gallery and preview
    print("🎨 Updating previews and README...")
    subprocess.run(["python3", str(REPO_DIR / "scripts" / "generate_gallery.py"), str(REPO_DIR)],
                   check=True)

    # Auto Git Commit & Push
    try:
        subprocess.run(["git", "add", "-A"], cwd=REPO_DIR, check=True)
        commit_msg = f"Auto-add wallpaper: {dest_path.name} ({category})"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=REPO_DIR, check=True)
        subprocess.Popen(["git", "push", "origin", "main"], cwd=REPO_DIR)
        print("🚀 Auto-pushed changes to GitHub in background.")
    except subprocess.CalledProcessError:
        pass

    notify("🖼️ Wallpaper Added", f"Organized into {category}/{dest_path.name}")
    return dest_path

def scan_root_inbox():
    # Scan root of REPO_DIR for any loose wallpapers
    for entry in os.listdir(REPO_DIR):
        p = REPO_DIR / entry
        if p.is_file() and p.suffix.lower() in VALID_EXTS:
            process_file(p)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = sys.argv[1]
        process_file(target)
    else:
        scan_root_inbox()

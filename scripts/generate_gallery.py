#!/usr/bin/env python3
"""
scripts/generate_gallery.py
Automated wallpaper preview generator and GitHub README gallery builder.
Preserves 100% of original wallpapers, generates lightweight WebP thumbnails,
and renders an elegant, responsive GitHub showcase gallery organized by color shade and media.
"""

import os
import sys
import subprocess
import urllib.parse
from fractions import Fraction
from pathlib import Path

CATEGORY_CONFIG = {
    "dark": {
        "title": "Dark & Obsidian",
        "emoji": "🌑",
        "description": "Deep blacks, OLED-friendly dark tones, cyber-noir, and midnight aesthetics."
    },
    "blue": {
        "title": "Oceanic & Blue",
        "emoji": "🌊",
        "description": "Calming azure, arctic Nord hues, alpine lakes, twilight skies, and cyan neon."
    },
    "warm": {
        "title": "Warm & Amber",
        "emoji": "🔥",
        "description": "Fiery sunsets, autumn foliage, crimson anime scenes, and cozy amber glows."
    },
    "purple": {
        "title": "Purple & Neon",
        "emoji": "🔮",
        "description": "Synthwave purples, violet twilight vistas, and electric magenta accents."
    },
    "green": {
        "title": "Verdant & Green",
        "emoji": "🍃",
        "description": "Lush alpine meadows, mossy waterfalls, rolling hills, and pastoral serenity."
    },
    "light": {
        "title": "Light & Minimal",
        "emoji": "☀️",
        "description": "Clean high-key compositions, delicate watercolor, zen ink, and airy aesthetics."
    },
    "gifs": {
        "title": "Animated GIFs",
        "emoji": "👾",
        "description": "Nostalgic pixel art scenes, 16-bit animations, and relaxing lofi loops."
    },
    "videos": {
        "title": "Live Wallpapers",
        "emoji": "🎬",
        "description": "Ultra-HD MP4 live video wallpapers suitable for mpvpaper, swww, or awallpaper."
    }
}

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}

def format_size(size_bytes):
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.0f} KB"
    return f"{size_bytes} B"

def get_aspect_ratio(w, h):
    if not w or not h or h == 0:
        return "Unknown"
    ratio = w / h
    if abs(ratio - 16/9) < 0.03:
        return "16:9"
    elif abs(ratio - 16/10) < 0.03:
        return "16:10"
    elif abs(ratio - 21/9) < 0.05:
        return "21:9"
    elif abs(ratio - 32/9) < 0.05:
        return "32:9"
    elif abs(ratio - 4/3) < 0.03:
        return "4:3"
    elif abs(ratio - 1/1) < 0.03:
        return "1:1"
    elif ratio < 0.9:
        return "Portrait"
    else:
        f = Fraction(w, h).limit_denominator(12)
        return f"{f.numerator}:{f.denominator}"

def get_resolution_badge(w, h, ext):
    if ext == ".mp4":
        res_label = "Live Video"
    elif ext == ".gif":
        res_label = "Animated"
    else:
        res_label = ""

    if w and h:
        if w >= 7680 or h >= 4320:
            badge = "8K UHD"
        elif w >= 5120 or h >= 2880:
            badge = "5K"
        elif w >= 3840 or h >= 2160:
            badge = "4K UHD"
        elif w >= 2560 or h >= 1440:
            badge = "1440p"
        elif w >= 1920 or h >= 1080:
            badge = "1080p"
        else:
            badge = f"{w}x{h}"
    else:
        badge = "HD"

    if res_label:
        return f"{badge} • {res_label}"
    return badge

def clean_display_title(filename):
    stem = Path(filename).stem
    # Replace dashes and underscores with spaces
    title = stem.replace("_", " ").replace("-", " ")
    # Clean up multiple spaces
    title = " ".join(title.split())
    # Title-case each word
    title = title.title()
    if len(title) > 30:
        title = title[:28] + "…"
    return title

def extract_metadata_and_preview(repo_dir, category, filename):
    source_path = os.path.join(repo_dir, category, filename)
    ext = os.path.splitext(filename)[1].lower()
    size_bytes = os.path.getsize(source_path)
    
    preview_dir = os.path.join(repo_dir, "previews", category)
    os.makedirs(preview_dir, exist_ok=True)
    preview_filename = f"{filename}.webp"
    preview_path = os.path.join(preview_dir, preview_filename)
    
    w, h, fmt = None, None, ext[1:].upper()
    
    preview_exists = os.path.exists(preview_path)
    needs_gen = not preview_exists or os.path.getmtime(preview_path) < os.path.getmtime(source_path)

    if ext == ".mp4":
        try:
            cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
                   "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", source_path]
            out = subprocess.check_output(cmd).decode().strip()
            parts = out.split('x')
            w, h = int(parts[0]), int(parts[1])
        except Exception:
            w, h = 1920, 1080

        if needs_gen:
            cmd = ["ffmpeg", "-y", "-ss", "00:00:01", "-i", source_path,
                   "-vframes", "1", "-vf", "scale='min(640,iw)':-1",
                   "-q:v", "80", preview_path]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    else:
        try:
            cmd = ["identify", "-ping", "-format", "%w %h %m\n", f"{source_path}[0]"]
            out = subprocess.check_output(cmd).decode().strip()
            parts = out.split()
            w, h = int(parts[0]), int(parts[1])
            fmt = parts[2]
        except Exception:
            pass

        if needs_gen:
            cmd = ["magick", f"{source_path}[0]", "-resize", "640x360>",
                   "-quality", "82", preview_path]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    aspect = get_aspect_ratio(w, h)
    badge = get_resolution_badge(w, h, ext)
    
    return {
        "filename": filename,
        "category": category,
        "width": w,
        "height": h,
        "format": fmt,
        "aspect": aspect,
        "size_str": format_size(size_bytes),
        "size_bytes": size_bytes,
        "badge": badge,
        "title": clean_display_title(filename),
        "rel_source": f"{category}/{filename}",
        "rel_preview": f"previews/{category}/{preview_filename}"
    }

def generate_markdown(repo_dir, catalog):
    total_count = sum(len(items) for items in catalog.values())
    total_bytes = sum(sum(item["size_bytes"] for item in items) for items in catalog.values())
    
    lines = []
    lines.append("# 🖼️ Curated Desktop Wallpapers")
    lines.append("")
    lines.append("A curated collection of Ultra-HD (4K / 5K / 8K), animated pixel art, and live desktop wallpapers organized by color shade and media format.")
    lines.append("")
    lines.append(f"![Wallpapers](https://img.shields.io/badge/Wallpapers-{total_count}-blue?style=flat-square&logo=images)")
    lines.append(f"![Total Size](https://img.shields.io/badge/Total%20Size-{format_size(total_bytes).replace(' ', '%20')}-informational?style=flat-square)")
    lines.append("![Resolution](https://img.shields.io/badge/Resolution-1080p%20|%204K%20|%205K%20|%208K-blueviolet?style=flat-square)")
    lines.append("![License](https://img.shields.io/badge/License-MIT%20/%20Personal-green?style=flat-square)")
    lines.append("![Maintained](https://img.shields.io/badge/Maintained-Yes-success?style=flat-square)")
    lines.append("")
    lines.append("> [!TIP]")
    lines.append("> **Instant Full Quality**: Click any preview thumbnail below to view or download the uncompressed original wallpaper.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🧭 Quick Navigation")
    lines.append("")
    lines.append("| Category | Wallpapers | Color & Style Highlights |")
    lines.append("| :--- | :---: | :--- |")
    
    for cat_key, conf in CATEGORY_CONFIG.items():
        count = len(catalog.get(cat_key, []))
        link = f"#{conf['title'].lower().replace(' ', '-').replace('&', '').replace('--', '-')}"
        lines.append(f"| [{conf['emoji']} **{conf['title']}**]({link}) | `{count}` | {conf['description']} |")
    
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Sections per category
    for cat_key, conf in CATEGORY_CONFIG.items():
        items = catalog.get(cat_key, [])
        if not items:
            continue
            
        lines.append(f"## {conf['emoji']} {conf['title']}")
        lines.append(f"*{conf['description']}* &nbsp;•&nbsp; **`{len(items)} wallpapers`**")
        lines.append("")
        
        lines.append("| Preview | Preview | Preview |")
        lines.append("| :---: | :---: | :---: |")
        
        row = []
        for item in items:
            src_url = urllib.parse.quote(item['rel_source'])
            prev_url = urllib.parse.quote(item['rel_preview'])
            title = item['title']
            badge = item['badge']
            aspect = item['aspect']
            sz = item['size_str']
            
            cell = f"<a href=\"{src_url}\"><img src=\"{prev_url}\" width=\"240\" alt=\"{title}\" /></a><br /><sub>**{title}**<br />`{badge}` • `{aspect}` • `{sz}`</sub>"
            row.append(cell)
            
            if len(row) == 3:
                lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
                row = []
                
        if len(row) == 1:
            lines.append(f"| {row[0]} | | |")
        elif len(row) == 2:
            lines.append(f"| {row[0]} | {row[1]} | |")
            
        lines.append("")
        lines.append("<p align=\"right\"><a href=\"#🖼️-curated-desktop-wallpapers\">⬆️ Back to Top</a></p>")
        lines.append("")
        lines.append("---")
        lines.append("")
        
    # Download & Hyprland Setup Guide
    lines.append("## 🚀 Download & Setup Guide")
    lines.append("")
    lines.append("### 1. Clone the Collection")
    lines.append("```bash")
    lines.append("git clone git@github.com:Realdhiru/walpp.git ~/Pictures/Wallpapers")
    lines.append("```")
    lines.append("")
    lines.append("### 2. Download Specific Shades (Sparse Checkout)")
    lines.append("```bash")
    lines.append("git clone --filter=blob:none --sparse git@github.com:Realdhiru/walpp.git ~/Pictures/Wallpapers")
    lines.append("cd ~/Pictures/Wallpapers")
    lines.append("git sparse-checkout set dark blue   # only download dark and blue shades")
    lines.append("```")
    lines.append("")
    lines.append("### 3. Setting Wallpapers on Linux & Hyprland")
    lines.append("* **hyprpaper**:")
    lines.append("  ```ini")
    lines.append("  preload = ~/Pictures/Wallpapers/dark/pure-black-minimal.jpg")
    lines.append("  wallpaper = ,~/Pictures/Wallpapers/dark/pure-black-minimal.jpg")
    lines.append("  ```")
    lines.append("* **swww** (smooth transitions):")
    lines.append("  ```bash")
    lines.append("  swww img ~/Pictures/Wallpapers/blue/monterey-nord-dunes.png --transition-type wipe")
    lines.append("  ```")
    lines.append("* **mpvpaper** (for live MP4 wallpapers):")
    lines.append("  ```bash")
    lines.append("  mpvpaper '*' ~/Pictures/Wallpapers/videos/cracked-screen-cat.mp4 -o 'loop --no-audio'")
    lines.append("  ```")
    lines.append("* **feh**:")
    lines.append("  ```bash")
    lines.append("  feh --bg-fill ~/Pictures/Wallpapers/dark/nixos-snowflake-minimal.png")
    lines.append("  ```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🛠️ Automated Gallery Generator")
    lines.append("")
    lines.append("To regenerate WebP previews and update the README table when adding wallpapers:")
    lines.append("")
    lines.append("```bash")
    lines.append("./scripts/update-gallery.sh")
    lines.append("git add .")
    lines.append("git commit -m \"Add wallpapers\"")
    lines.append("git push")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📜 License & Credits")
    lines.append("- Wallpapers remain copyright of their respective digital artists, photographers, and studios.")
    lines.append("- The repository structure, automation scripts, and gallery templates are licensed under the [MIT License](LICENSE).")
    lines.append("")
    
    return "\n".join(lines)

def main():
    repo_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(f"📁 Scanning repository at: {repo_dir}")
    
    catalog = {}
    total_scanned = 0
    
    for cat_key in CATEGORY_CONFIG.keys():
        cat_dir = os.path.join(repo_dir, cat_key)
        if not os.path.isdir(cat_dir):
            continue
            
        files = sorted(os.listdir(cat_dir))
        catalog[cat_key] = []
        
        for f in files:
            if f.startswith("."):
                continue
            ext = os.path.splitext(f)[1].lower()
            if ext in VALID_EXTENSIONS:
                meta = extract_metadata_and_preview(repo_dir, cat_key, f)
                catalog[cat_key].append(meta)
                total_scanned += 1
                
        print(f"  • {cat_key}: {len(catalog[cat_key])} wallpapers processed")
        
    print(f"✨ Total wallpapers processed: {total_scanned}")
    
    # Generate README
    readme_content = generate_markdown(repo_dir, catalog)
    readme_path = os.path.join(repo_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    print(f"📝 Successfully updated README.md at: {readme_path}")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
scripts/generate_gallery.py
Automated wallpaper preview generator and GitHub README gallery builder.
Preserves original wallpapers, generates lightweight WebP thumbnails,
and renders a clean, minimal GitHub showcase gallery organized by color shade and media.
"""

import os
import sys
import shutil
import subprocess
import urllib.parse
from fractions import Fraction
from pathlib import Path

CATEGORY_CONFIG = {
    "nord": {"title": "Nord", "icon": "❄️", "desc": "Arctic frost, icy cyan gradients, frosty teal & polar minimalism"},
    "ocean": {"title": "Ocean", "icon": "🌊", "desc": "Deep sapphire, cobalt horizons, midnight navy & oceanic abyss"},
    "emerald": {"title": "Emerald", "icon": "🌿", "desc": "Verdant moss, enchanted forests, misty pines & calming sage"},
    "sakura": {"title": "Sakura", "icon": "🌸", "desc": "Pastel cherry blossoms, soft blush, romantic rose & floral twilights"},
    "sunset": {"title": "Sunset", "icon": "🌅", "desc": "Fiery crimson skies, golden hour ambers, scarlet horizons & twilight glow"},
    "synthwave": {"title": "Synthwave", "icon": "🔮", "desc": "Cyberpunk neon, electric violet, retrowave magenta & glowing cityscapes"},
    "gruvbox": {"title": "Gruvbox", "icon": "🍂", "desc": "Warm autumn earth, retro mustard, cozy sepia & vintage rust"},
    "dark": {"title": "Dark", "icon": "🌑", "desc": "True OLED blacks, cyber-noir, moody midnight & low-luminance minimalism"},
    "light": {"title": "Light", "icon": "☀️", "desc": "Zen watercolor, high-key parchment, clean airy whites & subtle brushwork"},
    "gifs": {"title": "GIFs", "icon": "✨", "desc": "Animated pixel art, aesthetic retro loops & 60fps micro-animations"},
    "videos": {"title": "Videos", "icon": "🎬", "desc": "Ultra-HD live wallpapers for mpvpaper and animated backends"},
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
        res_label = "Video"
    elif ext == ".gif":
        res_label = "GIF"
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
    title = stem.replace("_", " ").replace("-", " ")
    title = " ".join(title.split())
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
            im_cmd = "magick" if shutil.which("magick") else "convert"
            cmd = [im_cmd, f"{source_path}[0]", "-resize", "640x360>",
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
    total_walls = sum(len(catalog.get(k, [])) for k in CATEGORY_CONFIG)
    
    lines = []
    
    # Hero Title & Badges
    lines.append("<div align=\"center\">")
    lines.append("")
    lines.append("# 🌌 Wallpapers Showcase")
    lines.append("")
    lines.append("A curated collection of ultra-high-definition desktop wallpapers, animated pixel-art loops, and live video backdrops.")
    lines.append("")
    lines.append(f"![Wallpapers](https://img.shields.io/badge/Wallpapers-{total_walls}_Total-7aa2f7?style=for-the-badge&logo=unsplash&logoColor=white) "
                 f"![Quality](https://img.shields.io/badge/Quality-4K_%7C_5K_%7C_8K-bb9af7?style=for-the-badge&logo=4k) "
                 f"![Previews](https://img.shields.io/badge/Previews-WebP_Optimized-9ece6a?style=for-the-badge&logo=webp) "
                 f"![License](https://img.shields.io/badge/License-MIT-f7768e?style=for-the-badge)")
    lines.append("")
    lines.append("</div>")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Quick Navigation Bar
    lines.append("### 🧭 Category Directory")
    lines.append("")
    
    nav_cards = []
    for cat_key, conf in CATEGORY_CONFIG.items():
        count = len(catalog.get(cat_key, []))
        link = f"#{conf['title'].lower()}"
        icon = conf.get("icon", "📁")
        nav_cards.append(f"[`{icon} {conf['title']}`]({link}) <sup>**{count}**</sup>")
    
    lines.append(" &nbsp;•&nbsp; ".join(nav_cards))
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # Sections per category in requested order
    for cat_key, conf in CATEGORY_CONFIG.items():
        items = catalog.get(cat_key, [])
        if not items:
            continue
            
        icon = conf.get("icon", "🖼️")
        desc = conf.get("desc", "")
        lines.append(f"## {icon} {conf['title']}")
        if desc:
            lines.append(f"> *{desc}* &nbsp; • &nbsp; **{len(items)} wallpapers**")
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
            
            cell = (
                f"<a href=\"{src_url}\"><img src=\"{prev_url}\" width=\"240\" alt=\"{title}\" /></a>"
                f"<br /><sub>**{title}**<br />`{badge}` • `{aspect}` • `{sz}`</sub>"
            )
            row.append(cell)
            
            if len(row) == 3:
                lines.append(f"| {row[0]} | {row[1]} | {row[2]} |")
                row = []
                
        if len(row) == 1:
            lines.append(f"| {row[0]} | | |")
        elif len(row) == 2:
            lines.append(f"| {row[0]} | {row[1]} | |")
            
        lines.append("")
        lines.append(f"<div align=\"right\"><sub><a href=\"#-\">⬆ Back to Top</a></sub></div>")
        lines.append("")
        lines.append("---")
        lines.append("")
        
    # Setup Guide
    lines.append("## 🚀 Setup & Integration")
    lines.append("")
    lines.append("### 📦 Quick Clone")
    lines.append("```bash")
    lines.append("git clone git@github.com:Realdhiru/wallps.git ~/Pictures/Wallpapers")
    lines.append("```")
    lines.append("")
    lines.append("### ⚡ Sparse Checkout (Download Specific Categories)")
    lines.append("To save bandwidth and only fetch the categories you use:")
    lines.append("```bash")
    lines.append("git clone --filter=blob:none --sparse git@github.com:Realdhiru/wallps.git ~/Pictures/Wallpapers")
    lines.append("cd ~/Pictures/Wallpapers")
    lines.append("git sparse-checkout set nord ocean dark gruvbox sakura")
    lines.append("```")
    lines.append("")
    lines.append("### 🖥️ Setting Wallpapers on Hyprland & Linux")
    lines.append("* **`swww`** (Smooth transitions):")
    lines.append("  ```bash")
    lines.append("  swww img ~/Pictures/Wallpapers/blue/alone-night-sky-scenery.jpg --transition-type wipe")
    lines.append("  ```")
    lines.append("* **`hyprpaper`** (Static fast wallpaper engine):")
    lines.append("  ```ini")
    lines.append("  preload = ~/Pictures/Wallpapers/dark/pure-black-minimal.jpg")
    lines.append("  wallpaper = ,~/Pictures/Wallpapers/dark/pure-black-minimal.jpg")
    lines.append("  ```")
    lines.append("* **`mpvpaper`** (Animated live video backends):")
    lines.append("  ```bash")
    lines.append("  mpvpaper '*' ~/Pictures/Wallpapers/videos/cracked-screen-cat.mp4 -o 'loop --no-audio'")
    lines.append("  ```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 🛠️ Gallery Maintenance")
    lines.append("")
    lines.append("Regenerate lightweight WebP previews and update the gallery at any time:")
    lines.append("```bash")
    lines.append("./scripts/update-gallery.sh")
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 📜 License")
    lines.append("Wallpapers belong to their respective digital artists, photographers, and studios. Automation scripts and gallery templates are licensed under the [MIT License](LICENSE).")
    lines.append("")
    
    return "\n".join(lines)

def cleanup_orphaned_previews(repo_dir):
    previews_root = os.path.join(repo_dir, "previews")
    if not os.path.isdir(previews_root):
        return
    orphans_removed = 0
    for cat_key in CATEGORY_CONFIG.keys():
        cat_preview_dir = os.path.join(previews_root, cat_key)
        cat_src_dir = os.path.join(repo_dir, cat_key)
        if not os.path.isdir(cat_preview_dir):
            continue
        for pf in os.listdir(cat_preview_dir):
            if not pf.endswith(".webp"):
                continue
            orig_filename = pf[:-5]
            orig_path = os.path.join(cat_src_dir, orig_filename)
            if not os.path.isfile(orig_path):
                orphan_file = os.path.join(cat_preview_dir, pf)
                try:
                    os.remove(orphan_file)
                    orphans_removed += 1
                    print(f"Purged orphan preview: previews/{cat_key}/{pf}")
                except OSError:
                    pass
    if orphans_removed > 0:
        print(f"Purged {orphans_removed} orphaned preview(s).")

def main():
    repo_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(f"Scanning repository at: {repo_dir}")
    
    cleanup_orphaned_previews(repo_dir)
    
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
                source_path = os.path.join(cat_dir, f)
                if not os.path.isfile(source_path):
                    continue
                try:
                    meta = extract_metadata_and_preview(repo_dir, cat_key, f)
                    catalog[cat_key].append(meta)
                    total_scanned += 1
                except FileNotFoundError:
                    continue
                
        print(f"  • {cat_key}: {len(catalog[cat_key])} wallpapers processed")
        
    print(f"Total wallpapers processed: {total_scanned}")
    
    # Generate README
    readme_content = generate_markdown(repo_dir, catalog)
    readme_path = os.path.join(repo_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme_content)
        
    print(f"Successfully updated README.md at: {readme_path}")

if __name__ == "__main__":
    main()

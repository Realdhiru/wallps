# 📖 Complete Guide: How Your Wallpaper Repository Works

This document explains everything that was done to transform your wallpaper folder into an automated, beautifully organized GitHub repository, and how all the moving parts work together.

---

## 🎯 The Big Picture (Before vs. After)

### Before:
- **One messy folder**: 215 wallpapers dumped into the root directory with no structure.
- **Random file names**: Screenshots like `Screenshot 2025-10-30 201701.png`, hashes like `ddg_1786851485157838324.gif`, spaces, Chinese characters (`绿色房子.png`), and numbers like `42.gif`.
- **Corrupted files**: `peaks.png` and `blue_swirl.png` were broken/truncated.
- **Unstaged deletions**: 184 wallpapers you had deleted were lingering in Git status.
- **No gallery or preview**: Viewing 700+ MB of raw 4K/8K images and 100 MB video files directly on GitHub would cause massive lag and slow load times.

### After:
- **Clean Structure**: Wallpapers sorted by **color shade** (`dark`, `blue`, `warm`, `purple`, `green`, `light`) and media format (`gifs`, `videos`).
- **100% Clean Names**: Every file has a descriptive, lowercase `kebab-case` name (e.g. `dark/ascii-matrix-hacker-terminal.png`, `gifs/arch-linux-isometric-cubes.gif`).
- **0 Corrupt Files**: Repaired and verified with 100% integrity.
- **Lightweight Previews**: 216 optimized WebP thumbnails (~6.1 MB total) let GitHub load the gallery instantly while keeping original full-res files untouched.
- **Interactive README**: Badges, quick-jump category tables, resolution indicators (`[4K UHD]`, `[5K]`, `[Animated]`, etc.), and Hyprland config snippets.
- **100% Zero-Touch Automation**: A local background daemon (`wallpaper-watcher.service`) and GitHub Actions automatically handle renaming, sorting, thumbnail generation, and Git syncing whenever you add a new wallpaper.

---

## 🧱 What We Did & Key Decisions

### 1. Renaming Every Random File
We analyzed every random file and gave it an accurate, descriptive name:
| Old Name | New Location & Name | Reason |
| :--- | :--- | :--- |
| `ddg_1786851485157838324.gif` | `gifs/arch-linux-isometric-cubes.gif` | Visual shows isometric Arch Linux cubes |
| `ddg_1786851502437412201.gif` | `gifs/matrix-digital-rain-code.gif` | Green falling Matrix rain code |
| `ddg_1786027426502739852.png` | `dark/ascii-matrix-hacker-terminal.png` | ASCII hacker terminal on dark theme |
| `Screenshot 2025-10-30 201701.png`| `warm/elden-ring-malenia.png` | Elden Ring Malenia boss art |
| `绿色房子.png` | `green/green-house-countryside.png` | Replaced Chinese characters with English kebab-case |
| `live/11.mp4` | `videos/goth-anime-girl-monochrome.mp4` | MP4 video metadata identified content |

### 2. Color Shade Categorization (Static Wallpapers)
Instead of guessing ambiguous categories like "aesthetic" or "scifi", we analyzed each static image's pixel colors (Hue, Saturation, Value):
- **`dark/`** (48 images): Low brightness, pure OLED blacks, night scenes, minimal dark mode.
- **`blue/`** (58 images): Cyan, sky blue, ocean, Nord theme, alpine lakes.
- **`warm/`** (33 images): Sunset oranges, fiery reds, golden autumn, warm amber tones.
- **`purple/`** (8 images): Synthwave magenta, violet twilight, mystical skies.
- **`green/`** (10 images): Lush alpine meadows, mossy forests, countryside hills.
- **`light/`** (7 images): High brightness, watercolor, white sketches, zen calligraphy.

### 3. Media Separation
- **`gifs/`** (47 files): All animated pixel art and lofi loops kept together.
- **`videos/`** (5 files): All live MP4 wallpapers kept in `videos/` as regular Git files (Option A).

### 4. Zero Data Loss & File Integrity
- **Original Quality Preserved**: The original 4K, 5K, and 8K wallpapers were **never compressed, resized, or re-encoded**. They remain at 100% full quality.
- **Corrupt Files Fixed**: Restored `peaks.png` and `blue_swirl.png` from their intact backup snapshots (`.png~`).
- **Accepted Deleted Files**: We committed the removal of the 184 files you disliked so your Git history is clean.

---

## ⚙️ How the Automation Works (Under the Hood)

You now have **two automated engines** running so you never have to do manual work:

```
                  ┌──────────────────────────────────────────────┐
                  │ You download / save any wallpaper into       │
                  │ ~/Pictures/Wallpapers                        │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ Local Daemon: wallpaper-watcher.service      │
                  │ (uses inotifywait to detect file in < 1 sec) │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │ scripts/auto_organize.py                     │
                  │ 1. Cleans filename to kebab-case             │
                  │ 2. Detects format (GIF / MP4 / Image)        │
                  │ 3. Classifies color (dark, blue, warm, etc.) │
                  │ 4. Moves file to proper category folder      │
                  │ 5. Generates WebP thumbnail in previews/     │
                  │ 6. Updates README.md gallery table           │
                  │ 7. git add, commit, and push in background   │
                  │ 8. Sends desktop notification to your screen │
                  └──────────────────────────────────────────────┘
```

### The Tools Involved:
1. **`scripts/generate_gallery.py`**:
   Scans all 8 categories, calculates image dimensions, aspect ratios, and file sizes, creates lightweight WebP thumbnails in `previews/`, and builds the full `README.md` gallery table.
2. **`scripts/auto_organize.py`**:
   The brains of the ingestion. When given a file, it cleans the filename, measures the image's colors via ImageMagick, sorts it into the right folder, and calls `generate_gallery.py`.
3. **`scripts/wallpaper_watcher.sh`**:
   A continuous loop using Linux `inotifywait`. It watches `~/Pictures/Wallpapers/` and immediately calls `auto_organize.py` whenever a new media file finishes writing.
4. **`wallpaper-watcher.service`** (Systemd User Service):
   Runs `wallpaper_watcher.sh` automatically in the background as long as your user session is active. It starts on boot and restarts automatically if it ever crashes.
5. **`.github/workflows/update-gallery.yml`** (GitHub Actions):
   If you ever upload an image directly to the GitHub website or push from a phone, GitHub runs the preview generator in the cloud and commits the preview back automatically.

---

## 🚀 How to Use It Day-to-Day

### Adding New Wallpapers (Zero-Touch):
1. **Download any wallpaper** from your browser directly into `~/Pictures/Wallpapers/` (even with a messy name like `download (3).jpg`).
2. **That's it!**
   - The daemon automatically renames it (e.g. `wallpaper-alpine-sunset.jpg`).
   - It sorts it into the right folder (e.g. `warm/`).
   - It generates the preview thumbnail.
   - It updates `README.md`.
   - It pushes to GitHub.
   - You will see a desktop notification: *"🖼️ Wallpaper Added: Organized into warm/wallpaper-alpine-sunset.jpg"*.

### Checking the Watcher Status:
If you ever want to check if the background daemon is healthy:
```bash
systemctl --user status wallpaper-watcher.service
```

### Viewing Logs of What It Did:
```bash
journalctl --user -u wallpaper-watcher.service -f
```

---

## 🎨 Setting Wallpapers on Hyprland & Linux

In your Hyprland configuration or terminal, you can easily set any wallpaper from the clean paths:

- **hyprpaper**:
  ```ini
  preload = ~/Pictures/Wallpapers/dark/pure-black-minimal.jpg
  wallpaper = ,~/Pictures/Wallpapers/dark/pure-black-minimal.jpg
  ```
- **swww** (smooth transitions):
  ```bash
  swww img ~/Pictures/Wallpapers/blue/monterey-nord-dunes.png --transition-type wipe
  ```
- **mpvpaper** (for live MP4 videos):
  ```bash
  mpvpaper '*' ~/Pictures/Wallpapers/videos/cracked-screen-cat.mp4 -o 'loop --no-audio'
  ```
- **feh**:
  ```bash
  feh --bg-fill ~/Pictures/Wallpapers/warm/great-wave-off-kanagawa.jpg
  ```

# System Overview & Architecture

An automated, curated desktop wallpaper repository paired with a zero-touch ingestion pipeline, deterministic color-shade categorization, and high-performance WebP thumbnail generation.

---

## 1. Project Philosophy & Design Principles

1. **Uncompressed Asset Preservation**: Master wallpaper assets (4K, 5K, 8K, pixel art GIFs, and MP4 live wallpapers) are stored in their native formats without lossy compression or resolution downsampling.
2. **Instant Visual Browsing**: Rather than loading hundreds of megabytes of raw files when viewing the repository, lightweight WebP previews (capped at 640px width, ~25 KB average) are generated incrementally, keeping total thumbnail payload under 7 MB.
3. **Deterministic Color Sorting**: Static wallpapers are categorized based on algorithmic HSV color distribution rather than subjective genre tags.
4. **Strict Uniform Naming**: All assets adhere to lowercase `kebab-case.ext` conventions with no special characters, timestamps, camera hashes, or language-specific scripts.
5. **Zero-Touch Automation**: New wallpapers placed in the repository root are automatically ingested, classified, renamed, previewed, and committed to Git by background daemons or GitHub Actions CI.

---

## 2. Directory Structure

```text
walpp/
├── scripts/
│   ├── auto_organize.py            # Automated ingestion, classification & sync
│   ├── generate_gallery.py         # WebP preview generator & README table builder
│   ├── update-gallery.sh           # Manual one-command gallery refresh runner
│   ├── wallpaper_watcher.sh        # inotifywait event daemon
│   └── wallpaper-watcher.service   # Systemd user service unit definition
├── previews/                       # Generated WebP thumbnails (mirrors category structure)
├── nord/                           # Arctic frost, icy cyan, frosty teal, polar minimalism
├── ocean/                          # Deep sapphire, cobalt horizons, midnight navy, oceanic abyss
├── emerald/                        # Verdant moss, enchanted forests, misty pines, calming sage
├── sakura/                         # Pastel cherry blossoms, soft blush, romantic rose, floral twilights
├── sunset/                         # Fiery crimson skies, golden hour ambers, scarlet horizons
├── synthwave/                      # Cyberpunk neon, electric violet, retrowave magenta, glowing cityscapes
├── gruvbox/                        # Warm autumn earth, retro mustard, cozy sepia, vintage rust
├── dark/                           # Low-luminance, OLED black, cyber-noir, moody midnight minimalism
├── light/                          # High-key minimal compositions, zen watercolor, clean parchment
├── gifs/                           # Animated pixel art, aesthetic retro loops & 60fps micro-animations
├── videos/                         # Ultra-HD live MP4 wallpapers for video backends
├── LICENSE                         # MIT License
├── README.md                       # Visual showcase gallery and client setup guide
└── OVERVIEW.md                     # System architecture & maintenance documentation
```

---

## 3. Color Classification Pipeline

Static images are classified into curated aesthetic shade categories using raw 32×32 pixel HSV distribution:

- **Dark**: Low-luminance average Value < 0.20 or >65% OLED pitch black pixels.
- **Light**: High-luminance average Value > 0.78 with low saturation (< 0.22).
- **Sakura**: Soft pink and rose tones (Hue 315°–355° or 355°–18° with high lightness / moderate saturation).
- **Sunset**: Fiery crimson, scarlet, and golden amber (Hue 0°–45° with high saturation & value).
- **Gruvbox**: Warm earthy browns, retro mustard, cozy sepia, and autumn rust (Hue 18°–68° with earthy saturation).
- **Emerald**: Forest greens, mossy streams, misty pines, and sage (Hue 68°–165°).
- **Nord**: Polar frost, icy cyan, and arctic teal (Hue 165°–205°).
- **Ocean**: Deep sapphire, cobalt, twilight navy, and deep-sea blues (Hue 205°–260°).
- **Synthwave**: Cyberpunk neon, electric violet, and vivid magenta (Hue 260°–315° with high saturation).
- **Format Overrides**: Animated files (`.gif`) and video files (`.mp4`, `.mkv`, `.webm`, `.mov`) are automatically routed to `gifs/` and `videos/` respectively.

---

## 4. Automation & Ingestion Architecture

The repository supports dual-layer automation: local event-driven daemon execution and remote GitHub Actions CI.

```mermaid
flowchart TD
    A[New Wallpaper Dropped] --> B{Source}
    B -->|Local Desktop| C[inotifywait Daemon]
    B -->|GitHub Web / Push| D[GitHub Actions Runner]

    C --> E[scripts/auto_organize.py]
    E --> F[Sanitize to kebab-case]
    F --> G[Classify Format & Color]
    G --> H[Move to Target Folder]
    H --> I[Generate WebP Preview]
    I --> J[Rebuild README.md]
    J --> K[git commit & push]
    K --> L[Desktop Notification]

    D --> M[scripts/generate_gallery.py]
    M --> N[Generate Missing Previews]
    N --> O[Rebuild README.md]
    O --> P[Auto-commit to main]
```

### Automation Components

| Component | Responsibility |
| :--- | :--- |
| **`scripts/generate_gallery.py`** | Scans category directories, extracts dimensions and aspect ratios via ImageMagick/FFprobe, incrementally builds WebP thumbnails in `previews/`, and renders the markdown table in `README.md`. |
| **`scripts/auto_organize.py`** | Ingestion worker. Handles name sanitization, HSV color classification, file relocation, preview generation, and background Git synchronization. |
| **`scripts/wallpaper_watcher.sh`** | Lightweight bash daemon utilizing `inotifywait` to monitor repository directories for file close/move events. |
| **`wallpaper-watcher.service`** | Systemd user service ensuring continuous, headless background operation of the watcher daemon across user sessions. |
| **`update-gallery.yml`** | GitHub Actions workflow ensuring thumbnail parity and gallery updates when commits are pushed directly from remote clients. |

---

## 5. Maintenance & Operation

### Running the Local Watcher
The local watcher service runs as a systemd user unit:

```bash
# Check service health
systemctl --user status wallpaper-watcher.service

# View real-time ingestion logs
journalctl --user -u wallpaper-watcher.service -f

# Restart or stop daemon
systemctl --user restart wallpaper-watcher.service
systemctl --user stop wallpaper-watcher.service
```

### Manual Gallery Regeneration
If thumbnails or markdown tables need to be rebuilt manually:

```bash
./scripts/update-gallery.sh
```

---

## 6. Client Integration & Desktop Usage

Wallpapers can be queried and set dynamically by Linux window managers and display tools:

### Hyprland (`hyprpaper`)
```ini
preload = ~/Pictures/Wallpapers/dark/pure-black-minimal.jpg
wallpaper = ,~/Pictures/Wallpapers/dark/pure-black-minimal.jpg
```

### Smooth Transitions (`swww`)
```bash
swww img ~/Pictures/Wallpapers/blue/monterey-nord-dunes.png --transition-type wipe
```

### Live Video Wallpapers (`mpvpaper`)
```bash
mpvpaper '*' ~/Pictures/Wallpapers/videos/cracked-screen-cat.mp4 -o 'loop --no-audio'
```

### Sparse Checkout (Single Category Clone)
To download only specific categories without fetching the entire repository:

```bash
git clone --filter=blob:none --sparse git@github.com:Realdhiru/wallps.git ~/Pictures/Wallpapers
cd ~/Pictures/Wallpapers
git sparse-checkout set dark blue   # only checkout dark and blue folders
```

# Antigravity Persistent Rules & System Memory — Wallpapers (wallps)

## 1. Absolute Asset & Workflow Non-Negotiables

### A. Asset Preservation & Integrity
- **Zero Lossy Master Modifications**: Master wallpaper assets (`blue/`, `dark/`, `warm/`, `purple/`, `green/`, `light/`, `gifs/`, `videos/`) must NEVER be compressed, downscaled, or transcoded in place.
- **Preview Isolation**: Generated previews live exclusively in `previews/<category>/<filename>.webp` (640px max width).
- **Strict Naming Standard**: All filenames must strictly follow lowercase `kebab-case.<ext>` with no spaces, special characters, uppercase letters, camera hashes, or timestamps.

### B. Ingestion & Gallery Pipeline
- When assets are added, moved, or deleted, always execute the gallery builder:
  ```bash
  python3 scripts/generate_gallery.py
  ```
- Do not manually edit table rows in `README.md` — they are programmatically derived by `generate_gallery.py`.

---

## 2. Git & Review Policy

- **No Automatic Git Actions**: Never stage (`git add`), commit, or push automatically.
- Always leave changes unstaged in the working tree for the user to review, stage, commit, and push.

---

## 3. Token Efficiency & Communication Policy (High-Density / Caveman Mode)

- **Zero Conversational Filler**: No pleasantries, generic preambles, or conversational padding.
- **High Semantic Density**: Minimal tokens during reasoning and responses; pure technical signal.
- **Technical Rigor Preserved**: Exact file paths, markdown links, and diffs must remain 100% accurate.
- **Brief Final Summaries**: Ultra-compact bullet points designed for instant parsing.

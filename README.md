# Corne Layout Generator

Python CLI that renders labels from a Vial keymap JSON onto your Corne keyboard template image.

## What it does

- Reads `layers` from a Vial config JSON.
- Reads key rectangles from a layout JSON.
- Draws each selected layer label on each key at configurable positions:
  - `top-left`, `top`, `top-right`, `left`, `center`, `right`, `bottom-left`, `bottom`, `bottom-right`
- Supports 9 layers at once (one per position).
- Supports `solo: true` mode:
  - only the first configured layer is rendered,
  - forced to `center`,
  - uses that layer's own color and font size.

## Project structure

- `corne_layout_generator/` - package code
- `scripts/generate_layout.py` - script wrapper
- `config/layout.corne.json` - default Corne key rectangles (3x6+3)
- `config/layout.corne.853x309.json` - starter map for the attached `assets/layout.png`
- `config/render.example.json` - render config example
- `config/render.uploaded.json` - ready config for uploaded files in this workspace
- `inputs/vial.sample.json` - sample Vial-like input
- `assets/` - put your empty keyboard image here
- `output/` - generated images

## Setup

```bash
cd /Users/vdupelev/work/corne
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

## Configure

1. Put your empty keyboard image in `assets/` (for example `assets/corne-empty.jpg`).
2. Put your real Vial export JSON in `inputs/` (for example `inputs/vial.json` or `inputs/*.vil`).
3. Copy and edit config:

```bash
cp config/render.example.json config/render.local.json
```

Then edit these fields in `config/render.local.json`:
- `vial_config_path`
- `template_image_path`
- `layout_config_path`
- `output_dir`
- `layers`
- `solo`

## Run

```bash
corne-layout-gen --config config/render.local.json
```

or

```bash
python scripts/generate_layout.py --config config/render.local.json
```

Output image is written to `output_dir`.

## Config format

You can define layers as objects:

```json
"layers": [
  {"number": 0, "position": "center", "color": "#f8fafc", "font_size": 24},
  {"number": 1, "position": "top-left", "color": "#bae6fd", "font_size": 14}
]
```

You can also define layers as numbers, with optional per-layer styles in `layer_styles`:

```json
"layers": [0, 1, 2],
"layer_styles": {
  "0": {"position": "center", "color": "#f8fafc", "font_size": 24},
  "1": {"position": "top-left", "color": "#bae6fd", "font_size": 14}
}
```

`default_style` applies to all layers unless overridden.

## Run with uploaded files in this workspace

```bash
python scripts/generate_layout.py --config config/render.uploaded.json
```

This config points to:
- `inputs/25 v3.vil`
- `assets/layout.png`

## Git setup and push

### GitHub

```bash
git init
git add .
git commit -m "Initial Corne layout generator"
git branch -M main
git remote add origin git@github.com:<your-user>/<your-repo>.git
git push -u origin main
```

### GitLab

```bash
git init
git add .
git commit -m "Initial Corne layout generator"
git branch -M main
git remote add origin git@gitlab.com:<your-user>/<your-repo>.git
git push -u origin main
```

`.gitlab-ci.yml` is included and runs a compile + sample render pipeline.

## Notes

- `config/layout.corne.json` is a starter map. If key text placement is slightly off for your image, tweak `x/y/w/h` per key.
- Vial exports can vary; this tool supports both `layers` and `.vil`-style `layout` arrays, then flattens nested arrays and reads values by key index.

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

POSITION_ANCHORS: dict[str, tuple[float, float]] = {
    "top-left": (0.16, 0.18),
    "top": (0.50, 0.18),
    "top-right": (0.84, 0.18),
    "left": (0.16, 0.50),
    "center": (0.50, 0.50),
    "right": (0.84, 0.50),
    "bottom-left": (0.16, 0.82),
    "bottom": (0.50, 0.82),
    "bottom-right": (0.84, 0.82),
}

DEFAULT_POSITION_ORDER = [
    "center",
    "top-left",
    "top",
    "top-right",
    "left",
    "right",
    "bottom-left",
    "bottom",
    "bottom-right",
]


@dataclass(frozen=True)
class LayerStyle:
    number: int
    position: str
    color: str
    font_size: int
    font_path: str | None
    stroke_color: str
    stroke_width: int


@dataclass(frozen=True)
class KeyRect:
    index: int
    x: float
    y: float
    w: float
    h: float


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected object in JSON: {path}")
    return data


def _resolve_path(base_dir: Path, value: str | None) -> Path | None:
    if value is None:
        return None
    p = Path(value)
    if p.is_absolute():
        return p
    return (base_dir / p).resolve()


def _flatten_layer_items(items: Any) -> list[Any]:
    flattened: list[Any] = []

    def _walk(value: Any) -> None:
        if isinstance(value, list):
            for it in value:
                _walk(it)
        else:
            flattened.append(value)

    _walk(items)
    return flattened


def _normalize_vial_layers(vial_json: dict[str, Any]) -> list[list[Any]]:
    raw_layers = vial_json.get("layers")
    if not isinstance(raw_layers, list):
        # .vil exports usually store keycodes in `layout`.
        raw_layers = vial_json.get("layout")
    if not isinstance(raw_layers, list):
        raise ValueError("Vial config must contain an array field: layers or layout")

    layers: list[list[Any]] = []
    for raw in raw_layers:
        layers.append(_flatten_layer_items(raw))
    return layers


def _normalize_key_label(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, dict):
        if "label" in value:
            value = value["label"]
        elif "keycode" in value:
            value = value["keycode"]

    text = str(value).strip()
    if not text:
        return ""

    if text in {"KC_TRNS", "_______", "TRNS"}:
        return ""
    if text in {"XXXXXXX", "KC_NO", "NO"}:
        return ""

    if text.startswith("KC_"):
        text = text[3:]

    return text.replace("_", " ")


def _load_font(font_path: str | None, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    if font_path:
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            pass

    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    style: LayerStyle,
    max_width: float,
    max_height: float,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    start = max(8, style.font_size)
    for size in range(start, 7, -1):
        font = _load_font(style.font_path, size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        width = right - left
        height = bottom - top
        if width <= max_width and height <= max_height:
            return font

    return _load_font(style.font_path, 8)


def _draw_text_in_key(
    draw: ImageDraw.ImageDraw,
    rect: KeyRect,
    text: str,
    style: LayerStyle,
) -> None:
    if not text:
        return

    anchor = POSITION_ANCHORS[style.position]
    target_x = rect.x + rect.w * anchor[0]
    target_y = rect.y + rect.h * anchor[1]

    max_width = rect.w * (0.82 if style.position == "center" else 0.44)
    max_height = rect.h * (0.50 if style.position == "center" else 0.26)

    font = _fit_font(draw, text, style, max_width=max_width, max_height=max_height)

    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_w = right - left
    text_h = bottom - top

    draw.text(
        (target_x - (text_w / 2), target_y - (text_h / 2)),
        text,
        fill=style.color,
        font=font,
        stroke_width=style.stroke_width,
        stroke_fill=style.stroke_color,
    )


def _draw_key_rectangles(
    draw: ImageDraw.ImageDraw,
    key_rects: list[KeyRect],
    color: str,
    width: int,
) -> None:
    outline_width = max(1, width)
    for rect in key_rects:
        draw.rectangle(
            (rect.x, rect.y, rect.x + rect.w, rect.y + rect.h),
            outline=color,
            width=outline_width,
        )


def _parse_layers(config: dict[str, Any]) -> list[LayerStyle]:
    raw_layers = config.get("layers")
    if not isinstance(raw_layers, list) or not raw_layers:
        raise ValueError("render config must define a non-empty array: layers")

    defaults = config.get("default_style") or {}
    if not isinstance(defaults, dict):
        raise ValueError("default_style must be an object if present")

    light_palette = [
        "#F8FAFC",
        "#DBEAFE",
        "#DCFCE7",
        "#FEF3C7",
        "#FCE7F3",
        "#E0E7FF",
        "#CCFBF1",
        "#FDE68A",
        "#E9D5FF",
    ]

    styles_from_map = config.get("layer_styles") or {}
    if not isinstance(styles_from_map, dict):
        raise ValueError("layer_styles must be an object if present")

    raw_muted = config.get("mute_layers", [])
    if not isinstance(raw_muted, list):
        raise ValueError("mute_layers must be an array if present")
    muted_layer_numbers = {int(layer) for layer in raw_muted}

    parsed: list[LayerStyle] = []

    for i, entry in enumerate(raw_layers):
        if isinstance(entry, int):
            layer_number = entry
            entry_style = styles_from_map.get(str(layer_number), {})
            if not isinstance(entry_style, dict):
                raise ValueError(f"layer_styles['{layer_number}'] must be an object")
        elif isinstance(entry, dict):
            if "number" not in entry:
                raise ValueError("each layer object must include: number")
            layer_number = int(entry["number"])
            entry_style = dict(entry)
        else:
            raise ValueError("layers entries must be either integers or objects")

        style_obj = {**defaults, **entry_style}
        is_muted = bool(style_obj.get("mute", False)) or (layer_number in muted_layer_numbers)
        if is_muted:
            continue

        position = str(style_obj.get("position", "")).strip()
        if not position:
            if layer_number == 0:
                position = "center"
            else:
                fallback_idx = min(i, len(DEFAULT_POSITION_ORDER) - 1)
                position = DEFAULT_POSITION_ORDER[fallback_idx]

        if position not in POSITION_ANCHORS:
            allowed = ", ".join(POSITION_ANCHORS.keys())
            raise ValueError(
                f"Invalid position '{position}' for layer {layer_number}. Allowed: {allowed}"
            )

        color = str(style_obj.get("color", light_palette[i % len(light_palette)]))
        font_size = int(style_obj.get("font_size", 22 if position == "center" else 14))
        font_path = style_obj.get("font_path")
        stroke_color = str(style_obj.get("stroke_color", "#111827"))
        stroke_width = int(style_obj.get("stroke_width", 2))

        parsed.append(
            LayerStyle(
                number=layer_number,
                position=position,
                color=color,
                font_size=font_size,
                font_path=str(font_path) if font_path else None,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
            )
        )

    if not parsed:
        raise ValueError("No active layers to render. Check layers/mute settings.")

    return parsed


def _parse_layout(layout_json: dict[str, Any], image_w: int, image_h: int) -> list[KeyRect]:
    keys = layout_json.get("keys")
    if not isinstance(keys, list) or not keys:
        raise ValueError("layout config must contain non-empty array: keys")

    ref = layout_json.get("reference_image_size") or {}
    ref_w = float(ref.get("width", image_w))
    ref_h = float(ref.get("height", image_h))

    sx = image_w / ref_w
    sy = image_h / ref_h

    parsed: list[KeyRect] = []
    for key in keys:
        if not isinstance(key, dict):
            raise ValueError("Each key in layout config must be an object")
        parsed.append(
            KeyRect(
                index=int(key["index"]),
                x=float(key["x"]) * sx,
                y=float(key["y"]) * sy,
                w=float(key["w"]) * sx,
                h=float(key["h"]) * sy,
            )
        )

    return parsed


def _build_output_name(config: dict[str, Any], active_layers: list[LayerStyle], solo: bool) -> str:
    explicit = config.get("output_filename")
    if explicit:
        return str(explicit)

    layer_part = "_".join(str(l.number) for l in active_layers)
    mode = "solo" if solo else "stacked"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"corne_layout_{mode}_{layer_part}_{timestamp}.png"


def render_from_config(config_path: Path) -> Path:
    config_path = config_path.resolve()
    base_dir = config_path.parent

    config = _load_json(config_path)

    vial_path = _resolve_path(base_dir, config.get("vial_config_path"))
    template_path = _resolve_path(base_dir, config.get("template_image_path"))
    layout_path = _resolve_path(base_dir, config.get("layout_config_path"))
    output_dir = _resolve_path(base_dir, config.get("output_dir", "output"))

    if vial_path is None:
        raise ValueError("render config must define: vial_config_path")
    if template_path is None:
        raise ValueError("render config must define: template_image_path")
    if layout_path is None:
        raise ValueError("render config must define: layout_config_path")
    if output_dir is None:
        raise ValueError("render config must define: output_dir")

    active_layers = _parse_layers(config)
    solo = bool(config.get("solo", False))

    if solo:
        first = active_layers[0]
        active_layers = [
            LayerStyle(
                number=first.number,
                position="center",
                color=first.color,
                font_size=first.font_size,
                font_path=first.font_path,
                stroke_color=first.stroke_color,
                stroke_width=first.stroke_width,
            )
        ]
    elif len(active_layers) > 9:
        raise ValueError("At most 9 layers can be rendered at once (9 positions per key)")

    vial_json = _load_json(vial_path)
    layout_json = _load_json(layout_path)

    img = Image.open(template_path).convert("RGBA")
    image_scale = float(config.get("image_scale", 1.0))
    if image_scale <= 0:
        raise ValueError("image_scale must be greater than 0")
    if image_scale != 1.0:
        scaled_w = max(1, int(round(img.width * image_scale)))
        scaled_h = max(1, int(round(img.height * image_scale)))
        img = img.resize((scaled_w, scaled_h), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(img)

    key_rects = _parse_layout(layout_json, image_w=img.width, image_h=img.height)
    vial_layers = _normalize_vial_layers(vial_json)

    if bool(config.get("draw_key_rect", False)):
        key_rect_color = str(config.get("key_rect_color", "#ffffff"))
        key_rect_width = int(config.get("key_rect_width", 1))
        _draw_key_rectangles(draw, key_rects, color=key_rect_color, width=key_rect_width)

    for rect in key_rects:
        for layer in active_layers:
            if layer.number < 0 or layer.number >= len(vial_layers):
                continue
            keycodes = vial_layers[layer.number]
            if rect.index < 0 or rect.index >= len(keycodes):
                continue

            label = _normalize_key_label(keycodes[rect.index])
            _draw_text_in_key(draw, rect, label, layer)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_name = _build_output_name(config, active_layers, solo=solo)
    output_path = output_dir / output_name

    img.convert("RGB").save(output_path)
    return output_path.resolve()

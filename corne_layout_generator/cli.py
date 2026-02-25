from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .renderer import render_from_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corne-layout-gen",
        description="Render keyboard layers from Vial config onto a keyboard template image.",
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to render config JSON (includes layers, colors, paths).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        output_path = render_from_config(Path(args.config))
    except Exception as exc:  # noqa: BLE001
        print(f"[error] {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(f"Rendered image: {output_path}")


if __name__ == "__main__":
    main()

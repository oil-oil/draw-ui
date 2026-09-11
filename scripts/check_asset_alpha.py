#!/usr/bin/env python3
"""检查图片的实际透明度；不会抠图、修改图片或判断构图质量。"""
import argparse
import json
from pathlib import Path

from PIL import Image


def inspect_alpha(path):
    with Image.open(path) as im:
        native_alpha = "A" in im.getbands() or "transparency" in im.info
        histogram = im.convert("RGBA").getchannel("A").histogram()
        total = im.width * im.height
        transparent = histogram[0]
        partial = sum(histogram[1:255])
        opaque = histogram[255]
        return {
            "path": str(Path(path).resolve()),
            "mode": im.mode,
            "size": [im.width, im.height],
            "has_alpha_or_transparency_metadata": native_alpha,
            "transparent_pixels": transparent,
            "partial_alpha_pixels": partial,
            "opaque_pixels": opaque,
            "nonopaque_fraction": (transparent + partial) / total,
            "has_visible_content": partial + opaque > 0,
            "transparency_check_passed": native_alpha
            and transparent + partial > 0
            and partial + opaque > 0,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--require-transparency", action="store_true")
    args = parser.parse_args()
    result = inspect_alpha(args.image)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_transparency and not result["transparency_check_passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

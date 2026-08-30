"""tools/make_art.py — convert any source image to coverage-ramp ASCII art.

Usage:
    python tools/make_art.py <source> <dest.txt> [cols] [--aspect F] [--crop T,B] [--threshold N]

How it works:
- Alpha-aware: transparent pixels are background, regardless of color.
- Threshold: pixels brighter than N count as ink (for grayscale inputs).
  For RGBA inputs, the threshold applies to luminance.
- Aspect: terminal cell height / width. Pass 1.0 for a square shape
  (like a ring), 2.05 for a wide landscape.
- Crop: trim a fraction off the top and bottom (e.g. 0.10,0.90 to drop a
  title bar). Default 0,0 (no crop).

Output is plain characters — no ANSI, no color — so it renders identically
everywhere, including piped output.
"""

import sys
from pathlib import Path

from PIL import Image


def to_gray(img: Image.Image) -> Image.Image:
    if img.mode in ("RGBA", "LA"):
        bg = Image.new("RGB", img.size, (0, 0, 0))
        bg.paste(img, mask=img.split()[-1])
        return bg.convert("L")
    return img.convert("L")


def main() -> None:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    src, dst = Path(args[0]), Path(args[1])
    cols = 64
    aspect = 2.05
    crop_top, crop_bottom = 0.0, 1.0
    threshold = 90
    i = 2
    while i < len(args):
        a = args[i]
        if a == "--aspect":
            aspect = float(args[i + 1]); i += 2
        elif a == "--crop":
            crop_top, crop_bottom = float(args[i + 1]), float(args[i + 2]); i += 3
        elif a == "--threshold":
            threshold = int(args[i + 1]); i += 2
        else:
            cols = int(a); i += 1

    img = to_gray(Image.open(src))
    w, h = img.size
    art = img.crop((0, int(h * crop_top), w, int(h * crop_bottom)))
    aw, ah = art.size
    rows = max(1, round(ah / (aw / cols) / aspect))

    px = art.load()
    box_w = aw / cols
    box_h = ah / rows

    RAMP = [
        (0.04, " "), (0.10, "."), (0.18, ":"), (0.30, "="),
        (0.45, "+"), (0.60, "*"), (0.78, "#"), (1.01, "@"),
    ]

    lines = []
    for ry in range(rows):
        line_chars = []
        for cx in range(cols):
            x0, x1 = int(cx * box_w), int((cx + 1) * box_w)
            y0, y1 = int(ry * box_h), int((ry + 1) * box_h)
            ink = sum(1 for yy in range(y0, y1) for xx in range(x0, x1)
                      if px[xx, yy] > threshold)
            frac = ink / max(1, (x1 - x0) * (y1 - y0))
            line_chars.append(next(ch for edge, ch in RAMP if frac < edge))
        lines.append("".join(line_chars).rstrip())

    dst.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {dst} ({cols} cols x {rows} rows)")


if __name__ == "__main__":
    main()

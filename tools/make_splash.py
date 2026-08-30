"""tools/make_splash.py — regenerate assets/splash.txt from assets/pixil2.jpg.

Run with a Python that has Pillow (the system python has it via streamlit):
    python tools/make_splash.py [cols]

Why coverage, not brightness: the source is white character strokes on
black. Area-averaging a cell that contains ~2 characters says "25% ink"
EVERYWHERE — every cell renders as '.', and the landscape dissolves into
dots (this exact failure shipped in v1 of this script). Instead we:

1. Binarize the source (ink vs background) with a brightness threshold.
2. Sample ~1 terminal cell per source character (cols ~= source grid).
3. Map each cell's INK FRACTION to a ramp: 0 -> space, sparse -> '.',
   typical glyph -> ':*+', dense/bold -> '#%@'.

Aspect: terminal cells are ~2x taller than wide, so vertical sampling
compresses by the same factor to keep the landscape proportioned.

The output is plain characters — no ANSI — so it renders identically
everywhere, including piped output.

Art credit: the source landscape is by @littlebitspace; see README.
"""

import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).parent.parent
SRC = HERE / "assets" / "pixil2.jpg"
DST = HERE / "assets" / "splash.txt"

INK_THRESHOLD = 90          # pixel brightness above this counts as ink
CROP_TOP, CROP_BOTTOM = 0.28, 0.92   # trim the title band (top) and signature (bottom-right)
CELL_ASPECT = 2.05          # terminal cell height / width (typical 10x21px)

# ink-fraction bucket edges -> character. Sum of glyph strokes in a normal
# character cell is 10-35%; bold/dense regions go higher.
RAMP = [
    (0.04, " "),
    (0.10, "."),
    (0.18, ":"),
    (0.30, "="),
    (0.45, "+"),
    (0.60, "*"),
    (0.78, "#"),
    (1.01, "@"),
]


def main() -> None:
    cols = int(sys.argv[1]) if len(sys.argv) > 1 else 104
    img = Image.open(SRC).convert("L")
    w, h = img.size

    art = img.crop((0, int(h * CROP_TOP), w, int(h * CROP_BOTTOM)))
    aw, ah = art.size
    rows = max(1, round(ah / (aw / cols) / CELL_ASPECT))

    px = art.load()
    box_w = aw / cols
    box_h = ah / rows

    lines = []
    for ry in range(rows):
        line_chars = []
        for cx in range(cols):
            x0, x1 = int(cx * box_w), int((cx + 1) * box_w)
            y0, y1 = int(ry * box_h), int((ry + 1) * box_h)
            ink = sum(
                1
                for yy in range(y0, y1)
                for xx in range(x0, x1)
                if px[xx, yy] > INK_THRESHOLD
            )
            frac = ink / max(1, (x1 - x0) * (y1 - y0))
            line_chars.append(next(ch for edge, ch in RAMP if frac < edge))
        lines.append("".join(line_chars).rstrip())

    DST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {DST} ({cols} cols x {rows} rows)")


if __name__ == "__main__":
    main()

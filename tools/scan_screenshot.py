"""Read a screenshot taken under the `ident` skin and name every asset in it.

This is how the ~400 assets whose IDs reveal nothing about what they draw get
identified. `ident` paints each one a unique colour; this reverses that in
bulk, so a single screenshot names every asset visible in it rather than one
per question.

    python tools/build.py --profile ident
    python tools/install.py --skins-only
    # in game: pick "MithrilUI Dark (Ident)", screenshot the area in question
    python tools/scan_screenshot.py "path/to/ScreenShot_....jpg"

Narrow it down to one part of the screen:

    python tools/scan_screenshot.py shot.jpg --region 1700,0,560,400   # minimap
    python tools/scan_screenshot.py shot.jpg --bottom 240              # toolbar

LOTRO writes JPEGs, which shift colours slightly, so matching is nearest
neighbour with a tolerance and a minimum pixel count. Both are adjustable if a
small element is being missed.

Needs Pillow and numpy. Everything else in this repo runs on a bare Python.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def load_legend(explicit: str | None) -> list[tuple[tuple[int, int, int], str]]:
    if explicit:
        paths = [Path(explicit)]
    else:
        paths = list((REPO / "dist" / "skins").glob("*/debug-legend.txt"))
    if not paths:
        raise SystemExit(
            "No legend found. Build the identification skin first:\n"
            "  python tools/build.py --profile ident"
        )

    entries = []
    for path in paths:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line.startswith("#") or len(line) < 9:
                continue
            parts = line.split()
            if len(parts) < 2 or len(parts[0]) != 7:
                continue
            hex_code = parts[0][1:]
            try:
                rgb = (int(hex_code[0:2], 16), int(hex_code[2:4], 16), int(hex_code[4:6], 16))
            except ValueError:
                continue
            entries.append((rgb, " ".join(parts[1:])))
    if not entries:
        raise SystemExit(f"No usable entries in {', '.join(str(p) for p in paths)}")
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("screenshot", help="PNG or JPG taken with the ident skin active")
    parser.add_argument("--legend", help="path to a specific debug-legend.txt")
    parser.add_argument("--region", help="crop to x,y,width,height before scanning")
    parser.add_argument("--bottom", type=int, help="scan only the bottom N pixel rows")
    parser.add_argument("--tolerance", type=float, default=18.0,
                        help="max RGB distance to count as a match (default 18)")
    parser.add_argument("--min-pixels", type=int, default=40,
                        help="ignore matches smaller than this (default 40)")
    parser.add_argument("--top", type=int, default=40, help="how many results to print")
    args = parser.parse_args(argv)

    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        raise SystemExit(
            "This tool needs Pillow and numpy:\n  pip install pillow numpy"
        )

    path = Path(args.screenshot)
    if not path.exists():
        raise SystemExit(f"No such file: {path}")

    image = Image.open(path).convert("RGB")
    if args.region:
        x, y, w, h = (int(v) for v in args.region.split(","))
        image = image.crop((x, y, x + w, y + h))
        origin = (x, y)
    elif args.bottom:
        origin = (0, max(0, image.height - args.bottom))
        image = image.crop((0, origin[1], image.width, image.height))
    else:
        origin = (0, 0)

    pixels = np.asarray(image, dtype=np.int16)
    height, width = pixels.shape[:2]
    flat = pixels.reshape(-1, 3)

    # Collapse to distinct colours first; a screenshot has far fewer of them
    # than pixels, and this keeps the distance matrix small.
    packed = (flat[:, 0].astype(np.int32) << 16) | (flat[:, 1].astype(np.int32) << 8) | flat[:, 2]
    uniq, inverse, counts = np.unique(packed, return_inverse=True, return_counts=True)
    keep = counts >= max(4, args.min_pixels // 4)
    uniq_kept = uniq[keep]
    if uniq_kept.size == 0:
        print("Nothing above the pixel threshold. Try --min-pixels 4.")
        return 0

    uniq_rgb = np.stack([(uniq_kept >> 16) & 255, (uniq_kept >> 8) & 255, uniq_kept & 255], axis=1)

    entries = load_legend(args.legend)
    legend_rgb = np.array([e[0] for e in entries], dtype=np.int16)
    names = [e[1] for e in entries]

    # Nearest legend colour for each distinct screenshot colour.
    diff = uniq_rgb[:, None, :].astype(np.int32) - legend_rgb[None, :, :].astype(np.int32)
    dist = np.sqrt((diff ** 2).sum(axis=2))
    best = dist.argmin(axis=1)
    best_dist = dist[np.arange(dist.shape[0]), best]

    hits: dict[str, dict] = {}
    for index, colour_code in enumerate(uniq_kept):
        if best_dist[index] > args.tolerance:
            continue
        name = names[best[index]]
        mask = (packed == colour_code).reshape(height, width)
        ys, xs = np.nonzero(mask)
        record = hits.setdefault(name, {"pixels": 0, "x0": 1 << 30, "y0": 1 << 30, "x1": 0, "y1": 0,
                                        "dist": best_dist[index]})
        record["pixels"] += int(mask.sum())
        record["x0"] = min(record["x0"], int(xs.min()) + origin[0])
        record["y0"] = min(record["y0"], int(ys.min()) + origin[1])
        record["x1"] = max(record["x1"], int(xs.max()) + origin[0])
        record["y1"] = max(record["y1"], int(ys.max()) + origin[1])
        record["dist"] = min(record["dist"], float(best_dist[index]))

    hits = {k: v for k, v in hits.items() if v["pixels"] >= args.min_pixels}
    if not hits:
        print("No legend colours found in that area.")
        print("Either the ident skin was not active, or nothing there is skinnable.")
        print("Try a larger --tolerance or a smaller --min-pixels.")
        return 0

    ranked = sorted(hits.items(), key=lambda kv: -kv[1]["pixels"])[: args.top]
    print(f"{path.name}  scanned {width}x{height} at offset {origin}")
    print(f"{len(hits)} asset(s) identified\n")
    print(f"{'':2}{'pixels':>8}  {'x,y':>12}  {'w x h':>11}  {'d':>4}  asset")
    for name, r in ranked:
        w = r["x1"] - r["x0"] + 1
        h = r["y1"] - r["y0"] + 1
        # JPEG blends colours along every edge, inventing near-matches that are
        # small and imprecise. A real element is a large block at distance 0-2.
        solid = r["dist"] <= 2.5 and r["pixels"] >= 400
        mark = "* " if solid else "  "
        print(f"{mark}{r['pixels']:>8}  {r['x0']:>5},{r['y0']:<6}  "
              f"{w:>4} x {h:<4}  {r['dist']:>4.0f}  {name}")

    print("\n* = large block, exact colour match. Trust these.")
    print("  Unmarked rows are usually JPEG edge blending between two neighbours.")
    print("\nAdd any of these to the `exclude` list in skin/sweep.json to leave")
    print("them to the client, or give them their own rule.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

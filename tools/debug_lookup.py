"""Turn a colour picked out of a screenshot into the ArtAssetID that drew it.

Companion to the `ident` profile, which paints every asset the skin controls
in its own colour. Most ArtAssetIDs give no hint where they appear, so this is
the only reliable way to name the asset behind a piece of the interface.

    python tools/build.py --profile ident
    python tools/install.py --skins-only
    # pick "MithrilUI Ident" in game, screenshot the thing, read the pixel
    python tools/debug_lookup.py "#a1b2c3"
    python tools/debug_lookup.py 161 178 195

Screenshots are usually JPEG, so the colour will be slightly off. The lookup
is nearest-match and reports the distance, so a large distance means you
sampled an edge, a shadow, or something the skin does not control.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def parse_color(parts: list[str]) -> tuple[int, int, int]:
    if len(parts) == 3:
        return tuple(int(p) for p in parts)  # type: ignore[return-value]
    text = parts[0].strip().lstrip("#")
    if len(text) != 6:
        raise SystemExit(f"Cannot read colour {parts!r}. Use '#a1b2c3' or 'R G B'.")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def find_legends() -> list[Path]:
    found = list((REPO / "dist" / "skins").glob("*/debug-legend.txt"))
    if not found:
        raise SystemExit(
            "No legend found. Build the identification skin first:\n"
            "  python tools/build.py --profile ident"
        )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("color", nargs="+", help="'#a1b2c3' or three 0-255 values")
    parser.add_argument("--top", type=int, default=5, help="how many matches to show")
    parser.add_argument("--legend", help="path to a specific debug-legend.txt")
    args = parser.parse_args(argv)

    target = parse_color(args.color)
    legends = [Path(args.legend)] if args.legend else find_legends()

    entries: list[tuple[tuple[int, int, int], str]] = []
    for path in legends:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") is False and " " not in line:
                continue
            if not line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2 or len(parts[0]) != 7:
                continue
            try:
                entries.append((parse_color([parts[0]]), " ".join(parts[1:])))
            except (ValueError, SystemExit):
                continue

    if not entries:
        raise SystemExit(f"No usable entries in {', '.join(str(p) for p in legends)}")

    def distance(candidate: tuple[int, int, int]) -> float:
        return sum((candidate[i] - target[i]) ** 2 for i in range(3)) ** 0.5

    ranked = sorted(entries, key=lambda e: distance(e[0]))[: args.top]

    print(f"Sampled #{target[0]:02x}{target[1]:02x}{target[2]:02x}  "
          f"({len(entries)} assets in legend)\n")
    for color, asset_id in ranked:
        d = distance(color)
        marker = "  <-- exact" if d == 0 else ""
        print(f"  #{color[0]:02x}{color[1]:02x}{color[2]:02x}  d={d:6.1f}  {asset_id}{marker}")

    if distance(ranked[0][0]) > 40:
        print("\nNearest match is far off. That pixel is probably an edge, a shadow,")
        print("or something the client draws that no skin can reach.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

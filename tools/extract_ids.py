"""Mine PanelFile / Element / ArtAssetID names out of existing SkinDefinition files.

There is no complete published list of LOTRO panel and element IDs. The
practical way to find the one you need is to read skins that already touch it.
Point this at any skin folder -- yours, JRR's, anything in ui/skins -- and it
prints (or writes) the sorted ID inventory.

    python tools/extract_ids.py "C:/Users/me/Documents/The Lord of the Rings Online/ui/skins"
    python tools/extract_ids.py <path> --panel ID_UISkin_Toolbar
    python tools/extract_ids.py <path> --out docs/reference-element-ids.txt --kind element

IDs are factual names from the game client, not authored content -- this reads
structure, never art.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree


def iter_definitions(root: Path):
    if root.is_file():
        yield root
        return
    yield from sorted(root.rglob("SkinDefinition.xml"))


def extract(paths, panel_filter: str | None = None):
    panels: set[str] = set()
    elements: set[str] = set()
    art: set[str] = set()
    elements_by_panel: dict[str, set[str]] = defaultdict(set)
    unreadable: list[tuple[Path, str]] = []

    for path in paths:
        try:
            root = ElementTree.parse(path).getroot()
        except ElementTree.ParseError as exc:
            unreadable.append((path, str(exc)))
            continue

        for mapping in root.iter("Mapping"):
            if mapping.get("ArtAssetID"):
                art.add(mapping.get("ArtAssetID"))

        for panel in root.iter("PanelFile"):
            panel_id = panel.get("ID") or "(no ID)"
            panels.add(panel_id)
            if panel_filter and panel_id != panel_filter:
                continue
            for element in panel.iter("Element"):
                element_id = element.get("ID")
                if element_id:
                    elements.add(element_id)
                    elements_by_panel[panel_id].add(element_id)

    return panels, elements, art, elements_by_panel, unreadable


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("path", help="a skin folder, a tree of skin folders, or one XML file")
    parser.add_argument("--panel", help="only list elements belonging to this PanelFile ID")
    parser.add_argument("--kind", choices=["all", "panel", "element", "art", "tree"],
                        default="all", help="what to print (default: all)")
    parser.add_argument("--out", help="write the list to a file instead of stdout")
    args = parser.parse_args(argv)

    root = Path(args.path).expanduser()
    if not root.exists():
        raise SystemExit(f"Path does not exist: {root}")

    files = list(iter_definitions(root))
    if not files:
        raise SystemExit(f"No SkinDefinition.xml found under {root}")

    panels, elements, art, by_panel, unreadable = extract(files, args.panel)

    lines: list[str] = []
    if args.kind in ("all", "panel"):
        if args.kind == "all":
            lines.append(f"# PanelFile IDs ({len(panels)})")
        lines.extend(sorted(panels))
        if args.kind == "all":
            lines.append("")
    if args.kind in ("all", "element"):
        if args.kind == "all":
            lines.append(f"# Element IDs ({len(elements)})")
        lines.extend(sorted(elements))
        if args.kind == "all":
            lines.append("")
    if args.kind in ("all", "art"):
        if args.kind == "all":
            lines.append(f"# ArtAssetIDs ({len(art)})")
        lines.extend(sorted(art))
    if args.kind == "tree":
        for panel_id in sorted(by_panel):
            lines.append(panel_id)
            for element_id in sorted(by_panel[panel_id]):
                lines.append(f"    {element_id}")
            lines.append("")

    output = "\n".join(lines) + "\n"
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"Wrote {len(lines)} line(s) to {out_path}")
    else:
        print(output, end="")

    print(
        f"\nScanned {len(files)} file(s): "
        f"{len(panels)} panels, {len(elements)} elements, {len(art)} art assets",
        flush=True,
    )
    for path, error in unreadable:
        print(f"  could not parse {path}: {error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

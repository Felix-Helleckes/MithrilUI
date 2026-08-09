"""Check a built skin before the game does.

LOTRO's failure mode for a broken skin is silence: the skin simply does not
appear in the User Skins list, with no error anywhere. This script turns that
into an actual message.

    python tools/validate.py dist/skins/MithrilUI
    python tools/validate.py "C:/Users/me/Documents/The Lord of the Rings Online/ui/skins/SomeSkin"

It also works on skins you did not build here, which makes it a decent way to
debug someone else's SkinDefinition.xml.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from xml.etree import ElementTree

REQUIRED_ELEMENT_ATTRS = ("X", "Y", "Width", "Height")


class Report:
    def __init__(self, name: str):
        self.name = name
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def note(self, message: str) -> None:
        self.notes.append(message)

    def print_summary(self, show_notes: bool = True) -> None:
        status = "FAIL" if self.errors else ("warn" if self.warnings else "ok")
        print(f"  [{status:>4}] {self.name}")
        for message in self.errors:
            print(f"         ERROR   {message}")
        for message in self.warnings:
            print(f"         warning {message}")
        if show_notes:
            for message in self.notes:
                print(f"         note    {message}")


def read_tga_header(path: Path) -> dict | None:
    """Return the interesting header fields, or None if it is not a TGA."""
    try:
        with path.open("rb") as handle:
            header = handle.read(18)
    except OSError:
        return None
    if len(header) < 18:
        return None
    (
        _id_len, _cmap_type, data_type, _cmap_origin, _cmap_len, _cmap_depth,
        _x_origin, _y_origin, width, height, bpp, descriptor,
    ) = struct.unpack("<BBBHHBHHHHBB", header)
    if data_type not in (2, 10):  # uncompressed / RLE true-colour
        return None
    return {
        "data_type": data_type,
        "width": width,
        "height": height,
        "bpp": bpp,
        "descriptor": descriptor,
    }


def load_reference_ids(path: Path | None) -> set[str]:
    if not path or not Path(path).exists():
        return set()
    text = Path(path).read_text(encoding="utf-8-sig")
    return {line.strip() for line in text.splitlines() if line.strip()}


def load_expected_sizes(repo_root: Path) -> dict[str, tuple[int, int]]:
    manifest = repo_root / "skin" / "assets.json"
    if not manifest.exists():
        return {}
    with manifest.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {
        entry["id"]: tuple(entry["size"])
        for entry in data.get("assets", [])
        if "id" in entry
    }


def validate_skin(skin_dir: str | Path, reference_ids: str | Path | None = None) -> Report:
    skin_dir = Path(skin_dir)
    report = Report(skin_dir.name)

    definition = skin_dir / "SkinDefinition.xml"
    if not definition.exists():
        report.error(f"no SkinDefinition.xml in {skin_dir}")
        return report

    try:
        tree = ElementTree.parse(definition)
    except ElementTree.ParseError as exc:
        report.error(f"SkinDefinition.xml is not well-formed XML: {exc}")
        report.note("The game would silently drop this skin from the list.")
        return report

    root = tree.getroot()
    if root.tag != "opt":
        report.error(f"root element is <{root.tag}>, expected <opt>")

    skin_names = root.findall("SkinName")
    if len(skin_names) != 1:
        report.error(f"expected exactly one <SkinName>, found {len(skin_names)}")
    elif not (skin_names[0].get("Name") or "").strip():
        report.error("<SkinName> has no Name attribute")

    # -- art mappings ----------------------------------------------------

    repo_root = Path(__file__).resolve().parent.parent
    expected_sizes = load_expected_sizes(repo_root)

    seen_ids: dict[str, str] = {}
    referenced_files: set[Path] = set()

    for mapping in root.findall("Mapping"):
        asset_id = mapping.get("ArtAssetID")
        file_name = mapping.get("FileName")
        if not asset_id:
            report.error("a <Mapping> has no ArtAssetID")
            continue
        if not file_name:
            report.error(f"<Mapping ArtAssetID='{asset_id}'> has no FileName")
            continue

        if asset_id in seen_ids:
            report.error(
                f"ArtAssetID '{asset_id}' mapped twice "
                f"('{seen_ids[asset_id]}' and '{file_name}') -- the last one wins"
            )
        seen_ids[asset_id] = file_name

        resolved = skin_dir / Path(file_name.replace("\\", "/"))
        if not resolved.exists():
            report.error(f"'{asset_id}' points at missing file: {file_name}")
            continue
        referenced_files.add(resolved.resolve())

        header = read_tga_header(resolved)
        if header is None:
            report.warn(f"'{asset_id}' -> {file_name} is not a readable true-colour TGA")
            continue
        if header["bpp"] != 32:
            report.warn(f"'{asset_id}' is {header['bpp']}-bit; 32-bit (RGBA) is expected")
        if asset_id in expected_sizes:
            want = expected_sizes[asset_id]
            got = (header["width"], header["height"])
            if want != got:
                report.warn(
                    f"'{asset_id}' is {got[0]}x{got[1]}, the game expects {want[0]}x{want[1]}"
                )

    if not seen_ids:
        report.note("no art mappings -- this skin only changes layout")

    # -- panel layout ----------------------------------------------------

    known_ids = load_reference_ids(Path(reference_ids) if reference_ids else None)
    unknown: set[str] = set()
    element_count = 0

    for panel in root.findall("PanelFile"):
        panel_id = panel.get("ID")
        if not panel_id:
            report.error("a <PanelFile> has no ID")
            continue
        if not panel_id.startswith("ID_UISkin_"):
            report.warn(f"PanelFile ID '{panel_id}' does not look like an ID_UISkin_* name")

        for element in panel.iter("Element"):
            element_count += 1
            element_id = element.get("ID")
            if not element_id:
                report.error(f"an <Element> in {panel_id} has no ID")
                continue
            missing = [a for a in REQUIRED_ELEMENT_ATTRS if element.get(a) is None]
            if missing:
                report.error(
                    f"<Element ID='{element_id}'> is missing {', '.join(missing)} "
                    "-- the client needs all four"
                )
            for attr in REQUIRED_ELEMENT_ATTRS:
                value = element.get(attr)
                if value is not None and not value.lstrip("-").isdigit():
                    report.error(
                        f"<Element ID='{element_id}'> has non-numeric {attr}='{value}' "
                        "(an unresolved template expression?)"
                    )
            if known_ids and element_id not in known_ids:
                unknown.add(element_id)

    if unknown:
        report.warn(
            f"{len(unknown)} element ID(s) are not in the reference list: "
            + ", ".join(sorted(unknown)[:6])
            + ("..." if len(unknown) > 6 else "")
        )
        report.note(
            "The reference list is not exhaustive -- it was mined from one skin. "
            "An unknown ID is simply ignored by the client, never fatal."
        )

    if element_count:
        report.note(f"{element_count} layout element(s) across {len(root.findall('PanelFile'))} panel(s)")

    # -- unreferenced art ------------------------------------------------

    art_dir = skin_dir / "art"
    if art_dir.exists():
        orphans = [
            p for p in art_dir.rglob("*.tga") if p.resolve() not in referenced_files
        ]
        if orphans:
            report.warn(
                f"{len(orphans)} TGA file(s) in art/ are not referenced by any Mapping"
            )

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("paths", nargs="*", help="skin folder(s); defaults to dist/skins/*")
    parser.add_argument("--quiet", action="store_true", help="hide informational notes")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    reference = repo_root / "docs" / "reference-element-ids.txt"

    targets = [Path(p) for p in args.paths]
    if not targets:
        dist = repo_root / "dist" / "skins"
        targets = sorted(p for p in dist.glob("*") if p.is_dir()) if dist.exists() else []
        if not targets:
            print("Nothing to validate. Run: python tools/build.py")
            return 1

    print(f"Validating {len(targets)} skin(s)")
    failures = 0
    for target in targets:
        report = validate_skin(target, reference_ids=reference)
        report.print_summary(show_notes=not args.quiet)
        if report.errors:
            failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

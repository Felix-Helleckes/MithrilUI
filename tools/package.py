"""Build release archives in the shape lotrointerface.com expects.

The archive rules there are specific and easy to get wrong: upload a zip, give
it a descriptive name, and have exactly ONE root folder which is the folder the
user drops into place. An archive that contains `ui/skins/...` or two root
folders makes extra work for every person who installs it.

    python tools/package.py                      # everything, version from Util.lua
    python tools/package.py --version 0.2.0
    python tools/package.py --compendium-id 1234 # after the first upload

Produces, in dist/release/:

    MithrilUI-Skin-Dark-0.1.0.zip       -> root folder MithrilUI/
    MithrilUI-Skin-Ash-0.1.0.zip        -> root folder MithrilUI-Ash/
    MithrilUI-Plugins-0.1.0.zip         -> root folder MithrilUI/
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist" / "skins"
RELEASE = REPO / "dist" / "release"
VERSION_FILE = REPO / "VERSION"

AUTHOR = "Felix-Helleckes"
INFO_URL = "https://github.com/Felix-Helleckes/MithrilUI"


def detect_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def zip_folder(source: Path, archive: Path, root_name: str | None = None) -> int:
    """Zip `source` so it unpacks as a single root folder."""
    root_name = root_name or source.name
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()

    count = 0
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(source.rglob("*")):
            if path.is_dir():
                continue
            relative = path.relative_to(source)
            zf.write(path, Path(root_name) / relative)
            count += 1
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--version", help="override the version (default: from VERSION)")
    args = parser.parse_args(argv)

    version = args.version or detect_version()
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True)

    made: list[tuple[Path, int]] = []

    skins = sorted(p for p in DIST.glob("*") if p.is_dir()) if DIST.exists() else []
    if not skins:
        print("No built skins found. Run: python tools/build.py --all")
    for skin in skins:
        # The diagnostic skins are developer tools, not something to ship.
        if skin.name.endswith(("-Debug", "-Ident")):
            continue
        # MithrilUI-Ash-Declutter -> "Ash-Declutter"; plain MithrilUI -> "Dark"
        suffix = skin.name.replace("MithrilUI", "").strip("-") or "Dark"
        archive = RELEASE / f"MithrilUI-Skin-{suffix}-{version}.zip"
        count = zip_folder(skin, archive, root_name=skin.name)
        made.append((archive, count))

    print(f"\nRelease archives for v{version} in {RELEASE.relative_to(REPO)}:")
    for archive, count in made:
        size = archive.stat().st_size / 1024 / 1024
        print(f"  {archive.name:<44} {count:>4} files  {size:>6.1f} MB")

    print(
        "\nEach archive unpacks as one root folder, which is what lotrointerface.com"
        "\nasks for: drop it straight into"
        "\n  Documents\\The Lord of the Rings Online\\ui\\skins\\"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

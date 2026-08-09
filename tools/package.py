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
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

REPO = Path(__file__).resolve().parent.parent
DIST = REPO / "dist" / "skins"
RELEASE = REPO / "dist" / "release"
PLUGINS = REPO / "plugins" / "MithrilUI"

AUTHOR = "Felix-Helleckes"
INFO_URL = "https://github.com/Felix-Helleckes/MithrilUI"

# The .plugin manifests that make up the suite, in load order.
PLUGIN_MANIFESTS = ["MithrilUI.plugin", "Databar.plugin", "Vitals.plugin", "BuffBars.plugin"]


def detect_version() -> str:
    """Single source of truth is Util.VERSION, so a release cannot ship a
    version string that disagrees with what /mithril prints in game."""
    util = PLUGINS / "Core" / "Util.lua"
    match = re.search(r'Util\.VERSION\s*=\s*"([^"]+)"', util.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"Could not read Util.VERSION from {util}")
    return match.group(1)


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


def write_compendium(version: str, compendium_id: str | None, download_url: str | None) -> Path:
    """The Plugin Compendium installer reads this to find and update the suite.

    <Id> is assigned by lotrointerface.com when the package is first uploaded,
    so it stays a placeholder until you have it.
    """
    descriptors = "\n".join(
        f"    <descriptor>MithrilUI\\{name}</descriptor>" for name in PLUGIN_MANIFESTS
    )
    content = f"""<?xml version="1.0" encoding="utf-8"?>
<PluginConfig>
  <Id>{compendium_id or "0"}</Id>
  <Name>MithrilUI</Name>
  <Version>{version}</Version>
  <Author>{AUTHOR}</Author>
  <InfoUrl>{INFO_URL}</InfoUrl>
  <DownloadUrl>{download_url or INFO_URL + "/releases/latest"}</DownloadUrl>
  <Descriptors>
{descriptors}
  </Descriptors>
  <Dependencies />
  <StartupScript></StartupScript>
</PluginConfig>
"""
    target = PLUGINS / "MithrilUI.plugincompendium"
    target.write_text(content, encoding="utf-8")
    return target


def skin_readme(skin_dir: Path) -> str:
    existing = skin_dir / "README.txt"
    return existing.read_text(encoding="utf-8") if existing.exists() else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--version", help="override the version (default: from Core/Util.lua)")
    parser.add_argument("--compendium-id",
                        help="lotrointerface file id, assigned after the first upload")
    parser.add_argument("--download-url", help="direct download URL for the Plugin Compendium")
    parser.add_argument("--skins-only", action="store_true")
    parser.add_argument("--plugins-only", action="store_true")
    args = parser.parse_args(argv)

    version = args.version or detect_version()
    if RELEASE.exists():
        shutil.rmtree(RELEASE)
    RELEASE.mkdir(parents=True)

    made: list[tuple[Path, int]] = []

    if not args.plugins_only:
        skins = sorted(p for p in DIST.glob("*") if p.is_dir()) if DIST.exists() else []
        if not skins:
            print("No built skins found. Run: python tools/build.py --all")
        for skin in skins:
            # MithrilUI-Ash-Declutter -> "Ash-Declutter"; plain MithrilUI -> "Dark"
            suffix = skin.name.replace("MithrilUI", "").strip("-") or "Dark"
            archive = RELEASE / f"MithrilUI-Skin-{suffix}-{version}.zip"
            count = zip_folder(skin, archive, root_name=skin.name)
            made.append((archive, count))

    if not args.skins_only:
        compendium = write_compendium(version, args.compendium_id, args.download_url)
        print(f"wrote {compendium.relative_to(REPO)}"
              + ("" if args.compendium_id else "  (Id is a placeholder until first upload)"))

        archive = RELEASE / f"MithrilUI-Plugins-{version}.zip"
        count = zip_folder(PLUGINS, archive, root_name="MithrilUI")
        made.append((archive, count))

    print(f"\nRelease archives for v{version} in {RELEASE.relative_to(REPO)}:")
    for archive, count in made:
        size = archive.stat().st_size / 1024 / 1024
        print(f"  {archive.name:<44} {count:>4} files  {size:>6.1f} MB")

    print(
        "\nEach archive unpacks as one root folder, which is what lotrointerface.com asks for:"
        "\n  skins   -> Documents\\The Lord of the Rings Online\\ui\\skins\\"
        "\n  plugins -> Documents\\The Lord of the Rings Online\\Plugins\\"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

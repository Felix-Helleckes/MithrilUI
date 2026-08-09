"""Copy built skins and the plugin suite into LOTRO's user folder.

    python tools/install.py                 # install everything that was built
    python tools/install.py --dry-run       # show what would happen
    python tools/install.py --link          # symlink instead of copy (dev loop)
    python tools/install.py --uninstall
    python tools/install.py --game-dir "D:/LOTRO Docs"

LOTRO reads user content from:

    <Documents>/The Lord of the Rings Online/ui/skins/<SkinFolder>/
    <Documents>/The Lord of the Rings Online/Plugins/<Author>/

Skins are read once at client startup. Plugins can be reloaded live with
/plugins reload.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GAME_FOLDER = "The Lord of the Rings Online"


def documents_dir() -> Path:
    """Resolve the real Documents folder, which is not always ~/Documents --
    OneDrive redirection moves it, and localized Windows only renames the
    display name, not the path."""
    if sys.platform == "win32":
        try:
            import ctypes
            import ctypes.wintypes

            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            # CSIDL_PERSONAL = 5, SHGFP_TYPE_CURRENT = 0
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0:
                return Path(buf.value)
        except Exception:
            pass
    return Path.home() / "Documents"


def find_game_dir(override: str | None = None) -> Path:
    if override:
        path = Path(override).expanduser()
        if not path.exists():
            raise SystemExit(f"--game-dir does not exist: {path}")
        return path

    candidates = [
        documents_dir() / GAME_FOLDER,
        Path.home() / "Documents" / GAME_FOLDER,
        Path.home() / "OneDrive" / "Documents" / GAME_FOLDER,
        Path.home() / "OneDrive" / "Dokumente" / GAME_FOLDER,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise SystemExit(
        "Could not find your LOTRO user folder. Looked in:\n  "
        + "\n  ".join(str(c) for c in candidates)
        + "\n\nStart the game once so it creates the folder, or pass --game-dir."
    )


def remove_tree(target: Path, attempts: int = 4) -> None:
    """Delete a folder even when OneDrive is being difficult.

    Documents is routinely redirected into OneDrive, which marks synced files
    read-only and briefly holds handles while it uploads. A plain rmtree hits
    PermissionError on both. So: clear the read-only bit on failure, and retry
    a couple of times to let a sync operation finish.
    """
    def clear_readonly(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    for attempt in range(attempts):
        try:
            if sys.version_info >= (3, 12):
                shutil.rmtree(target, onexc=clear_readonly)
            else:
                shutil.rmtree(target, onerror=clear_readonly)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise SystemExit(
                    f"Could not replace {target}.\n"
                    "Something is holding those files open. Close the LOTRO client "
                    "(and the LOTRO launcher), pause OneDrive sync if it is running, "
                    "then try again."
                )
            time.sleep(0.6 * (attempt + 1))


def place(source: Path, target: Path, link: bool, dry_run: bool) -> str:
    """Copy or link `source` onto `target`, replacing whatever is there."""
    action = "link" if link else "copy"
    if dry_run:
        return f"would {action} {source.name} -> {target}"

    if target.is_symlink() or (target.exists() and target.is_dir() and os.path.islink(target)):
        target.unlink()
    elif target.exists():
        remove_tree(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    if link:
        try:
            target.symlink_to(source.resolve(), target_is_directory=True)
        except OSError as exc:
            raise SystemExit(
                f"Could not create a symlink ({exc}).\n"
                "On Windows this needs Developer Mode enabled or an elevated shell. "
                "Drop --link to copy instead."
            ) from exc
    else:
        shutil.copytree(source, target)
    return f"{'linked' if link else 'copied'} {source.name} -> {target}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--game-dir", help="LOTRO user folder, if auto-detection fails")
    parser.add_argument("--link", action="store_true",
                        help="symlink the repo instead of copying (edit-and-reload workflow)")
    parser.add_argument("--dry-run", action="store_true", help="print actions without doing them")
    parser.add_argument("--uninstall", action="store_true", help="remove MithrilUI skins and plugins")
    parser.add_argument("--skins-only", action="store_true")
    parser.add_argument("--plugins-only", action="store_true")
    args = parser.parse_args(argv)

    game_dir = find_game_dir(args.game_dir)
    skins_dir = game_dir / "ui" / "skins"
    plugins_dir = game_dir / "Plugins"
    print(f"LOTRO folder: {game_dir}")

    do_skins = not args.plugins_only
    do_plugins = not args.skins_only

    if args.uninstall:
        removed = 0
        if do_skins and skins_dir.exists():
            for path in skins_dir.glob("MithrilUI*"):
                print(f"  removing {path}")
                if not args.dry_run:
                    path.unlink() if path.is_symlink() else remove_tree(path)
                removed += 1
        if do_plugins:
            target = plugins_dir / "MithrilUI"
            if target.exists() or target.is_symlink():
                print(f"  removing {target}")
                if not args.dry_run:
                    target.unlink() if target.is_symlink() else remove_tree(target)
                removed += 1
        print(f"Removed {removed} item(s)."
              + (" (dry run -- nothing changed)" if args.dry_run else ""))
        return 0

    actions = 0

    if do_skins:
        built = REPO / "dist" / "skins"
        skins = sorted(p for p in built.glob("*") if p.is_dir()) if built.exists() else []
        if not skins:
            print("No built skins found. Run: python tools/build.py")
        for skin in skins:
            print("  " + place(skin, skins_dir / skin.name, args.link, args.dry_run))
            actions += 1

    if do_plugins:
        source = REPO / "plugins" / "MithrilUI"
        if source.exists():
            print("  " + place(source, plugins_dir / "MithrilUI", args.link, args.dry_run))
            actions += 1
        else:
            print(f"No plugin folder at {source}")

    if args.dry_run:
        print(f"\nDry run: {actions} action(s) planned, nothing written.")
        return 0

    print(f"\nInstalled {actions} item(s).")
    if do_skins:
        print("Skins:   restart the client, then "
              "Options (Ctrl+O) -> UI Settings -> Misc -> Current User Skin.")
    if do_plugins:
        print("Plugins: in game, /plugins refresh   then   /plugins load MithrilUI")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Lint the plugin folder the way the game's loader sees it.

The most common way a LOTRO plugin fails is boring: the <Package> path in the
.plugin manifest does not match the folder layout, or an `import` names a module
that is not there. The client's response is a one-line Lua error at load time
and nothing else. This checks both before you ever alt-tab.

    python tools/check_plugins.py

Also does a light structural pass over the Lua (balanced block keywords,
balanced brackets) which catches the typo class that stops a file from parsing.
It is not a Lua parser and does not pretend to be one.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

REPO = Path(__file__).resolve().parent.parent
PLUGINS = REPO / "plugins"

IMPORT_RE = re.compile(r'^\s*import\s+"([^"]+)"\s*;?', re.MULTILINE)
# Blocks that must be closed by `end`. `elseif` is deliberately absent: it
# reuses its `if`, and \b keeps it from matching as one anyway.
BLOCK_OPEN = re.compile(r"\b(function|if|for|while)\b")
BLOCK_CLOSE = re.compile(r"\bend\b")
# The `do` in `for ... do` / `while ... do` belongs to the loop keyword and
# must not be counted a second time. Only a standalone `do` opens its own block.
LOOP_DO = re.compile(r"\b(for|while)\b[^\n]*?\bdo\b")
STANDALONE_DO = re.compile(r"\bdo\b")
LONG_COMMENT = re.compile(r"--\[\[.*?\]\]", re.DOTALL)
LINE_COMMENT = re.compile(r"--[^\n]*")
STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'')


class Issues:
    def __init__(self):
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def lua_compiler():
    """Return a real Lua compile function if one is installed, else None.

    LOTRO runs Lua 5.1, so prefer a 5.1-compatible runtime. This turns the
    keyword heuristic below into a belt-and-braces second opinion instead of
    the only line of defence. Optional on purpose: the repo must stay buildable
    with a bare Python install.
    """
    try:
        import lupa  # noqa: PLC0415
    except ImportError:
        return None, None

    for attribute in ("lua51", "luajit21", "lua54"):
        runtime_module = getattr(lupa, attribute, None)
        if runtime_module is None:
            continue
        try:
            runtime = runtime_module.LuaRuntime()
            return runtime.compile, attribute
        except Exception:
            continue
    try:
        return lupa.LuaRuntime().compile, "default"
    except Exception:
        return None, None


def strip_lua(source: str) -> str:
    """Remove comments and string bodies so keyword counting is meaningful."""
    source = LONG_COMMENT.sub(" ", source)
    source = STRING_LITERAL.sub('""', source)
    source = LINE_COMMENT.sub(" ", source)
    return source


def package_to_path(package: str, author_dir: Path) -> Path:
    """MithrilUI.Databar.Main -> plugins/MithrilUI/Databar/Main.lua

    The first segment is the author folder, which is the directory itself."""
    parts = package.split(".")
    if parts and parts[0] == author_dir.name:
        parts = parts[1:]
    return author_dir.joinpath(*parts).with_suffix(".lua")


def check_manifest(path: Path, author_dir: Path, issues: Issues) -> str | None:
    try:
        root = ElementTree.parse(path).getroot()
    except ElementTree.ParseError as exc:
        issues.error(f"{path.name}: not well-formed XML: {exc}")
        return None

    info = root.find("Information")
    name = info.findtext("Name") if info is not None else None
    if not name:
        issues.error(f"{path.name}: <Information><Name> is missing")

    package = root.findtext("Package")
    if not package:
        issues.error(f"{path.name}: <Package> is missing")
        return name

    target = package_to_path(package, author_dir)
    if not target.exists():
        issues.error(
            f"{path.name}: <Package>{package}</Package> points at "
            f"{target.relative_to(REPO)}, which does not exist"
        )
    return name


def check_lua(path: Path, known_modules: set[str], issues: Issues, compile_lua=None) -> None:
    source = path.read_text(encoding="utf-8")
    rel = path.relative_to(REPO)

    if compile_lua is not None:
        try:
            compile_lua(source)
        except Exception as exc:
            issues.error(f"{rel}: Lua syntax error: {exc}")
            return  # nothing below will be meaningful on a file that won't parse

    for module in IMPORT_RE.findall(source):
        if module.startswith("Turbine"):
            continue
        if module not in known_modules:
            issues.error(f"{rel}: imports '{module}', which no file provides")

    stripped = strip_lua(source)

    # Drop each loop's own `do` before counting, so `for x do ... end` is one
    # block and not two.
    without_loop_do = LOOP_DO.sub(lambda m: m.group(1), stripped)
    opens = len(BLOCK_OPEN.findall(without_loop_do)) + len(
        STANDALONE_DO.findall(without_loop_do)
    )
    closes = len(BLOCK_CLOSE.findall(without_loop_do))
    if opens != closes:
        issues.warn(
            f"{rel}: {opens} block opener(s) vs {closes} 'end' "
            "(heuristic, check manually if the plugin fails to load)"
        )

    for opener, closer, label in (("(", ")", "parentheses"), ("{", "}", "braces"),
                                  ("[", "]", "brackets")):
        if stripped.count(opener) != stripped.count(closer):
            issues.error(
                f"{rel}: unbalanced {label} "
                f"({stripped.count(opener)} vs {stripped.count(closer)})"
            )

    if "Plugins[" in source and ".Unload" not in source:
        issues.warn(f"{rel}: touches Plugins[...] but defines no Unload handler")


def module_name_for(path: Path, author_dir: Path) -> str:
    rel = path.relative_to(author_dir).with_suffix("")
    return ".".join([author_dir.name, *rel.parts])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("path", nargs="?", default=str(PLUGINS),
                        help="plugins folder (default: plugins/)")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        raise SystemExit(f"No such folder: {root}")

    author_dirs = [p for p in root.iterdir() if p.is_dir()]
    if not author_dirs:
        raise SystemExit(f"No author folders under {root}")

    issues = Issues()
    total_manifests = 0
    total_lua = 0
    compile_lua, runtime_name = lua_compiler()

    for author_dir in author_dirs:
        lua_files = sorted(author_dir.rglob("*.lua"))
        known = {module_name_for(p, author_dir) for p in lua_files}

        manifests = sorted(author_dir.glob("*.plugin"))
        if not manifests:
            issues.warn(f"{author_dir.name}/: no .plugin manifest, nothing to load")
        for manifest in manifests:
            total_manifests += 1
            check_manifest(manifest, author_dir, issues)

        for lua_file in lua_files:
            total_lua += 1
            check_lua(lua_file, known, issues, compile_lua)

    parser_note = (
        f"compiled with lupa/{runtime_name}"
        if compile_lua is not None
        else "no Lua runtime found (pip install lupa for real syntax checks)"
    )
    print(f"Checked {total_manifests} manifest(s) and {total_lua} Lua file(s) -- {parser_note}")
    for message in issues.errors:
        print(f"  ERROR   {message}")
    for message in issues.warnings:
        print(f"  warning {message}")

    if issues.errors:
        print(f"\n{len(issues.errors)} error(s).")
        return 1
    print("OK" + (f" ({len(issues.warnings)} warning(s))" if issues.warnings else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

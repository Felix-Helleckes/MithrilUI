"""Emit the shared palette as Lua so the plugins and the skin never drift apart.

The whole point of a UI suite is that everything looks like one thing. The skin
gets its colours from themes/<id>.json; this writes the same numbers into
plugins/MithrilUI/Core/ThemeColors.lua, which the Lua side reads.

Run indirectly via tools/build.py, or directly:

    python tools/gen_lua.py --theme mithril-ash
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from theme import Theme, discover

REPO = Path(__file__).resolve().parent.parent
TARGET = REPO / "plugins" / "MithrilUI" / "Core" / "ThemeColors.lua"

# Roles the Lua side expects. Keeping the list explicit means a theme that
# forgets one fails at build time instead of at runtime in someone's client.
ROLES = [
    "panel", "panelAlt", "header", "border", "borderBright",
    "accent", "accentDim", "text", "textDim",
    "button", "buttonHover", "buttonDown",
    "good", "bad", "shadow",
]

ALPHA_ROLES = {
    "panel": "panel",
    "panelAlt": "panel",
    "header": "header",
    "button": "button",
}


def lua_color(theme: Theme, role: str) -> str:
    opacity_role = ALPHA_ROLES.get(role)
    r, g, b, a = theme.color(role, opacity=opacity_role)
    return (
        f"{{ a = {a / 255:.3f}, r = {r / 255:.3f}, "
        f"g = {g / 255:.3f}, b = {b / 255:.3f} }}"
    )


def generate(theme: Theme, target: Path = TARGET) -> Path:
    lines = [
        "-- GENERATED FILE - do not edit by hand.",
        f"-- Source: themes/{theme.id}.json",
        "-- Rebuild with: python tools/build.py",
        "--",
        "-- Values are 0..1 components ready for Turbine.UI.Color(a, r, g, b).",
        "",
        'import "Turbine";',
        'import "Turbine.UI";',
        "",
        "-- LOTRO plugins share one global table per apartment, so modules",
        "-- publish themselves into a namespace rather than returning a value.",
        "MithrilUI = MithrilUI or {};",
        "MithrilUI.Core = MithrilUI.Core or {};",
        "",
        "local ThemeColors = {};",
        "",
        f'ThemeColors.id = "{theme.id}";',
        f'ThemeColors.name = "{theme.name}";',
        "",
        "ThemeColors.raw = {",
    ]
    for role in ROLES:
        lines.append(f"    {role} = {lua_color(theme, role)},")
    lines += [
        "};",
        "",
        "-- Turbine.UI.Color instances, built once at load.",
        "ThemeColors.color = {};",
        "for name, c in pairs(ThemeColors.raw) do",
        "    ThemeColors.color[name] = Turbine.UI.Color(c.a, c.r, c.g, c.b);",
        "end",
        "",
        "-- Same hue, custom alpha. Handy for hover states and washes.",
        "function ThemeColors.Alpha(name, alpha)",
        "    local c = ThemeColors.raw[name];",
        "    if (c == nil) then return Turbine.UI.Color(1, 1, 0, 1); end",
        "    return Turbine.UI.Color(alpha, c.r, c.g, c.b);",
        "end",
        "",
        "MithrilUI.Core.ThemeColors = ThemeColors;",
        "",
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--theme", default="mithril-dark")
    args = parser.parse_args(argv)

    themes = discover(REPO / "themes")
    if args.theme not in themes:
        raise SystemExit(f"No theme '{args.theme}'. Available: {', '.join(themes)}")

    path = generate(Theme.load(themes[args.theme]))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

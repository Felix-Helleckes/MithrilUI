"""Theme loading and colour resolution.

A theme is a flat JSON file of named colours, named opacities and a little
geometry. Recipes never hardcode a colour -- they ask the theme for a role
("panel", "accent", "border"), which is what makes a full retheme a one-file
change.
"""

from __future__ import annotations

import json
from pathlib import Path

from tga import RGBA, clamp, lighten, parse_color

DEFAULT_OPACITIES = {
    "panel": 0.90,
    "header": 0.95,
    "button": 0.95,
    "chat": 0.55,
    "selection": 0.30,
    "selectionHot": 0.50,
    "overlay": 0.60,
}


class Theme:
    def __init__(self, data: dict, source: Path | None = None):
        self.source = source
        self.id = data.get("id") or (source.stem if source else "unnamed")
        self.name = data.get("name", self.id)
        self.description = data.get("description", "")
        self._colors = data.get("colors", {})
        self._opacities = {**DEFAULT_OPACITIES, **data.get("opacity", {})}
        self.geometry = data.get("geometry", {})
        self.texture = data.get("texture", {"enabled": False})

        missing = [k for k in ("panel", "border", "accent", "text") if k not in self._colors]
        if missing:
            raise ValueError(
                f"theme '{self.id}' is missing required colour(s): {', '.join(missing)}"
            )

    @classmethod
    def load(cls, path: str | Path) -> "Theme":
        path = Path(path)
        with path.open(encoding="utf-8") as handle:
            return cls(json.load(handle), source=path)

    # -- lookups ---------------------------------------------------------

    def opacity(self, name, default: float = 1.0) -> float:
        """Accept an opacity role name, a raw float, or None."""
        if name is None:
            return default
        if isinstance(name, (int, float)):
            return float(name)
        if name not in self._opacities:
            raise KeyError(f"theme '{self.id}' has no opacity role '{name}'")
        return float(self._opacities[name])

    def color(self, name, opacity=None, lighten_by: float = 0.0) -> RGBA:
        """Resolve a colour role (or a literal hex string) to RGBA.

        `opacity` may be an opacity role name or a plain 0..1 float; it
        multiplies whatever alpha the colour already carries.
        """
        if isinstance(name, (list, tuple)):
            resolved = parse_color(name)
        elif isinstance(name, str) and name.startswith("#"):
            resolved = parse_color(name)
        else:
            if name not in self._colors:
                raise KeyError(f"theme '{self.id}' has no colour role '{name}'")
            resolved = parse_color(self._colors[name])

        if lighten_by:
            resolved = lighten(resolved, lighten_by)
        if opacity is not None:
            resolved = (
                resolved[0],
                resolved[1],
                resolved[2],
                clamp(resolved[3] * self.opacity(opacity)),
            )
        return resolved

    @property
    def border_width(self) -> int:
        return max(1, int(self.geometry.get("borderWidth", 1)))

    @property
    def header_accent_width(self) -> int:
        return max(0, int(self.geometry.get("headerAccentWidth", 1)))

    def texture_color(self) -> RGBA | None:
        if not self.texture.get("enabled"):
            return None
        return self.color(
            self.texture.get("color", "#ffffff"),
            opacity=float(self.texture.get("opacity", 0.02)),
        )

    @property
    def texture_step(self) -> int:
        return max(1, int(self.texture.get("step", 3)))


def discover(themes_dir: str | Path) -> dict[str, Path]:
    """Map theme id -> file path for every theme JSON in a directory."""
    themes_dir = Path(themes_dir)
    found = {}
    for path in sorted(themes_dir.glob("*.json")):
        try:
            with path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path} is not valid JSON: {exc}") from exc
        found[data.get("id", path.stem)] = path
    return found

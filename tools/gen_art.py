"""Procedural art generation: skin/assets.json + a theme -> a folder of TGAs.

Nothing here is hand-drawn. Every asset is flat fills, hairline borders and the
occasional circle, which is exactly the point -- "minimal and clean" is a set of
rules, not a pile of PNGs, so a new palette is one JSON file away.

Recipes are registered with @recipe and receive (canvas, theme, params).
"""

from __future__ import annotations

import colorsys
import hashlib
import json
import math
import re
from pathlib import Path

from tga import Canvas, RGBA, clamp
from theme import Theme

RECIPES: dict[str, callable] = {}


def recipe(name: str):
    def register(fn):
        RECIPES[name] = fn
        return fn

    return register


# -- helpers -------------------------------------------------------------

CORNER_EDGES = {"tl": "tl", "tr": "tr", "bl": "bl", "br": "br"}


def _fill_body(canvas: Canvas, theme: Theme, params: dict) -> None:
    """Paint the panel body unless the asset is border-only (fill: "none")."""
    if params.get("fill") == "none":
        return
    body = theme.color(
        params.get("color", "panel"), opacity=params.get("opacity", "panel")
    )
    canvas.fill_rect(0, 0, canvas.width, canvas.height, body)
    if params.get("texture"):
        tex = theme.texture_color()
        if tex:
            canvas.scanline_texture(tex, theme.texture_step)


def _border_color(theme: Theme, params: dict) -> RGBA:
    return theme.color(params.get("borderColor", params.get("color2", "border")))


def _draw_line(canvas: Canvas, x0, y0, x1, y1, color: RGBA, thickness: int = 1) -> None:
    """Bresenham with a square brush -- plenty for a 16px close icon."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    half = thickness // 2
    while True:
        canvas.blend_rect(x0 - half, y0 - half, thickness, thickness, color)
        if x0 == x1 and y0 == y1:
            break
        err2 = 2 * err
        if err2 >= dy:
            err += dy
            x0 += sx
        if err2 <= dx:
            err += dx
            y0 += sy


def _draw_disc(canvas: Canvas, cx: float, cy: float, radius: float, color: RGBA) -> None:
    """Filled circle with a one-pixel antialiased rim."""
    for y in range(canvas.height):
        for x in range(canvas.width):
            dist = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
            if dist <= radius - 0.5:
                canvas.blend_pixel(x, y, color)
            elif dist < radius + 0.5:
                coverage = radius + 0.5 - dist
                canvas.blend_pixel(x, y, (color[0], color[1], color[2], clamp(color[3] * coverage)))


# -- recipes -------------------------------------------------------------


@recipe("solid")
def r_solid(canvas: Canvas, theme: Theme, params: dict) -> None:
    _fill_body(canvas, theme, params)


@recipe("hidden")
def r_hidden(canvas: Canvas, theme: Theme, params: dict) -> None:
    """Fully transparent. The skin engine has no "remove this" verb, so a
    transparent replacement is how ornament gets deleted."""
    return


@recipe("panel")
def r_panel(canvas: Canvas, theme: Theme, params: dict) -> None:
    _fill_body(canvas, theme, params)
    canvas.stroke_rect(
        0, 0, canvas.width, canvas.height,
        _border_color(theme, params),
        theme.border_width,
        params.get("edges", "tlbr"),
    )


@recipe("nine_corner")
def r_nine_corner(canvas: Canvas, theme: Theme, params: dict) -> None:
    """One corner of a 9-slice frame: body fill plus the two meeting edges."""
    _fill_body(canvas, theme, params)
    edges = CORNER_EDGES[params.get("corner", "tl")]
    canvas.stroke_rect(
        0, 0, canvas.width, canvas.height,
        _border_color(theme, params),
        theme.border_width,
        edges,
    )


@recipe("nine_edge")
def r_nine_edge(canvas: Canvas, theme: Theme, params: dict) -> None:
    """One straight side of a 9-slice frame. These tile, so the border line
    must sit flush against the outer edge."""
    _fill_body(canvas, theme, params)
    canvas.stroke_rect(
        0, 0, canvas.width, canvas.height,
        _border_color(theme, params),
        theme.border_width,
        params.get("edge", "t"),
    )


@recipe("header")
def r_header(canvas: Canvas, theme: Theme, params: dict) -> None:
    """Title bar: flat header fill, hairline accent along the bottom so the
    title reads as a header without a carved-stone texture."""
    canvas.fill_rect(
        0, 0, canvas.width, canvas.height,
        theme.color(params.get("color", "header"), opacity=params.get("opacity", "header")),
    )
    border = _border_color(theme, params)
    edges = params.get("edges", "")
    if edges:
        canvas.stroke_rect(0, 0, canvas.width, canvas.height, border, theme.border_width, edges)
    canvas.stroke_rect(0, 0, canvas.width, canvas.height, border, theme.border_width, "t")
    accent_width = theme.header_accent_width
    if accent_width:
        canvas.blend_rect(
            0, canvas.height - accent_width, canvas.width, accent_width,
            theme.color(params.get("accent", "accent"), opacity=0.65),
        )


BUTTON_STATES = {
    "normal": ("button", "border", 0.0),
    "hover": ("buttonHover", "borderBright", 0.0),
    "down": ("buttonDown", "border", 0.0),
    "disabled": ("buttonDisabled", "border", 0.0),
}


@recipe("button")
def r_button(canvas: Canvas, theme: Theme, params: dict) -> None:
    state = params.get("state", "normal")
    fill_role, border_role, _ = BUTTON_STATES.get(state, BUTTON_STATES["normal"])
    fill = theme.color(fill_role, opacity="button")
    if state == "disabled":
        fill = (fill[0], fill[1], fill[2], clamp(fill[3] * 0.6))
    canvas.fill_rect(0, 0, canvas.width, canvas.height, fill)

    border = theme.color(border_role)
    if params.get("highlighted"):
        # "Highlighted" is LOTRO's default/confirm button. Accent border plus a
        # faint accent wash keeps it obvious without a gold bevel.
        canvas.blend_rect(0, 0, canvas.width, canvas.height, theme.color("accent", opacity=0.14))
        border = theme.color("accent", opacity=0.85)
    if state == "hover":
        canvas.blend_rect(0, 0, canvas.width, canvas.height, theme.color("accent", opacity=0.08))

    canvas.stroke_rect(
        0, 0, canvas.width, canvas.height, border, theme.border_width,
        params.get("edges", "tlbr"),
    )


@recipe("close_button")
def r_close_button(canvas: Canvas, theme: Theme, params: dict) -> None:
    state = params.get("state", "normal")
    color = {
        "normal": theme.color("textDim"),
        "hover": theme.color("bad"),
        "down": theme.color("bad", lighten_by=-0.0, opacity=0.7),
    }.get(state, theme.color("textDim"))

    inset = max(3, canvas.width // 4)
    lo, hi = inset, canvas.width - inset - 1
    _draw_line(canvas, lo, lo, hi, hi, color, 1)
    _draw_line(canvas, hi, lo, lo, hi, color, 1)


@recipe("dot")
def r_dot(canvas: Canvas, theme: Theme, params: dict) -> None:
    color = theme.color(params.get("color", "accent"))
    radius = min(canvas.width, canvas.height) / 2.0 - 1.5
    _draw_disc(canvas, canvas.width / 2.0, canvas.height / 2.0, max(1.5, radius), color)


@recipe("tab")
def r_tab(canvas: Canvas, theme: Theme, params: dict) -> None:
    """Front = active tab (brighter, accent underline on top). Back = inactive."""
    front = params.get("state", "front") == "front"
    body = theme.color("panelAlt" if front else "panel", opacity="panel")
    if not front:
        body = (body[0], body[1], body[2], clamp(body[3] * 0.75))
    canvas.fill_rect(0, 0, canvas.width, canvas.height, body)

    canvas.stroke_rect(
        0, 0, canvas.width, canvas.height,
        theme.color("borderBright" if front else "border"),
        theme.border_width,
        params.get("edges", "t"),
    )
    if front:
        canvas.blend_rect(0, 0, canvas.width, max(1, theme.border_width + 1), theme.color("accent"))


SELECTION_STATES = {
    "idle": (None, 0.0),
    "normal": ("selection", 1.0),
    "hot": ("selectionHot", 1.0),
    "disabled": ("selection", 0.4),
}


@recipe("selection")
def r_selection(canvas: Canvas, theme: Theme, params: dict) -> None:
    """A list row highlight: soft accent wash plus a solid 2px accent bar down
    the left edge. The bar is what makes selection readable at a glance once
    the heavy blue gradient is gone."""
    state = params.get("state", "normal")
    opacity_role, scale = SELECTION_STATES.get(state, SELECTION_STATES["normal"])
    if opacity_role is None:
        return

    role = params.get("color", "selection")
    base = theme.color(role, opacity=opacity_role)
    if scale != 1.0:
        base = (base[0], base[1], base[2], clamp(base[3] * scale))

    # Fade the wash out to the right so long rows do not turn into a slab.
    for x in range(canvas.width):
        t = x / max(1, canvas.width - 1)
        alpha = base[3] * (1.0 - 0.45 * t)
        canvas.blend_rect(x, 0, 1, canvas.height, (base[0], base[1], base[2], clamp(alpha)))

    bar_width = 2 if canvas.width >= 24 else 1
    canvas.blend_rect(0, 0, bar_width, canvas.height, theme.color(role, opacity=0.9 * scale))


@recipe("divider")
def r_divider(canvas: Canvas, theme: Theme, params: dict) -> None:
    """A horizontal rule on a transparent field, centred vertically."""
    y = canvas.height // 2
    canvas.blend_rect(0, y, canvas.width, theme.border_width, theme.color("border"))


@recipe("ring")
def r_ring(canvas: Canvas, theme: Theme, params: dict) -> None:
    """Square outline, inset so it frames the quickslot rather than covering it."""
    thickness = int(params.get("thickness", 1))
    color = theme.color(params.get("color", "accent"), lighten_by=params.get("lighten", 0.0))
    inset = int(params.get("inset", 1))
    canvas.stroke_rect(
        inset, inset,
        canvas.width - 2 * inset, canvas.height - 2 * inset,
        color, thickness, "tlbr",
    )


@recipe("gradient")
def r_gradient(canvas: Canvas, theme: Theme, params: dict) -> None:
    top = theme.color(params.get("from", "panelAlt"), opacity=params.get("opacity", "panel"))
    bottom = theme.color(params.get("to", "panel"), opacity=params.get("opacity", "panel"))
    canvas.vertical_gradient(0, 0, canvas.width, canvas.height, top, bottom)


# -- manifest driving ----------------------------------------------------


def generate_sweep(
    dictionary_path: str | Path,
    rules_path: str | Path,
    theme: Theme,
    out_dir: str | Path,
    explicit_ids: set[str],
    rle: bool = False,
    catch_all: bool = True,
    debug: bool = False,
    debug_unique: bool = False,
    verbose: bool = False,
) -> tuple[list[dict], dict[str, int]]:
    """Flatten every ArtAssetID the hand-written manifest does not cover.

    The documented dictionary is from 2007 and lists a fraction of what the
    modern client actually draws, so covering only it leaves the interface
    looking untouched. This assigns a flat colour to the rest by name pattern.

    Because every sweep asset is a solid fill, all IDs sharing a role can point
    at the same file: thousands of mappings cost a handful of TGAs, and the
    exact dimension the game expects stops mattering.
    """
    out_dir = Path(out_dir)
    with Path(rules_path).open(encoding="utf-8") as handle:
        config = json.load(handle)

    size = config.get("sharedAssetSize", [128, 128])
    excludes = [re.compile(pattern, re.IGNORECASE) for pattern in config.get("exclude", [])]
    rules = []
    for rule in config.get("rules", []):
        if rule.get("catchAll") and not catch_all:
            continue
        rules.append((re.compile(rule["match"], re.IGNORECASE), rule))

    ids = [
        line.strip()
        for line in Path(dictionary_path).read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    def unique_color(asset_id: str) -> RGBA:
        """A vivid, stable colour per asset ID.

        Identification mode gives every single asset its own colour and writes
        a legend beside the skin. Screenshot the thing you are asking about,
        read the pixel, look it up: the answer is the exact ArtAssetID rather
        than a category. That is the only way to name an asset whose ID gives
        no hint what it draws, which is most of them.

        Kept saturated and mid-bright so JPEG screenshots stay legible.
        """
        digest = hashlib.md5(asset_id.encode("utf-8")).digest()
        hue = digest[0] / 255.0
        saturation = 0.70 + (digest[1] / 255.0) * 0.30
        value = 0.55 + (digest[2] / 255.0) * 0.40
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        return (clamp(r * 255), clamp(g * 255), clamp(b * 255), 255)

    legend: list[tuple[str, str]] = []
    shared: dict[str, str] = {}       # role -> relative file path
    written: list[dict] = []
    stats = {
        "total": len(ids), "explicit": 0, "excluded": 0,
        "swept": 0, "unmatched": 0, "catchAll": 0,
    }

    for asset_id in ids:
        if asset_id in explicit_ids:
            stats["explicit"] += 1
            continue
        if any(pattern.search(asset_id) for pattern in excludes):
            stats["excluded"] += 1
            continue

        matched = next((rule for pattern, rule in rules if pattern.search(asset_id)), None)
        if matched is None:
            stats["unmatched"] += 1
            continue

        if matched.get("catchAll"):
            stats["catchAll"] += 1

        if debug_unique:
            color = unique_color(asset_id)
            # 8x8 is plenty: the client stretches it, and 1900 of these cost
            # half a megabyte instead of a hundred.
            canvas = Canvas(8, 8)
            canvas.fill_rect(0, 0, 8, 8, color)
            relative = Path("art") / "ident" / f"{asset_id}.tga"
            canvas.save(out_dir / relative, rle=rle)
            hex_code = f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
            legend.append((hex_code, asset_id))
            written.append({
                "id": asset_id,
                "file": relative.as_posix().replace("/", "\\"),
                "module": "sweep",
                "bytes": 0,
            })
            stats["swept"] += 1
            continue

        role = matched["role"]
        if role not in shared:
            canvas = Canvas(size[0], size[1])
            if debug:
                # Diagnostic mode: paint every swept asset a solid, garish
                # colour keyed to the rule that matched it. Anything that
                # lights up in game is something this skin controls; anything
                # that stays as it was is drawn by the client and cannot be
                # reached from a skin at all. Answers "did I cause that?" in
                # one relog instead of a guessing session.
                fill = theme.color(matched.get("debugColor", "#ff00ff"), opacity=1.0)
            else:
                fill = theme.color(matched["color"], opacity=matched.get("opacity"))
            canvas.fill_rect(0, 0, size[0], size[1], fill)
            relative = Path("art") / "sweep" / f"{role}.tga"
            canvas.save(out_dir / relative, rle=rle)
            shared[role] = relative.as_posix().replace("/", "\\")
            if verbose:
                print(f"  shared fill: {role}")

        written.append(
            {"id": asset_id, "file": shared[role], "module": "sweep", "bytes": 0}
        )
        stats["swept"] += 1

    if legend:
        legend_path = out_dir / "debug-legend.txt"
        lines = [
            "# MithrilUI identification legend",
            "# Every swept asset drawn in its own colour. Screenshot the element",
            "# you are asking about, read the pixel colour, find it here.",
            "#",
            "# Look one up:  python tools/debug_lookup.py \"#a1b2c3\"",
            "",
        ]
        lines += [f"{hex_code}  {asset_id}" for hex_code, asset_id in sorted(legend)]
        legend_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Record the real file sizes once, against the first mapping that uses each.
    counted: set[str] = set()
    for record in written:
        if record["file"] not in counted:
            counted.add(record["file"])
            record["bytes"] = (out_dir / Path(record["file"].replace("\\", "/"))).stat().st_size

    return written, stats


def load_manifest(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    # Entries that only carry "$group" are section comments for humans.
    return [entry for entry in data["assets"] if "id" in entry]


def generate(
    manifest_path: str | Path,
    theme: Theme,
    out_dir: str | Path,
    modules: set[str] | None = None,
    rle: bool = False,
    verbose: bool = False,
) -> list[dict]:
    """Render every enabled asset. Returns records for the skin generator."""
    entries = load_manifest(manifest_path)
    out_dir = Path(out_dir)
    written = []

    for entry in entries:
        module = entry.get("module", "misc")
        if modules is not None and module not in modules:
            continue

        recipe_name = entry["recipe"]
        if recipe_name not in RECIPES:
            raise KeyError(
                f"asset '{entry['id']}' wants unknown recipe '{recipe_name}'. "
                f"Known recipes: {', '.join(sorted(RECIPES))}"
            )

        width, height = entry["size"]
        canvas = Canvas(width, height)
        RECIPES[recipe_name](canvas, theme, entry.get("params", {}))

        rel = Path("art") / module / f"{entry['id']}.tga"
        size_bytes = canvas.save(out_dir / rel, rle=rle)
        written.append(
            {
                "id": entry["id"],
                "file": rel.as_posix().replace("/", "\\"),
                "module": module,
                "bytes": size_bytes,
            }
        )
        if verbose:
            print(f"  {entry['id']:<52} {width:>4}x{height:<4} {size_bytes / 1024:>8.1f} KB")

    return written

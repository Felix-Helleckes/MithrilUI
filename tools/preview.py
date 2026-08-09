"""Render a PNG mock-up of a built skin, so you can judge a theme without
restarting the game.

    python tools/preview.py                          # newest built skin
    python tools/preview.py dist/skins/MithrilUI --out preview.png
    python tools/preview.py dist/skins/MithrilUI --sheet   # every asset, tiled

The mock-up composites the *actual generated TGAs* -- 9-slicing the frame,
stretching the title bar, stacking real button and tab art -- rather than
redrawing them from the theme. If the preview looks right, the files are right.

Writes PNG with nothing but zlib from the standard library.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from tga import Canvas, parse_color

REPO = Path(__file__).resolve().parent.parent


# -- PNG output ----------------------------------------------------------


def write_png(path: Path, canvas: Canvas) -> int:
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + tag
            + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF)
        )

    row_bytes = canvas.width * 4
    raw = bytearray()
    for y in range(canvas.height):
        raw.append(0)  # filter type: none
        raw += canvas.pixels[y * row_bytes : (y + 1) * row_bytes]

    payload = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", canvas.width, canvas.height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return len(payload)


# -- asset lookup --------------------------------------------------------


class SkinAssets:
    """Find generated TGAs by ArtAssetID, wherever the module folders put them."""

    def __init__(self, skin_dir: Path):
        self.skin_dir = skin_dir
        self.index: dict[str, Path] = {}
        for path in (skin_dir / "art").rglob("*.tga"):
            self.index[path.stem] = path
        self._cache: dict[str, Canvas] = {}

    def get(self, asset_id: str) -> Canvas | None:
        if asset_id in self._cache:
            return self._cache[asset_id]
        path = self.index.get(asset_id)
        if not path:
            return None
        canvas = Canvas.load(path)
        self._cache[asset_id] = canvas
        return canvas

    def blit(self, target: Canvas, asset_id: str, x: int, y: int, w=None, h=None) -> bool:
        art = self.get(asset_id)
        if art is None:
            return False
        if w is None and h is None:
            target.draw(art, x, y)
        else:
            target.draw_scaled(art, x, y, w or art.width, h or art.height)
        return True


def nine_slice(
    target: Canvas, assets: SkinAssets, x: int, y: int, w: int, h: int, prefix: str, body: str
) -> None:
    """Draw a framed panel the way the client does: centre fill, stretched
    edges, untouched corners."""
    # Corners are drawn at their native size; only the four edges stretch.
    corner = assets.get(f"{prefix}_topleft")
    edge = min(corner.width, w // 3, h // 3) if corner else 6

    assets.blit(target, body, x, y, w, h)
    assets.blit(target, f"{prefix}_topmid", x + edge, y, w - 2 * edge, edge)
    assets.blit(target, f"{prefix}_bottommid", x + edge, y + h - edge, w - 2 * edge, edge)
    assets.blit(target, f"{prefix}_midleft", x, y + edge, edge, h - 2 * edge)
    assets.blit(target, f"{prefix}_midright", x + w - edge, y + edge, edge, h - 2 * edge)
    assets.blit(target, f"{prefix}_topleft", x, y, edge, edge)
    assets.blit(target, f"{prefix}_topright", x + w - edge, y, edge, edge)
    assets.blit(target, f"{prefix}_bottomleft", x, y + h - edge, edge, edge)
    assets.blit(target, f"{prefix}_bottomright", x + w - edge, y + h - edge, edge, edge)


# -- the mock window -----------------------------------------------------


def build_mockup(assets: SkinAssets) -> Canvas:
    width, height = 900, 560
    canvas = Canvas(width, height, parse_color("#1b1f24"))

    # A muted "world" backdrop so panel transparency is actually visible.
    for y in range(height):
        t = y / height
        canvas.fill_rect(
            0, y, width, 1,
            (
                int(38 + 24 * t),
                int(46 + 30 * t),
                int(40 + 20 * t),
                255,
            ),
        )
    for i in range(0, width, 64):
        canvas.blend_rect(i, 0, 1, height, (255, 255, 255, 8))

    # Main window: title bar, tab row, list of selectable rows, buttons.
    px, py, pw, ph = 40, 40, 520, 400
    nine_slice(canvas, assets, px, py, pw, ph, "basepanel", "base_box_center")

    title_h = 26
    assets.blit(canvas, "base_box_titlebar_left", px, py, 18, title_h)
    assets.blit(canvas, "base_box_titlebar_top", px + 18, py, pw - 36, title_h)
    assets.blit(canvas, "base_box_titlebar_right", px + pw - 18, py, 18, title_h)
    assets.blit(canvas, "titlebar_X_2", px + pw - 24, py + 5)

    tab_y = py + title_h + 6
    tab_x = px + 10
    for index in range(4):
        state = "front" if index == 1 else "back"
        assets.blit(canvas, f"tab_tier1_middle_{state}_w_sm", tab_x, tab_y, 8, 20)
        assets.blit(canvas, f"tab_tier1_middle_{state}_n_sm", tab_x + 8, tab_y, 74, 20)
        assets.blit(canvas, f"tab_tier1_middle_{state}_e_sm", tab_x + 82, tab_y, 8, 20)
        tab_x += 96

    row_y = tab_y + 30
    row_states = ["blue_selection_quest_normal", "blue_selection_quest_highlight",
                  "blue_selection_quest_highlight_active", "blue_selection_quest_normal",
                  "blue_selection_quest_normal"]
    for asset_id in row_states:
        assets.blit(canvas, asset_id, px + 12, row_y, pw - 24, 30)
        row_y += 34

    assets.blit(canvas, "options_panel_divider", px + 12, row_y + 4, pw - 24, 12)

    btn_y = py + ph - 34
    for index, (left, mid, right) in enumerate(
        [
            ("textbutton_left_normal", "textbutton_mid_normal", "textbutton_right_normal"),
            ("textbutton_left_mouseover", "textbutton_mid_mouseover", "textbutton_right_mouseover"),
            ("textbutton_left_highlighted_normal", "textbutton_mid_highlighted_normal",
             "textbutton_right_highlighted_normal"),
            ("textbutton_left_ghosted", "textbutton_mid_ghosted", "textbutton_right_ghosted"),
        ]
    ):
        bx = px + 14 + index * 124
        assets.blit(canvas, left, bx, btn_y, 12, 20)
        assets.blit(canvas, mid, bx + 12, btn_y, 88, 20)
        assets.blit(canvas, right, bx + 100, btn_y, 12, 20)

    # Chat window: the transparency test.
    cx, cy, cw, ch = 40, 460, 520, 80
    assets.blit(canvas, "chat_back", cx, cy, cw, ch)
    chat_tab_x = cx + 6
    for index in range(3):
        state = "front" if index == 0 else "back"
        assets.blit(canvas, f"chat_tab_tier1_middle_{state}_w", chat_tab_x, cy - 18, 8, 18)
        assets.blit(canvas, f"chat_tab_tier1_middle_{state}_n", chat_tab_x + 8, cy - 18, 62, 18)
        assets.blit(canvas, f"chat_tab_tier1_middle_{state}_e", chat_tab_x + 70, cy - 18, 8, 18)
        chat_tab_x += 84
    assets.blit(canvas, "chat_entry_focussed", cx, cy + ch - 18, cw, 18)

    # Right column: silver frame, autoattack ring, social highlight, money bar.
    sx, sy, sw, sh = 590, 40, 270, 190
    nine_slice(canvas, assets, sx, sy, sw, sh, "box_silver", "base_box_center_silver")
    assets.blit(canvas, "box_01_titlebar", sx + 8, sy + 8, sw - 16, 18)
    assets.blit(canvas, "money_player_all_background", sx + 12, sy + sh - 40, sw - 24, 24)

    assets.blit(canvas, "button_autoattack_highlight", 600, 250, 56, 56)
    assets.blit(canvas, "button_autoattack_mouseover", 664, 250, 56, 56)
    assets.blit(canvas, "social_panel_list_elements_highlight_center", 730, 250, 120, 56)

    assets.blit(canvas, "im_button_normal", 600, 320, 80, 19)
    assets.blit(canvas, "im_button_rollover", 690, 320, 80, 19)
    assets.blit(canvas, "im_button_pressed", 780, 320, 80, 19)
    assets.blit(canvas, "button_main_normal", 600, 350, 51, 34)
    assets.blit(canvas, "button_main_mouseover", 660, 350, 51, 34)
    assets.blit(canvas, "button_main_pressed", 720, 350, 51, 34)
    assets.blit(canvas, "im_chat_alert", 790, 358)

    assets.blit(canvas, "blue_mail_select_normal", 590, 400, 270, 26)
    assets.blit(canvas, "blue_mail_select_highlight", 590, 430, 270, 26)
    assets.blit(canvas, "blue_mail_select_highlight_active", 590, 460, 270, 26)
    assets.blit(canvas, "green_selection_vendor_item_stacktoggleon", 590, 490, 270, 26)

    return canvas


def build_sheet(assets: SkinAssets, columns: int = 8, cell: int = 96) -> Canvas:
    """Contact sheet of every generated asset, scaled to fit its cell."""
    ids = sorted(assets.index)
    rows = (len(ids) + columns - 1) // columns
    canvas = Canvas(columns * cell, rows * cell, parse_color("#22262b"))

    for index, asset_id in enumerate(ids):
        col, row = index % columns, index // columns
        ox, oy = col * cell, row * cell
        # Checkerboard so transparency is legible.
        for cy in range(0, cell, 8):
            for cx in range(0, cell, 8):
                shade = 52 if ((cx // 8) + (cy // 8)) % 2 else 40
                canvas.fill_rect(ox + cx, oy + cy, 8, 8, (shade, shade, shade, 255))

        art = assets.get(asset_id)
        if art is None:
            continue
        scale = min((cell - 12) / art.width, (cell - 12) / art.height, 1.0)
        w, h = max(1, int(art.width * scale)), max(1, int(art.height * scale))
        canvas.draw_scaled(art, ox + (cell - w) // 2, oy + (cell - h) // 2, w, h)
        canvas.stroke_rect(ox, oy, cell, cell, (255, 255, 255, 18), 1, "tlbr")

    return canvas


def newest_skin() -> Path:
    dist = REPO / "dist" / "skins"
    candidates = [p for p in dist.glob("*") if p.is_dir()] if dist.exists() else []
    if not candidates:
        raise SystemExit("No built skins. Run: python tools/build.py")
    return max(candidates, key=lambda p: p.stat().st_mtime)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("skin", nargs="?", help="built skin folder (default: newest in dist/skins)")
    parser.add_argument("--out", help="output PNG path")
    parser.add_argument("--sheet", action="store_true", help="contact sheet instead of a mock window")
    args = parser.parse_args(argv)

    skin_dir = Path(args.skin) if args.skin else newest_skin()
    if not (skin_dir / "art").exists():
        raise SystemExit(f"No art/ folder in {skin_dir}. Build it first.")

    assets = SkinAssets(skin_dir)
    canvas = build_sheet(assets) if args.sheet else build_mockup(assets)

    suffix = "-sheet" if args.sheet else "-preview"
    out = Path(args.out) if args.out else REPO / "dist" / f"{skin_dir.name}{suffix}.png"
    size = write_png(out, canvas)
    print(f"{out}  ({canvas.width}x{canvas.height}, {size / 1024:.0f} KB, "
          f"{len(assets.index)} assets available)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

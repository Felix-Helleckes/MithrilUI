"""Minimal, dependency-free TGA writer and drawing canvas.

LOTRO's skin engine reads uncompressed and RLE-compressed 32-bit TGA files.
Everything MithrilUI draws is flat geometry -- solid fills, 1px borders,
straight gradients -- so a tiny hand-rolled rasteriser is enough and keeps the
build runnable on a bare Python install with no `pip install` step.

Colours are RGBA tuples of ints 0-255. The canvas stores them in that order and
only swizzles to BGRA when writing the file.
"""

from __future__ import annotations

import struct
from pathlib import Path

RGBA = tuple[int, int, int, int]

TRANSPARENT: RGBA = (0, 0, 0, 0)


def clamp(value: float, low: int = 0, high: int = 255) -> int:
    return max(low, min(high, int(round(value))))


def parse_color(value, default_alpha: int = 255) -> RGBA:
    """Accept "#rrggbb", "#rrggbbaa", or a [r, g, b(, a)] sequence."""
    if isinstance(value, (list, tuple)):
        parts = list(value)
        if len(parts) == 3:
            parts.append(default_alpha)
        if len(parts) != 4:
            raise ValueError(f"colour needs 3 or 4 components, got {value!r}")
        return tuple(clamp(p) for p in parts)  # type: ignore[return-value]

    if not isinstance(value, str):
        raise TypeError(f"cannot read colour from {value!r}")

    text = value.strip().lstrip("#")
    if len(text) == 6:
        text += f"{default_alpha:02x}"
    if len(text) != 8:
        raise ValueError(f"colour hex must be 6 or 8 digits, got {value!r}")
    return (
        int(text[0:2], 16),
        int(text[2:4], 16),
        int(text[4:6], 16),
        int(text[6:8], 16),
    )


def with_alpha(color: RGBA, alpha: int) -> RGBA:
    return (color[0], color[1], color[2], clamp(alpha))


def scale_alpha(color: RGBA, factor: float) -> RGBA:
    return (color[0], color[1], color[2], clamp(color[3] * factor))


def mix(a: RGBA, b: RGBA, t: float) -> RGBA:
    """Linear interpolation from a to b. t=0 gives a, t=1 gives b."""
    t = max(0.0, min(1.0, t))
    return tuple(clamp(a[i] + (b[i] - a[i]) * t) for i in range(4))  # type: ignore[return-value]


def lighten(color: RGBA, amount: float) -> RGBA:
    """Push a colour toward white without touching its alpha."""
    r, g, b, a = color
    return (
        clamp(r + (255 - r) * amount),
        clamp(g + (255 - g) * amount),
        clamp(b + (255 - b) * amount),
        a,
    )


def darken(color: RGBA, amount: float) -> RGBA:
    r, g, b, a = color
    return (clamp(r * (1 - amount)), clamp(g * (1 - amount)), clamp(b * (1 - amount)), a)


class Canvas:
    """A fixed-size RGBA raster with the handful of primitives the skin needs."""

    def __init__(self, width: int, height: int, fill: RGBA = TRANSPARENT):
        if width < 1 or height < 1:
            raise ValueError(f"canvas must be at least 1x1, got {width}x{height}")
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(fill) * (width * height))

    # -- pixel access ----------------------------------------------------

    def set_pixel(self, x: int, y: int, color: RGBA) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            offset = (y * self.width + x) * 4
            self.pixels[offset : offset + 4] = bytes(color)

    def get_pixel(self, x: int, y: int) -> RGBA:
        offset = (y * self.width + x) * 4
        return tuple(self.pixels[offset : offset + 4])  # type: ignore[return-value]

    def blend_pixel(self, x: int, y: int, color: RGBA) -> None:
        """Source-over alpha blend, so overlapping strokes look right."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        src_a = color[3] / 255.0
        if src_a >= 1.0:
            self.set_pixel(x, y, color)
            return
        if src_a <= 0.0:
            return
        dst = self.get_pixel(x, y)
        dst_a = dst[3] / 255.0
        out_a = src_a + dst_a * (1 - src_a)
        if out_a <= 0:
            self.set_pixel(x, y, TRANSPARENT)
            return
        out = tuple(
            clamp((color[i] * src_a + dst[i] * dst_a * (1 - src_a)) / out_a)
            for i in range(3)
        )
        self.set_pixel(x, y, (out[0], out[1], out[2], clamp(out_a * 255)))

    # -- primitives ------------------------------------------------------

    def fill(self, color: RGBA) -> None:
        self.pixels = bytearray(bytes(color) * (self.width * self.height))

    def fill_rect(self, x: int, y: int, w: int, h: int, color: RGBA) -> None:
        """Opaque overwrite -- fastest path, used for backgrounds."""
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.width, x + w), min(self.height, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(color) * (x1 - x0)
        for row_y in range(y0, y1):
            offset = (row_y * self.width + x0) * 4
            self.pixels[offset : offset + len(row)] = row

    def blend_rect(self, x: int, y: int, w: int, h: int, color: RGBA) -> None:
        if color[3] >= 255:
            self.fill_rect(x, y, w, h, color)
            return
        for row_y in range(max(0, y), min(self.height, y + h)):
            for col_x in range(max(0, x), min(self.width, x + w)):
                self.blend_pixel(col_x, row_y, color)

    def stroke_rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        color: RGBA,
        thickness: int = 1,
        edges: str = "tlbr",
    ) -> None:
        """Draw an inset border. `edges` selects which sides get a line:
        any combination of t(op), l(eft), b(ottom), r(ight)."""
        thickness = max(1, thickness)
        if "t" in edges:
            self.blend_rect(x, y, w, thickness, color)
        if "b" in edges:
            self.blend_rect(x, y + h - thickness, w, thickness, color)
        if "l" in edges:
            self.blend_rect(x, y, thickness, h, color)
        if "r" in edges:
            self.blend_rect(x + w - thickness, y, thickness, h, color)

    def vertical_gradient(
        self, x: int, y: int, w: int, h: int, top: RGBA, bottom: RGBA
    ) -> None:
        if h <= 0:
            return
        for i in range(h):
            t = i / max(1, h - 1)
            self.blend_rect(x, y + i, w, 1, mix(top, bottom, t))

    def horizontal_gradient(
        self, x: int, y: int, w: int, h: int, left: RGBA, right: RGBA
    ) -> None:
        if w <= 0:
            return
        for i in range(w):
            t = i / max(1, w - 1)
            self.blend_rect(x + i, y, 1, h, mix(left, right, t))

    def scanline_texture(self, color: RGBA, step: int = 2) -> None:
        """Very subtle horizontal banding -- keeps large flat panels from
        looking like dead space without adding any actual ornament."""
        if step < 1:
            return
        for row_y in range(0, self.height, step):
            self.blend_rect(0, row_y, self.width, 1, color)

    # -- output ----------------------------------------------------------

    def to_bgra(self) -> bytes:
        out = bytearray(len(self.pixels))
        out[0::4] = self.pixels[2::4]  # B
        out[1::4] = self.pixels[1::4]  # G
        out[2::4] = self.pixels[0::4]  # R
        out[3::4] = self.pixels[3::4]  # A
        return bytes(out)

    def _header(self, data_type: int) -> bytes:
        # id len, colourmap type, image type, colourmap spec (5 bytes),
        # x/y origin, width, height, bpp, descriptor.
        # Descriptor 0x28 = 8 alpha bits + top-left origin.
        return struct.pack(
            "<BBBHHBHHHHBB",
            0, 0, data_type, 0, 0, 0, 0, 0,
            self.width, self.height, 32, 0x28,
        )

    def _rle_body(self) -> bytes:
        """Row-wise RLE. Packets never cross a scanline, which is what the
        stricter TGA readers expect."""
        bgra = self.to_bgra()
        out = bytearray()
        for row in range(self.height):
            base = row * self.width * 4
            pixels = [bgra[base + i * 4 : base + i * 4 + 4] for i in range(self.width)]
            i = 0
            while i < self.width:
                run = 1
                while (
                    run < 128
                    and i + run < self.width
                    and pixels[i + run] == pixels[i]
                ):
                    run += 1
                if run > 1:
                    out.append(0x80 | (run - 1))
                    out += pixels[i]
                    i += run
                    continue
                raw = 1
                while (
                    raw < 128
                    and i + raw < self.width
                    and pixels[i + raw] != pixels[i + raw - 1]
                ):
                    raw += 1
                if raw > 1 and i + raw < self.width and pixels[i + raw] == pixels[i + raw - 1]:
                    raw -= 1
                out.append(raw - 1)
                for k in range(raw):
                    out += pixels[i + k]
                i += raw
        return bytes(out)

    def save(self, path: str | Path, rle: bool = False) -> int:
        """Write the TGA and return the byte count.

        Uncompressed (rle=False) is the default because every LOTRO client
        reads it. RLE files are far smaller for flat art but should be
        verified in-game before you rely on them.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if rle:
            payload = self._header(10) + self._rle_body()
        else:
            payload = self._header(2) + self.to_bgra()
        path.write_bytes(payload)
        return len(payload)

    # -- input -----------------------------------------------------------

    @classmethod
    def load(cls, path: str | Path) -> "Canvas":
        """Read back a 32-bit TGA we wrote. Used by the preview tool so it
        composites the real output rather than a second guess at it."""
        data = Path(path).read_bytes()
        (
            id_len, _cmap_type, data_type, _cmap_origin, _cmap_len, _cmap_depth,
            _x_origin, _y_origin, width, height, bpp, descriptor,
        ) = struct.unpack("<BBBHHBHHHHBB", data[:18])
        if bpp != 32 or data_type not in (2, 10):
            raise ValueError(f"{path}: expected 32-bit true-colour TGA, got {bpp}bpp type {data_type}")

        body = data[18 + id_len :]
        if data_type == 2:
            bgra = body[: width * height * 4]
        else:
            bgra = bytearray()
            i = 0
            while len(bgra) < width * height * 4 and i < len(body):
                packet = body[i]
                i += 1
                count = (packet & 0x7F) + 1
                if packet & 0x80:
                    bgra += body[i : i + 4] * count
                    i += 4
                else:
                    bgra += body[i : i + 4 * count]
                    i += 4 * count
            bgra = bytes(bgra[: width * height * 4])

        canvas = cls(width, height)
        pixels = bytearray(len(bgra))
        pixels[0::4] = bgra[2::4]
        pixels[1::4] = bgra[1::4]
        pixels[2::4] = bgra[0::4]
        pixels[3::4] = bgra[3::4]
        canvas.pixels = pixels

        if not descriptor & 0x20:  # bottom-left origin: flip into top-left
            row = width * 4
            flipped = bytearray(len(pixels))
            for y in range(height):
                flipped[y * row : (y + 1) * row] = pixels[(height - 1 - y) * row : (height - y) * row]
            canvas.pixels = flipped
        return canvas

    def draw(self, other: "Canvas", x: int, y: int) -> None:
        """Alpha-composite another canvas onto this one."""
        for row in range(other.height):
            for col in range(other.width):
                self.blend_pixel(x + col, y + row, other.get_pixel(col, row))

    def draw_scaled(self, other: "Canvas", x: int, y: int, w: int, h: int) -> None:
        """Nearest-neighbour stretch. The game tiles or stretches 9-slice
        pieces the same way, so this is a fair approximation for a preview."""
        if w <= 0 or h <= 0:
            return
        for row in range(h):
            src_y = min(other.height - 1, row * other.height // h)
            for col in range(w):
                src_x = min(other.width - 1, col * other.width // w)
                self.blend_pixel(x + col, y + row, other.get_pixel(src_x, src_y))

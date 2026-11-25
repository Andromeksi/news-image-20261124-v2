#!/usr/bin/env python3
"""news-image-20261124 v2 (Builder 1) — one day's world news in one image.

Python 3.13 standard library only. Own rasterizer, hand-built 5x7 bitmap
font, zlib PNG encoder. Fully deterministic: no randomness, no wall clock,
no unordered iteration. Writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR).

Layout (1024x1024): masthead naming the day, central Earth, story panels
around it, secondary ticker strip at the foot. Builder 2: 13 panels —
hero ICJ/MYANMAR, NATO/SPACE, COP31, and two five-across bottom rows
(LIBYA, HORMUZ, GAZA, NVIDIA, GROK / EL CHAPO ISIDRO, SOLOMON ISLANDS,
DRC, NEPAL, MEASLES). The middle band shrank (130-560) so the bottom
holds two rows; masthead and Earth did not move. Motifs are drawn
proportional to their motif height so they fit the compact rows.

BUILDER 2 EXTENSION: panels 8-13 were appended to the PANELS registry
below (same dict shape as Builder 1's), with six new motif_* functions
and the four bottom-row motifs plus the two right-column motifs made
height-aware. Geometry rules still hold: every title/sub line fits
w - 16 px (len * 6 * scale - scale), every label names its place,
24 Nov facts only (see ~/workspace/makefun/news-image-20261124-news.md):
no 23 Nov items, no burning tankers in Hormuz, Libya is the 24 Nov
probe/demand not the 22 Nov blast.
"""

import os
import struct
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette
BG_TOP = (5, 8, 20)
BG_BOT = (11, 15, 34)
PANEL_BG = (13, 20, 38)
PANEL_EDGE = (62, 84, 124)
WHITE = (235, 238, 245)
DIM = (168, 180, 198)
GOLD = (212, 175, 55)
GOLD_DIM = (160, 128, 40)
BLUE = (96, 150, 220)
SKY = (140, 190, 235)
GREEN = (96, 190, 120)
RED = (224, 92, 72)
CORAL = (235, 130, 90)
TEAL = (90, 200, 180)
PURPLE = (170, 130, 220)
OCEAN = (24, 68, 138)
OCEAN_DK = (16, 48, 104)
LAND = (74, 140, 84)
LAND2 = (110, 160, 90)
ICE = (225, 232, 240)
GRID = (52, 96, 160)

# ---------------------------------------------------------------- font
# Hand-built 5x7 bitmap font. Each glyph: 7 rows of 5 cells, '#' = ink.
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ",": ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    "/": ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    "(": ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ")": ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    "%": ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    "&": ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    "+": ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    "=": ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    "$": ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def text_width(text, scale):
    """Pixel width of text at the given integer scale."""
    return len(text) * 6 * scale - scale


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = color[0]
            self.px[i + 1] = color[1]
            self.px[i + 2] = color[2]

    def get(self, x, y):
        i = (y * self.w + x) * 3
        return (self.px[i], self.px[i + 1], self.px[i + 2])

    def blend(self, x, y, color, alpha):
        """Alpha-blend color over the pixel at x, y (alpha 0..1)."""
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            for c in range(3):
                base = self.px[i + c]
                self.px[i + c] = int(base + (color[c] - base) * alpha)

    def fill_rect(self, x, y, w, h, color):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = color[0]
                self.px[i + 1] = color[1]
                self.px[i + 2] = color[2]

    def rect(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def line(self, x0, y0, x1, y1, color):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.set(x0, y0, color)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def thick_line(self, x0, y0, x1, y1, color, t=2):
        self.line(x0, y0, x1, y1, color)
        for k in range(1, t):
            self.line(x0, y0 + k, x1, y1 + k, color)

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def circle(self, cx, cy, r, color, t=1):
        # Outline by sampling the circumference.
        steps = max(24, r * 6)
        prev = None
        for s in range(steps + 1):
            a = 2 * 3.141592653589793 * s / steps
            x = int(cx + r * _cos(a) + 0.5)
            y = int(cy + r * _sin(a) + 0.5)
            if prev is not None:
                self.line(prev[0], prev[1], x, y, color)
            prev = (x, y)

    def fill_poly(self, pts, color):
        """Scanline polygon fill; pts is a list of (x, y) in order."""
        if len(pts) < 3:
            return
        ys = sorted(p[1] for p in pts)
        for y in range(max(0, ys[0]), min(self.h, ys[-1] + 1)):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    if y1 != y0:
                        x = x0 + (y - y0) * (x1 - x0) / (y1 - y0)
                        xs.append(x)
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = int(xs[k] + 0.5)
                xb = int(xs[k + 1] + 0.5)
                if xb > xa:
                    self.fill_rect(xa, y, xb - xa, 1, color)

    def poly_line(self, pts, color):
        n = len(pts)
        for i in range(n):
            self.line(pts[i][0], pts[i][1], pts[(i + 1) % n][0],
                      pts[(i + 1) % n][1], color)

    def text(self, x, y, s, color, scale, align="left"):
        """Draw text; x is left edge (align left) or centre (align center)."""
        if align == "center":
            x = x - text_width(s, scale) // 2
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[" "])
            for row in range(7):
                bits = glyph[row]
                for col in range(5):
                    if bits[col] == "1":
                        self.fill_rect(cx + col * scale, y + row * scale,
                                       scale, scale, color)
            cx += 6 * scale

    def text_lines(self, lines, cx, y0, scale, color, gap=4):
        """Draw centred lines starting at y0; returns y just past last line."""
        y = y0
        for ln in lines:
            self.text(cx, y, ln, color, scale, align="center")
            y += 7 * scale + gap
        return y


def _sin(a):
    # Taylor-free sine via the standard library-free series is overkill;
    # use a small lookup-free approximation: math is stdlib, allowed.
    import math
    return math.sin(a)


def _cos(a):
    import math
    return math.cos(a)


# ---------------------------------------------------------------- PNG
def write_png(canvas, path):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        raw += canvas.px[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", comp)
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


# ---------------------------------------------------------------- background
def draw_background(cv):
    for y in range(H):
        t = y / (H - 1)
        c = tuple(int(BG_TOP[i] + (BG_BOT[i] - BG_TOP[i]) * t) for i in range(3))
        cv.fill_rect(0, y, W, 1, c)
    # Deterministic starfield: fixed-seed LCG, no random module.
    seed = 1234567
    for _ in range(170):
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        x = seed % W
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        y = seed % H
        seed = (seed * 1103515245 + 12345) & 0x7FFFFFFF
        b = 90 + (seed % 140)
        cv.set(x, y, (b, b, min(255, b + 20)))
        if seed % 5 == 0:
            cv.set(x + 1, y, (b // 2, b // 2, b // 2))
            cv.set(x, y + 1, (b // 2, b // 2, b // 2))


# ---------------------------------------------------------------- Earth
EARTH_CX, EARTH_CY, EARTH_R = 512, 389, 152

# Simplified continents, as (dx, dy) offsets from the Earth centre.
CONTINENTS = [
    # North America
    [(-138, -62), (-108, -98), (-70, -88), (-58, -58), (-72, -38),
     (-98, -22), (-118, -18), (-142, -38)],
    # Greenland
    [(-82, -112), (-58, -112), (-62, -96), (-82, -98)],
    # South America
    [(-96, 8), (-68, 2), (-54, 28), (-58, 72), (-78, 108), (-100, 62)],
    # Africa
    [(2, -28), (34, -46), (58, -22), (56, 28), (34, 74), (6, 58),
     (-14, 18), (-8, -12)],
    # Europe
    [(2, -78), (30, -90), (52, -66), (40, -52), (12, -56), (-2, -62)],
    # Asia
    [(54, -88), (118, -96), (148, -58), (142, -22), (112, -2),
     (88, -18), (64, -48)],
    # Australia
    [(108, 56), (146, 52), (152, 82), (118, 92), (104, 72)],
]


def draw_earth(cv):
    cx, cy, r = EARTH_CX, EARTH_CY, EARTH_R
    # Glow: concentric rings fading into the background.
    for k in range(16, 0, -1):
        cv.circle(cx, cy, r + k, (30, 80, 150), 1)
        # soften by blending a ring of dots is expensive; use alpha blend
        # on the circle outline via a second pass at low alpha.
        steps = max(24, (r + k) * 6)
        for s in range(steps):
            a = 2 * 3.141592653589793 * s / steps
            x = int(cx + (r + k) * _cos(a) + 0.5)
            y = int(cy + (r + k) * _sin(a) + 0.5)
            cv.blend(x, y, (40, 110, 200), 0.10)
    cv.fill_circle(cx, cy, r, OCEAN)
    # Ocean shading: darker toward the lower edge.
    for dy in range(0, r + 1, 2):
        dx = int((r * r - dy * dy) ** 0.5)
        cv.fill_rect(cx - dx, cy + dy, 2 * dx + 1, 1, OCEAN_DK)
    # Graticule: latitude chords and longitude ellipses, clipped by the disc.
    for lat in (-60, -30, 0, 30, 60):
        yy = cy + int(r * _sin(lat * 3.141592653589793 / 180.0))
        half = int((r * r - (yy - cy) ** 2) ** 0.5)
        cv.line(cx - half, yy, cx + half, yy, GRID)
    for lon in (30, 60, 120):
        rx = int(r * _cos(lon * 3.141592653589793 / 180.0))
        if rx < 4:
            continue
        prev = None
        for s in range(73):
            a = 3.141592653589793 * s / 36.0
            x = int(cx + rx * _cos(a) + 0.5)
            y = int(cy + r * _sin(a) + 0.5)
            if prev is not None:
                cv.line(prev[0], prev[1], x, y, GRID)
            prev = (x, y)
    cv.line(cx, cy - r, cx, cy + r, GRID)
    # Continents.
    for poly in CONTINENTS:
        pts = [(cx + dx, cy + dy) for dx, dy in poly]
        cv.fill_poly(pts, LAND)
    # A few highland patches for texture.
    cv.fill_poly([(cx + 30, cy - 20), (cx + 52, cy - 30), (cx + 58, cy - 8),
                  (cx + 38, cy + 2)], LAND2)
    cv.fill_poly([(cx + 88, cy - 60), (cx + 118, cy - 66),
                  (cx + 122, cy - 40), (cx + 96, cy - 38)], LAND2)
    cv.fill_poly([(cx - 118, cy - 70), (cx - 92, cy - 78),
                  (cx - 80, cy - 52), (cx - 104, cy - 46)], LAND2)
    # Polar ice caps.
    cv.fill_poly([(cx - 62, cy - r + 4), (cx + 62, cy - r + 4),
                  (cx + 40, cy - r + 26), (cx - 40, cy - r + 26)], ICE)
    cv.fill_poly([(cx - 46, cy + r - 24), (cx + 46, cy + r - 24),
                  (cx + 62, cy + r - 4), (cx - 62, cy + r - 4)], ICE)
    # Trade arcs: gold routes across the globe.
    arcs = [((-118, -52), (30, -66)), ((-72, 30), (118, 62)),
            ((-96, -30), (96, -30)), ((-40, 60), (60, 40))]
    for (ax, ay), (bx, by) in arcs:
        mx, my = (ax + bx) // 2, min(ay, by) - 42
        prev = None
        for s in range(41):
            t = s / 40.0
            x = int((1 - t) ** 2 * ax + 2 * (1 - t) * t * mx + t * t * bx)
            y = int((1 - t) ** 2 * ay + 2 * (1 - t) * t * my + t * t * by)
            px, py = cx + x, cy + y
            if (px - cx) ** 2 + (py - cy) ** 2 <= (r - 3) ** 2:
                if prev is not None:
                    cv.line(prev[0], prev[1], px, py, GOLD)
                prev = (px, py)
            else:
                prev = None
        for (dx, dy) in ((ax, ay), (bx, by)):
            cv.fill_circle(cx + dx, cy + dy, 4, GOLD)
            cv.fill_circle(cx + dx, cy + dy, 2, WHITE)
    cv.circle(cx, cy, r, SKY, 2)


# ---------------------------------------------------------------- masthead
def draw_masthead(cv):
    cv.text(512, 14, "THE WORLD AT A CROSSROADS", WHITE, 4, align="center")
    cv.text(512, 56, "TUESDAY 24 NOVEMBER 2026", GOLD, 3, align="center")
    # Gold rule with end diamonds.
    cv.fill_rect(120, 96, 784, 3, GOLD)
    for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (-1, 0), (0, -1),
                   (2, 0), (0, 2), (-2, 0), (0, -2)):
        cv.set(112 + dx, 97 + dy, GOLD)
        cv.set(912 + dx, 97 + dy, GOLD)


# ---------------------------------------------------------------- motifs
# Each motif draws a small scene inside (x, y, w, h) — the motif area of
# its panel. All motifs are simple bold shapes, drawn, never pasted.

def motif_scales(cv, x, y, w, h):
    cx = x + w // 2
    top = y + 8
    base = y + h - 14
    # Beam, post, base.
    cv.fill_rect(cx - 64, top + 16, 128, 5, GOLD)
    cv.fill_rect(cx - 3, top + 16, 6, base - top - 16, GOLD)
    cv.fill_rect(cx - 40, base - 5, 80, 5, GOLD)
    # Chains and pans.
    for sx in (-64, 64):
        cv.line(cx + sx, top + 21, cx + sx, top + 48, GOLD)
        cv.fill_poly([(cx + sx - 30, top + 48), (cx + sx + 30, top + 48),
                      (cx + sx, top + 76)], GOLD)
    # Centre finial.
    cv.fill_circle(cx, top + 8, 5, GOLD)


def motif_satellite(cv, x, y, w, h):
    cx = x + w // 2
    cy = y + h // 2 - 4
    # Shield ring behind, scaled to the motif height.
    r = min(52, h // 2 - 8)
    if r < 14:
        r = 14
    cv.circle(cx, cy, r, BLUE, 2)
    cv.circle(cx, cy, max(10, r - 6), (60, 110, 180), 1)
    # Solar panels.
    cv.fill_rect(cx - 92, cy - 10, 52, 20, BLUE)
    cv.fill_rect(cx + 40, cy - 10, 52, 20, BLUE)
    cv.rect(cx - 92, cy - 10, 52, 20, SKY, 1)
    cv.rect(cx + 40, cy - 10, 52, 20, SKY, 1)
    cv.line(cx - 66, cy - 10, cx - 66, cy + 10, SKY)
    cv.line(cx + 66, cy - 10, cx + 66, cy + 10, SKY)
    # Body and dish.
    cv.fill_rect(cx - 40, cy - 14, 80, 28, DIM)
    cv.rect(cx - 40, cy - 14, 80, 28, WHITE, 2)
    cv.fill_rect(cx - 10, cy - 5, 20, 10, GOLD)
    cv.line(cx + 40, cy - 14, cx + 58, cy - 30, WHITE)
    cv.fill_circle(cx + 60, cy - 32, 4, RED)
    # Small shield badge below, only when the motif is tall enough.
    if h >= 100:
        bx, by = cx, cy + 50
        cv.fill_poly([(bx - 16, by - 12), (bx + 16, by - 12),
                      (bx + 16, by + 2), (bx, by + 16), (bx - 16, by + 2)],
                     TEAL)
        cv.text(bx, by - 8, "N", WHITE, 1, align="center")


def motif_ships_un(cv, x, y, w, h):
    cx = x + w // 2
    sea = y + h - 14
    # UN flag: blue field, white disc.
    fx, fy = cx - 20, y + 4
    cv.fill_rect(fx, fy, 40, 24, (40, 110, 210))
    cv.rect(fx, fy, 40, 24, WHITE, 1)
    cv.fill_circle(fx + 20, fy + 12, 7, WHITE)
    cv.fill_circle(fx + 20, fy + 12, 4, (40, 110, 210))
    # Two ships facing each other below the flag.
    for sx, flag_col in ((-82, RED), (26, GOLD)):
        hx = cx + sx
        cv.fill_poly([(hx, sea), (hx + 64, sea), (hx + 56, sea - 12),
                      (hx + 8, sea - 12)], DIM)
        cv.fill_rect(hx + 22, sea - 24, 7, 12, DIM)
        cv.fill_rect(hx + 36, sea - 24, 7, 12, DIM)
        cv.line(hx + 25, sea - 24, hx + 25, sea - 34, WHITE)
        cv.fill_poly([(hx + 25, sea - 34), (hx + 39, sea - 30),
                      (hx + 25, sea - 26)], flag_col)
    # Sea lines.
    cv.fill_rect(x + 10, sea + 4, w - 20, 2, BLUE)
    cv.fill_rect(x + 10, sea + 9, w - 20, 2, GRID)


def motif_strait(cv, x, y, w, h):
    cx = x + w // 2
    # Two headlands with a narrow channel between them.
    top = y + 6
    bot = y + h - 10
    cv.fill_poly([(x + 8, top), (x + 88, top), (x + 76, bot),
                  (x + 8, bot)], LAND)
    cv.fill_poly([(x + w - 88, top), (x + w - 8, top),
                  (x + w - 8, bot), (x + w - 76, bot)], LAND)
    # Water channel.
    cv.fill_rect(cx - 22, top, 44, bot - top, OCEAN)
    cv.fill_rect(cx - 22, top, 44, 3, SKY)
    # Warning triangle above the channel.
    tx, ty = cx, top + 2
    cv.fill_poly([(tx, ty - 2), (tx + 9, ty + 12), (tx - 9, ty + 12)], GOLD)
    cv.text(tx, ty + 4, "!", (10, 10, 20), 1, align="center")
    # One small ship in the channel below the warning.
    sy = bot - 6
    cv.fill_poly([(cx - 18, sy), (cx + 18, sy), (cx + 12, sy - 9),
                  (cx - 12, sy - 9)], DIM)
    cv.fill_rect(cx - 3, sy - 17, 6, 8, DIM)


def motif_cop(cv, x, y, w, h):
    cx = x + w // 2
    # Smokestacks left, conference table right, split down the middle.
    # All heights scale with the motif height.
    stack_h = max(18, h - 44)
    stop = y + 16
    for sx in (x + 26, x + 52):
        cv.fill_rect(sx, stop, 16, stack_h, DIM)
        cv.fill_rect(sx - 2, stop - 6, 20, 8, DIM)
        cv.fill_circle(sx + 8, stop - 8, 4, DIM)
        cv.fill_circle(sx + 16, stop - 14, 3, DIM)
    # Long table with a crack in the middle.
    ty = y + h - 16
    cv.fill_rect(x + 96, ty, 84, 10, (150, 110, 70))
    cv.fill_rect(x + 188, ty, 84, 10, (150, 110, 70))
    # Delegates: heads and shoulders, split colours, seated at the table.
    for k in range(4):
        hx = x + 112 + k * 40
        col = GREEN if k < 2 else CORAL
        cv.fill_rect(hx - 9, ty - 6, 18, 6, col)
        cv.fill_circle(hx, ty - 14, 8, col)
    cv.fill_rect(x + 96, ty + 10, 176, 4, DIM)
    # Crack marker: red X between the halves.
    cv.line(cx - 8, ty - 26, cx + 8, ty - 10, RED)
    cv.line(cx + 8, ty - 26, cx - 8, ty - 10, RED)


def motif_gaza(cv, x, y, w, h):
    cx = x + w // 2
    base = y + h - 12
    # Skyline: damaged buildings, heights scaled to the motif height.
    heights = [int(h * f) for f in (0.45, 0.62, 0.38, 0.55, 0.48)]
    bw = 34
    bx = cx - len(heights) * bw // 2
    tops = []
    for k, hh in enumerate(heights):
        xx = bx + k * bw
        tops.append(base - hh)
        cv.fill_rect(xx + 3, base - hh, bw - 6, hh, DIM)
        cv.rect(xx + 3, base - hh, bw - 6, hh, (90, 105, 130), 1)
        # Broken roofline on two buildings.
        if k in (1, 3):
            cv.fill_poly([(xx + 3, base - hh), (xx + 16, base - hh - 8),
                          (xx + bw - 3, base - hh)], (10, 14, 28))
        # Windows.
        for wy in range(base - hh + 10, base - 10, 16):
            cv.fill_rect(xx + 10, wy, 6, 8, GOLD_DIM)
            cv.fill_rect(xx + 20, wy, 6, 8, GOLD_DIM)
    # Smoke puffs hugging the rooftops, strictly inside the motif area.
    for k in (0, 1, 3):
        sx = bx + k * bw + bw // 2
        top = tops[k]
        cv.fill_circle(sx, top - 5, 3, (120, 125, 135))
        cv.fill_circle(sx + 5, top - 9, 3, (100, 105, 118))
    # Ground line.
    cv.fill_rect(x + 10, base, w - 20, 3, CORAL)


def motif_chip(cv, x, y, w, h):
    cx = x + w // 2
    cy = y + h // 2
    # Chip body with pins, scaled to the motif height (pins stay inside).
    s = min(44, h // 2 - 4)
    pin = max(2, h // 2 - s)
    cv.fill_rect(cx - s, cy - s, 2 * s, 2 * s, (28, 44, 66))
    cv.rect(cx - s, cy - s, 2 * s, 2 * s, TEAL, 3)
    step = max(6, s // 3)
    for k in range(-2, 3):
        off = k * step
        cv.fill_rect(cx + off - 2, cy - s - pin, 4, pin, TEAL)
        cv.fill_rect(cx + off - 2, cy + s, 4, pin, TEAL)
        cv.fill_rect(cx - s - pin, cy + off - 2, pin, 4, TEAL)
        cv.fill_rect(cx + s, cy + off - 2, pin, 4, TEAL)
    d = int(s * 0.6)
    cv.fill_rect(cx - d, cy - d, 2 * d, 2 * d, (16, 28, 46))
    cv.rect(cx - d, cy - d, 2 * d, 2 * d, GREEN, 2)
    # Rising market arrow across the die.
    cv.line(cx - d + 4, cy + d - 6, cx - 4, cy + 2, GREEN)
    cv.line(cx - 4, cy + 2, cx + 2, cy + 6, GREEN)
    cv.line(cx + 2, cy + 6, cx + d - 4, cy - d + 6, GREEN)
    cv.fill_poly([(cx + d - 4, cy - d + 6), (cx + d - 12, cy - d + 6),
                  (cx + d - 4, cy - d + 14)], GREEN)
    cv.text(cx, cy + d + 2, "N", GREEN, 1, align="center")


def motif_phone(cv, x, y, w, h):
    cx = x + w // 2
    # Phone, centred, with a warning on its screen.
    pw, ph = 54, h - 14
    px, py = cx - pw // 2, y + 7
    cv.fill_rect(px, py, pw, ph, (28, 44, 66))
    cv.rect(px, py, pw, ph, SKY, 2)
    cv.fill_rect(px + 6, py + 8, pw - 12, ph - 22, (16, 28, 46))
    # Warning triangle on the screen.
    tx, ty = cx, py + 12
    cv.fill_poly([(tx, ty), (tx + 10, ty + 16), (tx - 10, ty + 16)], GOLD)
    cv.text(tx, ty + 6, "!", (10, 10, 20), 1, align="center")
    cv.fill_rect(px + 14, py + ph - 8, pw - 28, 3, DIM)
    # Gavel leaning on the phone's right side.
    gx, gy = px + pw + 4, py + ph - 18
    cv.thick_line(gx, gy, gx + 26, gy - 20, (150, 110, 70), 2)
    cv.fill_rect(gx + 22, gy - 26, 12, 10, (150, 110, 70))


def motif_drone_cuffs(cv, x, y, w, h):
    cx = x + w // 2
    # Quadcopter drone.
    dy = y + 12
    cv.fill_rect(cx - 16, dy - 5, 32, 10, DIM)
    cv.rect(cx - 16, dy - 5, 32, 10, WHITE, 1)
    for sx in (-30, 30):
        cv.line(cx + sx - 14, dy - 8, cx + sx + 14, dy - 8, SKY)
        cv.fill_circle(cx + sx, dy - 8, 3, SKY)
        arm_x = cx - 16 if sx < 0 else cx + 16
        cv.line(cx + sx - 8, dy - 5, arm_x, dy - 2, DIM)
    cv.fill_circle(cx, dy, 3, RED)
    # Handcuffs below.
    hy = y + h - 16
    for sx in (-26, 26):
        cv.circle(cx + sx, hy, 10, GOLD, 2)
    cv.line(cx - 16, hy - 6, cx + 16, hy - 6, GOLD)
    cv.line(cx - 16, hy + 6, cx + 16, hy + 6, GOLD)


def motif_island_pact(cv, x, y, w, h):
    cx = x + w // 2
    base = y + h - 10
    # Sea and island mound.
    cv.fill_rect(x + 10, base, w - 20, 3, BLUE)
    cv.fill_poly([(cx - 56, base), (cx - 34, base - 16),
                  (cx + 34, base - 16), (cx + 56, base)], LAND)
    # Torn pact: white document with a red jagged tear down the middle.
    dx, dy = cx - 30, y + 4
    dw, dh = 60, 26
    cv.fill_rect(dx, dy, dw, dh, WHITE)
    cv.rect(dx, dy, dw, dh, DIM, 1)
    for k in range(3):
        cv.fill_rect(dx + 5, dy + 5 + k * 7, 14, 2, DIM)
        cv.fill_rect(dx + 41, dy + 5 + k * 7, 14, 2, DIM)
    cv.line(dx + 30, dy, dx + 24, dy + 9, RED)
    cv.line(dx + 24, dy + 9, dx + 32, dy + 17, RED)
    cv.line(dx + 32, dy + 17, dx + 26, dy + 26, RED)


def motif_clinic(cv, x, y, w, h):
    cx = x + w // 2
    base = y + h - 10
    # Clinic tent.
    cv.fill_poly([(cx - 44, base), (cx - 30, base - 30), (cx + 30, base - 30),
                  (cx + 44, base)], WHITE)
    cv.poly_line([(cx - 44, base), (cx - 30, base - 30), (cx + 30, base - 30),
                  (cx + 44, base)], DIM)
    # Red cross on the tent.
    cv.fill_rect(cx - 4, base - 26, 8, 18, RED)
    cv.fill_rect(cx - 9, base - 21, 18, 8, RED)
    # Door.
    cv.fill_rect(cx - 7, base - 12, 14, 12, (10, 14, 28))
    # Map pin above the tent's right side.
    px, py = cx + 48, y + 12
    cv.fill_circle(px, py, 7, RED)
    cv.fill_circle(px, py, 3, WHITE)
    cv.fill_poly([(px - 6, py + 4), (px + 6, py + 4), (px, py + 14)], RED)


def motif_quake(cv, x, y, w, h):
    cx = x + w // 2
    base = y + h - 12
    # Mountain range.
    cv.fill_poly([(x + 8, base), (x + 52, base - 28), (x + 92, base)], LAND2)
    cv.fill_poly([(x + 62, base), (x + 112, base - 36), (x + 158, base)],
                 LAND)
    cv.fill_poly([(x + 128, base), (x + 152, base - 22), (x + 172, base)],
                 LAND2)
    # Snow cap on the tallest peak.
    cv.fill_poly([(x + 112, base - 36), (x + 104, base - 26),
                  (x + 120, base - 26)], ICE)
    # Seismograph trace across the sky.
    trace_y = y + 6
    pts = []
    for k, amp in enumerate((0, 2, -3, 5, -6, 3, -2, 0)):
        pts.append((x + 14 + k * 20, trace_y + amp))
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], RED)


def motif_virus(cv, x, y, w, h):
    cx = x + w // 2
    cy = y + h // 2 + 2
    # Virus body with spikes, left of centre.
    vx = cx - 24
    r = 16
    for k in range(8):
        a = 2 * 3.141592653589793 * k / 8
        sx = int(vx + (r + 7) * _cos(a) + 0.5)
        sy = int(cy + (r + 7) * _sin(a) + 0.5)
        cv.line(vx + int(r * _cos(a) + 0.5), cy + int(r * _sin(a) + 0.5),
                sx, sy, RED)
        cv.fill_circle(sx, sy, 2, RED)
    cv.fill_circle(vx, cy, r, CORAL)
    cv.fill_circle(vx - 5, cy - 4, 3, RED)
    cv.fill_circle(vx + 5, cy + 3, 3, RED)
    # Falling chart line to the right: elimination status lost.
    cv.line(cx + 4, cy - 20, cx + 32, cy - 2, GOLD)
    cv.line(cx + 32, cy - 2, cx + 72, cy + 14, GOLD)
    cv.fill_poly([(cx + 72, cy + 14), (cx + 62, cy + 14),
                  (cx + 72, cy + 24)], GOLD)


# ---------------------------------------------------------------- panels
# PANELS REGISTRY — Builder 2: append dicts here to add panels 8-16.
#   key: short id. x, y, w, h: panel rect. accent: top bar colour.
#   motif: function(cv, x, y, w, h) drawing the scene in the motif area.
#   motif_h: height of the motif area. title: headline lines (scale given).
#   sub: fact lines. title_scale / sub_scale: integer font scales.
#   title_gap / sub_gap: extra pixels between lines (default 4 / 3).
# Geometry rules: title line width = len * 6 * scale - scale must fit
# w - 16; same for sub lines. Every label must name its place.
LAYOUT = {
    "masthead_h": 118,
    "middle_y": 130,
    "middle_h": 430,
    "bottom_y": 572,
    "bottom_h": 378,
    "footer_y": 954,
}

PANELS = [
    {
        "key": "hero_icj_myanmar",
        "x": 16, "y": 130, "w": 294, "h": 430, "accent": GOLD,
        "motif": motif_scales, "motif_h": 200,
        "title": ["ICJ FINDS", "MYANMAR GUILTY", "OF GENOCIDE"],
        "title_scale": 3,
        "sub": ["ROHINGYA 2017", "FIRST STATE FOUND", "RESPONSIBLE",
                "RULING 9-6", "14 NATIONS BACK IT"],
        "sub_scale": 2,
    },
    {
        "key": "nato_space",
        "x": 714, "y": 130, "w": 294, "h": 212, "accent": BLUE,
        "motif": motif_satellite, "motif_h": 84,
        "title": ["NATO VOWS TO", "DEFEND SPACE"],
        "title_scale": 2,
        "sub": ["RUSSIA MAY LAUNCH", "NUCLEAR SATELLITE", "WITHIN 60 DAYS"],
        "sub_scale": 2,
    },
    {
        "key": "cop31",
        "x": 714, "y": 354, "w": 294, "h": 206, "accent": GREEN,
        "motif": motif_cop, "motif_h": 80,
        "title": ["COP31 ENDS", "WITHOUT A DEAL"],
        "title_scale": 2,
        "sub": ["FOSSIL FUELS AND", "FINANCE DIVIDE", "THE SUMMIT"],
        "sub_scale": 2,
    },
    {
        "key": "libya_ships",
        "x": 18, "y": 572, "w": 188, "h": 183, "accent": GOLD,
        "motif": motif_ships_un, "motif_h": 56,
        "title": ["UKRAINE HITS", "LIBYA SHIPS"],
        "title_scale": 2,
        "sub": ["UN PROBE", "TRIPOLI WANTS", "ANSWERS"],
        "sub_scale": 2,
    },
    {
        "key": "hormuz",
        "x": 218, "y": 572, "w": 188, "h": 183, "accent": RED,
        "motif": motif_strait, "motif_h": 56,
        "title": ["RECORD IRANIAN", "ATTACKS"],
        "title_scale": 2,
        "sub": ["STRAIT OF", "HORMUZ", "TENSIONS RISE"],
        "sub_scale": 2,
    },
    {
        "key": "gaza",
        "x": 418, "y": 572, "w": 188, "h": 183, "accent": CORAL,
        "motif": motif_gaza, "motif_h": 48,
        "title": ["GAZA STRIKES", "KILL AT LEAST", "SIX"],
        "title_scale": 2,
        "sub": ["UN: 77 YEARS", "UNDONE"],
        "sub_scale": 2,
    },
    {
        "key": "nvidia",
        "x": 618, "y": 572, "w": 188, "h": 183, "accent": TEAL,
        "motif": motif_chip, "motif_h": 56,
        "title": ["HUANG IS BACK", "AS NVIDIA CEO"],
        "title_scale": 2,
        "sub": ["MARKET SURGES", "SHARES JUMP"],
        "sub_scale": 2,
    },
    {
        "key": "grok_suits",
        "x": 818, "y": 572, "w": 188, "h": 183, "accent": PURPLE,
        "motif": motif_phone, "motif_h": 56,
        "title": ["STATES SUE", "GROK IMAGES"],
        "title_scale": 2,
        "sub": ["OREGON AND", "VIRGINIA SUE", "SPACEX"],
        "sub_scale": 2,
    },
    {
        "key": "el_chapo_isidro",
        "x": 18, "y": 767, "w": 188, "h": 183, "accent": GOLD,
        "motif": motif_drone_cuffs, "motif_h": 56,
        "title": ["CHAPO ISIDRO", "CAPTURED"],
        "title_scale": 2,
        "sub": ["US DRONE AID", "SINALOA RAID"],
        "sub_scale": 2,
    },
    {
        "key": "solomon_islands",
        "x": 218, "y": 767, "w": 188, "h": 183, "accent": GREEN,
        "motif": motif_island_pact, "motif_h": 48,
        "title": ["SOLOMON", "ISLANDS END", "CHINA PACT"],
        "title_scale": 2,
        "sub": ["SECURITY PACT", "ENDS"],
        "sub_scale": 2,
    },
    {
        "key": "drc_ebola",
        "x": 418, "y": 767, "w": 188, "h": 183, "accent": RED,
        "motif": motif_clinic, "motif_h": 48,
        "title": ["DRC FIGHTING", "TRAPS EBOLA", "RESPONDERS"],
        "title_scale": 2,
        "sub": ["WHO: ITURI", "CLASHES"],
        "sub_scale": 2,
    },
    {
        "key": "nepal_quake",
        "x": 618, "y": 767, "w": 188, "h": 183, "accent": CORAL,
        "motif": motif_quake, "motif_h": 56,
        "title": ["NEPAL M5.6", "QUAKE"],
        "title_scale": 2,
        "sub": ["NEAR CHINA", "BORDER"],
        "sub_scale": 2,
    },
    {
        "key": "us_measles",
        "x": 818, "y": 767, "w": 188, "h": 183, "accent": PURPLE,
        "motif": motif_virus, "motif_h": 56,
        "title": ["US LOSES", "MEASLES STATUS"],
        "title_scale": 2,
        "sub": ["AFTER 25 YEARS", "9TH DEATH: PA"],
        "sub_scale": 2,
    },
]


def draw_panel(cv, p):
    x, y, w, h = p["x"], p["y"], p["w"], p["h"]
    cv.fill_rect(x, y, w, h, PANEL_BG)
    cv.rect(x, y, w, h, PANEL_EDGE, 2)
    cv.fill_rect(x, y, w, 5, p["accent"])
    cx = x + w // 2
    # Motif area.
    p["motif"](cv, x + 4, y + 10, w - 8, p["motif_h"])
    # Thin divider under the motif.
    div_y = y + 10 + p["motif_h"] + 6
    cv.fill_rect(x + 18, div_y, w - 36, 2, p["accent"])
    # Title, then sub lines.
    ty = div_y + 14
    ty = cv.text_lines(p["title"], cx, ty, p["title_scale"], WHITE,
                       gap=p.get("title_gap", 4))
    ty += 6
    cv.text_lines(p["sub"], cx, ty, p["sub_scale"], GOLD, gap=3)


# ---------------------------------------------------------------- footer ticker
FOOTER_LINES = [
    "UK SANCTIONS MYANMAR GENERALS  -  GERMANY GAINS UKRAINE DELTA "
    "ACCESS  -  TIANGONG HOSTS FIRST FOREIGN ASTRONAUT",
    "SANOFI BUYS INSMED FOR $41B  -  FDA APPROVES FIRST LIMB-GIRDLE "
    "DRUG  -  MOST DISTANT BLACK HOLE FOUND",
    "WARS THREATEN FOOD AID FOR 7.3M MORE  -  47,000 WOMEN KILLED BY "
    "PARTNERS IN 2025  -  NETANYAHU PUSHES TRUMP ON IRAN  -  IRAQ PM "
    "TAKES OVER KURD OILFIELDS",
]


def draw_footer(cv):
    y = LAYOUT["footer_y"]
    cv.text(512, y, "ALSO ON 24 NOVEMBER 2026", GOLD, 1, align="center")
    yy = y + 14
    for ln in FOOTER_LINES:
        cv.text(512, yy, ln, DIM, 1, align="center")
        yy += 10
    cv.text(512, yy + 4, "SOURCES: BBC - REUTERS - AL JAZEERA - AP - "
            "THE HINDU - USGS", (110, 120, 140), 1, align="center")


# ---------------------------------------------------------------- main
def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H)
    draw_background(cv)
    draw_masthead(cv)
    draw_earth(cv)
    for p in sorted(PANELS, key=lambda d: (d["y"], d["x"])):
        draw_panel(cv, p)
    draw_footer(cv)
    path = os.path.join(out_dir, "entry.png")
    n = write_png(cv, path)
    print("wrote %s (%d bytes)" % (path, n))


if __name__ == "__main__":
    main()

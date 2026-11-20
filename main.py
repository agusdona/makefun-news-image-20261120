#!/usr/bin/env python3
"""Three Powers, One Table - news-image-20261120.

Sum up 20 November 2026 world news in one 1024x1024 editorial poster.
Pure standard library only. No network, no file reads, deterministic.
Draws everything procedurally onto an RGB buffer and encodes PNG by hand
(zlib + struct, filter 0 per scanline).
Run: python3 main.py  ->  writes /output/entry.png
"""
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
NAVY = (10, 24, 48)
NAVY2 = (19, 42, 77)
NAVY3 = (14, 33, 64)
DARK = (8, 18, 36)
GOLD = (212, 175, 55)
GOLD_L = (242, 201, 76)
WHITE = (255, 255, 255)
OFFWHITE = (248, 245, 238)
INK = (16, 28, 52)
RED = (185, 28, 28)
RED_L = (220, 38, 38)
BLUE = (29, 78, 216)
TEAL = (14, 116, 144)
AMBER = (180, 83, 9)
PURPLE = (124, 58, 237)
SKIN = (232, 184, 138)
SKIN2 = (214, 164, 120)
HAIR = (30, 30, 34)
WOOD = (166, 124, 82)
WOOD_D = (107, 68, 35)
GREY = (45, 55, 72)

buf = bytearray(W * H * 3)


def set_px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i] = c[0]
        buf[i + 1] = c[1]
        buf[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            buf[i] = c[0]
            buf[i + 1] = c[1]
            buf[i + 2] = c[2]


def rect_border(x, y, w, h, t, c):
    fill_rect(x, y, w, t, c)
    fill_rect(x, y + h - t, w, t, c)
    fill_rect(x, y, t, h, c)
    fill_rect(x + w - t, y, t, h, c)


def vgrad(x, y, w, h, c1, c2):
    for yy in range(h):
        t = yy / max(1, h - 1)
        c = (int(c1[0] + (c2[0] - c1[0]) * t),
             int(c1[1] + (c2[1] - c1[1]) * t),
             int(c1[2] + (c2[2] - c1[2]) * t))
        fill_rect(x, y + yy, w, 1, c)


def fill_circle(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        fill_rect(cx - dx, cy + dy, dx * 2 + 1, 1, c)


def circle_outline(cx, cy, r, c, t=3):
    for a in range(360):
        import math as _m
        x = int(cx + r * _m.cos(_m.radians(a)))
        y = int(cy + r * _m.sin(_m.radians(a)))
        fill_circle(x, y, t // 2 + 1, c)


def fill_ellipse(cx, cy, rx, ry, c):
    for dy in range(-ry, ry + 1):
        t = 1.0 - (dy * dy) / float(ry * ry)
        dx = int(rx * (t ** 0.5)) if t > 0 else 0
        fill_rect(cx - dx, cy + dy, dx * 2 + 1, 1, c)


def draw_line(x0, y0, x1, y1, c, thick=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        if thick <= 1:
            set_px(x, y, c)
        else:
            fill_circle(x, y, thick // 2, c)
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


def fill_polygon(points, c):
    # scanline fill
    ys = [p[1] for p in points]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / float(y1 - y0)
                xs.append(int(x0 + t * (x1 - x0)))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            fill_rect(xs[i], y, xs[i + 1] - xs[i] + 1, 1, c)


def draw_star(cx, cy, r, c):
    import math as _m
    pts = []
    for i in range(10):
        ang = -_m.pi / 2 + i * _m.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((int(cx + rr * _m.cos(ang)), int(cy + rr * _m.sin(ang))))
    fill_polygon(pts, c)


# ---------------------------------------------------------------- 5x7 font
# Each glyph: 7 rows of 5 chars, '#' = ink.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "01010", "00000", "00000", "00000", "00000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '@': ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '*': ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    # bullet (middle dot)
    '\u2022': ("00000", "00000", "00100", "01110", "01110", "00100", "00000"),
}


def norm_char(ch):
    if ch == '\u2014' or ch == '\u2013':
        return '-'
    if ch == '\u2019' or ch == '\u2018':
        return "'"
    if ch == '\u201c' or ch == '\u201d':
        return '"'
    return ch.upper()


def text_width(text, scale):
    w = 0
    for ch in text:
        w += 6 * scale
    return w - scale if w else 0


def draw_char(x, y, ch, scale, color):
    g = FONT.get(norm_char(ch))
    if g is None:
        return
    for r in range(7):
        row = g[r]
        for c in range(5):
            if row[c] == '1':
                fill_rect(x + c * scale, y + r * scale, scale, scale, color)


def draw_text(x, y, text, scale, color):
    cx = x
    for ch in text:
        draw_char(cx, y, ch, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(cx, y, text, scale, color):
    x = cx - text_width(text, scale) // 2
    draw_text(x, y, text, scale, color)


def wrap_lines(text, scale, max_w):
    words = text.split(' ')
    lines = []
    cur = ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped_centered(cx, y, text, scale, color, max_w, line_h):
    lines = wrap_lines(text, scale, max_w)
    for i, ln in enumerate(lines):
        draw_text_centered(cx, y + i * line_h, ln, scale, color)
    return y + len(lines) * line_h


# ---------------------------------------------------------------- flags
def flag_usa(x, y, w, h):
    # 7 stripes
    sh = h // 7
    for i in range(7):
        c = RED_L if i % 2 == 0 else WHITE
        fill_rect(x, y + i * sh, w, sh + 1, c)
    cw, ch = int(w * 0.42), sh * 4
    fill_rect(x, y, cw, ch, (30, 50, 110))
    for r in range(3):
        for cc in range(4):
            fill_circle(x + 8 + cc * 11, y + 8 + r * 10, 2, WHITE)


def flag_china(x, y, w, h):
    fill_rect(x, y, w, h, (222, 41, 16))
    draw_star(x + 26, y + 22, 13, (255, 222, 0))
    for sx, sy in ((58, 12), (72, 22), (72, 38), (58, 48)):
        draw_star(x + sx, y + sy, 6, (255, 222, 0))


def flag_russia(x, y, w, h):
    bh = h // 3
    fill_rect(x, y, w, bh + 1, WHITE)
    fill_rect(x, y + bh, w, bh + 1, (0, 57, 166))
    fill_rect(x, y + 2 * bh, w, h - 2 * bh, (213, 43, 30))


def draw_flag(x, y, w, h, kind):
    rect_border(x, y, w, h, 2, GOLD)
    if kind == 'usa':
        flag_usa(x + 2, y + 2, w - 4, h - 4)
    elif kind == 'chn':
        flag_china(x + 2, y + 2, w - 4, h - 4)
    else:
        flag_russia(x + 2, y + 2, w - 4, h - 4)
    # pole
    draw_line(x + w // 2, y + h, x + w // 2, y + h + 14, GOLD, 3)
    fill_circle(x + w // 2, y - 4, 4, GOLD_L)


# ---------------------------------------------------------------- figures
def draw_person(cx, head_y, suit, skin):
    # body (trapezoid)
    fill_polygon([(cx - 52, head_y + 118), (cx + 52, head_y + 118),
                  (cx + 34, head_y + 52), (cx - 34, head_y + 52)], suit)
    # shirt + tie
    fill_polygon([(cx - 12, head_y + 52), (cx + 12, head_y + 52),
                  (cx + 6, head_y + 92), (cx - 6, head_y + 92)], WHITE)
    fill_polygon([(cx - 5, head_y + 54), (cx + 5, head_y + 54),
                  (cx + 4, head_y + 88), (cx - 4, head_y + 88)], RED)
    # head: skin circle + hair cap on top (no band across the face)
    fill_circle(cx, head_y, 26, skin)
    fill_ellipse(cx, head_y - 14, 26, 15, HAIR)


# ---------------------------------------------------------------- icons
def icon_scales(cx, cy):
    # justice scales, navy on light
    draw_line(cx, cy - 34, cx, cy + 30, INK, 4)
    draw_line(cx - 34, cy - 24, cx + 34, cy - 24, INK, 4)
    fill_circle(cx, cy - 36, 5, INK)
    for sx in (cx - 34, cx + 34):
        draw_line(sx, cy - 24, sx - 14, cy + 6, INK, 3)
        draw_line(sx, cy - 24, sx + 14, cy + 6, INK, 3)
        fill_ellipse(sx, cy + 8, 17, 7, INK)
    fill_rect(cx - 22, cy + 30, 44, 6, INK)


def icon_rocket(cx, cy):
    # stars
    for sx, sy in ((cx - 44, cy - 30), (cx + 44, cy - 28), (cx - 38, cy + 26), (cx + 40, cy + 30)):
        draw_star(sx, sy, 5, GOLD)
    # orbit ellipse outline (dots)
    import math as _m
    for a in range(0, 360, 6):
        x = int(cx + 52 * _m.cos(_m.radians(a)))
        y = int(cy + 16 * _m.sin(_m.radians(a)))
        set_px(x, y, BLUE)
        set_px(x + 1, y, BLUE)
    # rocket body
    fill_polygon([(cx, cy - 38), (cx - 13, cy - 2), (cx + 13, cy - 2)], RED)
    fill_rect(cx - 13, cy - 4, 26, 34, WHITE)
    rect_border(cx - 13, cy - 4, 26, 34, 2, INK)
    fill_circle(cx, cy + 8, 7, BLUE)
    fill_polygon([(cx - 13, cy + 22), (cx - 26, cy + 36), (cx - 13, cy + 30)], RED)
    fill_polygon([(cx + 13, cy + 22), (cx + 26, cy + 36), (cx + 13, cy + 30)], RED)
    fill_polygon([(cx - 7, cy + 30), (cx + 7, cy + 30), (cx, cy + 44)], GOLD_L)


def icon_cyclone(cx, cy):
    # spiral: concentric circle outlines
    for r, col in ((34, TEAL), (25, BLUE), (16, TEAL), (8, RED)):
        circle_outline(cx, cy, r, col, 3)
    fill_circle(cx, cy, 5, RED)
    # coastline + waves at bottom
    fill_rect(cx - 48, cy + 34, 96, 10, BLUE)
    draw_line(cx - 48, cy + 34, cx + 48, cy + 34, WHITE, 2)
    # rain drops
    for dx in (-40, -20, 0, 20, 40):
        draw_line(cx + dx, cy - 44, cx + dx - 5, cy - 34, BLUE, 3)


def icon_clock(cx, cy):
    circle_outline(cx, cy, 34, INK, 4)
    fill_circle(cx, cy, 34, WHITE)
    circle_outline(cx, cy, 34, INK, 3)
    draw_line(cx, cy, cx, cy - 22, INK, 4)
    draw_line(cx, cy, cx + 16, cy + 8, INK, 4)
    fill_circle(cx, cy, 4, RED)


def icon_controller(cx, cy):
    fill_rect(cx - 52, cy - 22, 104, 48, INK)
    for ccx, ccy in ((cx - 52, cy - 22), (cx + 52, cy - 22),
                     (cx - 52, cy + 26), (cx + 52, cy + 26)):
        fill_circle(ccx, ccy, 12, INK)
    # d-pad
    fill_rect(cx - 42, cy - 8, 24, 8, WHITE)
    fill_rect(cx - 34, cy - 16, 8, 24, WHITE)
    # buttons
    fill_circle(cx + 30, cy - 10, 5, GOLD_L)
    fill_circle(cx + 42, cy + 2, 5, RED_L)
    fill_circle(cx + 18, cy + 2, 5, (60, 180, 90))


# ---------------------------------------------------------------- scene
def draw_scene():
    fill_rect(0, 0, W, H, NAVY)
    rect_border(0, 0, W, H, 6, GOLD)

    # ---- masthead
    draw_text_centered(512, 20, "THE WORLD IN ONE PICTURE", 6, GOLD_L)
    draw_text_centered(512, 70, "FRIDAY \u2022 20 NOVEMBER 2026", 3, WHITE)
    fill_rect(16, 106, 992, 4, GOLD)

    # ---- hero panel
    vgrad(16, 128, 992, 492, NAVY2, NAVY3)
    rect_border(16, 128, 992, 492, 3, GOLD)

    draw_text_centered(512, 142, "THREE POWERS,", 7, WHITE)
    draw_text_centered(512, 198, "ONE TABLE", 7, GOLD_L)
    fill_rect(412, 252, 200, 3, GOLD)
    draw_text_centered(512, 264, "TRUMP, XI AND PUTIN MEET IN CHINA", 3, WHITE)
    draw_text_centered(512, 290, "NUCLEAR ARMS ON THE AGENDA", 3, GOLD_L)

    # flags
    draw_flag(130, 322, 120, 72, 'usa')
    draw_flag(452, 322, 120, 72, 'chn')
    draw_flag(774, 322, 120, 72, 'russia')
    draw_text_centered(190, 402, "USA", 2, WHITE)
    draw_text_centered(512, 402, "CHINA", 2, WHITE)
    draw_text_centered(834, 402, "RUSSIA", 2, WHITE)

    # Great Wall strip behind the leaders (Beijing cue)
    fill_rect(28, 420, 968, 10, (96, 64, 38))
    fill_rect(28, 420, 968, 2, GOLD)
    for tx in (300, 698):
        fill_rect(tx, 402, 26, 18, (96, 64, 38))
        fill_polygon([(tx - 4, 402), (tx + 30, 402), (tx + 13, 390)], GOLD)

    # three leaders (heads clear of the country labels above)
    draw_person(190, 460, (27, 58, 92), SKIN)
    draw_person(512, 454, (140, 20, 20), SKIN2)
    draw_person(834, 460, (45, 55, 72), SKIN)

    # round table
    fill_ellipse(512, 584, 392, 26, WOOD_D)
    fill_ellipse(512, 576, 392, 34, WOOD)
    fill_ellipse(512, 570, 392, 28, (190, 148, 100))
    fill_rect(492, 600, 40, 18, WOOD_D)
    # papers + microphones on the table
    for px in (300, 470, 680):
        fill_rect(px, 556, 52, 16, WHITE)
    for mx in (360, 512, 664):
        draw_line(mx, 566, mx, 542, INK, 3)
        fill_circle(mx, 538, 6, INK)

    # ---- bottom strip: 5 news panels
    panels = [
        ("ICJ: MYANMAR GUILTY OF ROHINGYA GENOCIDE", RED, icon_scales),
        ("VOYAGER 1 CROSSES A LIGHT-DAY", BLUE, icon_rocket),
        ("CYCLONE AKVAN 300,000 EVACUATED", TEAL, icon_cyclone),
        ("TRUMP DEFERS IRAN CALL TO 2027", AMBER, icon_clock),
        ("GTA 6 SALES PASS $1.8BN", PURPLE, icon_controller),
    ]
    px = 16
    for text, bar, icon in panels:
        fill_rect(px, 636, 192, 284, OFFWHITE)
        rect_border(px, 636, 192, 284, 3, INK)
        fill_rect(px, 636, 192, 12, bar)
        icon(px + 96, 706, )
        draw_wrapped_centered(px + 96, 762, text, 3, INK, 176, 26)
        px += 200

    # ---- also-today ticker (covers the remaining stories)
    draw_text_centered(512, 930, "ALSO: EUROPE READY TO TALK TO RUSSIA ON UKRAINE", 2, WHITE)
    draw_text_centered(512, 948, "HOUTHI STRIKE DAMAGES RIYADH TOWER", 2, GOLD_L)
    draw_text_centered(512, 966, "S. KOREA CLEARS EX-PM HAN \u2022 FIJI DROUGHT EMERGENCY", 2, WHITE)

    # ---- footer
    fill_rect(16, 988, 992, 3, GOLD)
    draw_text_centered(512, 998, "20 NOVEMBER 2026 \u2022 WORLD NEWS IN ONE IMAGE", 2, GOLD_L)


# ---------------------------------------------------------------- PNG encode
def chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    c += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return c


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)  # filter 0
        raw += buf[y * W * 3:(y + 1) * W * 3]
    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    draw_scene()
    png = encode_png()
    os.makedirs("/output", exist_ok=True)
    with open("/output/entry.png", "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()

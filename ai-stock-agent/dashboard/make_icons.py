"""Generate the app icons (opaque, full-bleed: iOS applies its own rounded mask and turns transparency black).
    python dashboard/make_icons.py      -> icon-180.png (apple-touch), icon-192.png, icon-512.png
Three candlesticks on a dark background; content stays inside the central 80% so it is safe as a maskable icon."""
import struct
import zlib
from pathlib import Path

BG, UP, DOWN = (14, 17, 22), (62, 207, 124), (255, 107, 107)
# (x center, wick top, wick bottom, body top, body bottom, color), all in 0..1 of the icon
CANDLES = [(0.30, 0.42, 0.72, 0.50, 0.66, UP), (0.50, 0.28, 0.68, 0.36, 0.58, DOWN), (0.70, 0.22, 0.60, 0.28, 0.52, UP)]


def pixel(u, v):
    for cx, wt, wb, bt, bb, col in CANDLES:
        if abs(u - cx) <= 0.011 and wt <= v <= wb:
            return col
        if abs(u - cx) <= 0.06 and bt <= v <= bb:
            return col
    return BG


def png(size, ss=3):
    rows = []
    for y in range(size):
        row = bytearray([0])
        for x in range(size):
            acc = [0, 0, 0]
            for j in range(ss):
                for i in range(ss):
                    c = pixel((x + (i + .5) / ss) / size, (y + (j + .5) / ss) / size)
                    acc[0] += c[0]; acc[1] += c[1]; acc[2] += c[2]
            row += bytes(a // (ss * ss) for a in acc)
        rows.append(bytes(row))
    raw = b"".join(rows)
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


for size, name in ((180, "icon-180.png"), (192, "icon-192.png"), (512, "icon-512.png")):
    (Path(__file__).parent / name).write_bytes(png(size))
    print("wrote", name)

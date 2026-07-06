"""生成最小占位 PNG 图标(64x64,橙色实心)。"""
import struct
import zlib
from pathlib import Path

w = h = 64
row = b"\x00" + bytes([0xEE, 0x55, 0x22, 255]) * w
raw = row * h
ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
idat = zlib.compress(raw, 9)


def chunk(t: bytes, d: bytes) -> bytes:
    return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)


png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
out = Path(__file__).resolve().parent.parent / "src-tauri" / "icons" / "icon.png"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(png)
print(f"icon.png written: {out} ({len(png)} bytes)")

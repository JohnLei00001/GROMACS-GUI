# -*- coding: utf-8 -*-
"""纯 Python 生成下拉箭头 PNG（无需 QApplication）。

生成 10x6 抗锯齿 V 形箭头：透明背景 + 圆角线段（两段直线）。
"""
import struct
import zlib
import os
import math


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))


def _make_arrow_png(color: tuple, size=(10, 6)) -> bytes:
    """color: (r,g,b); 绘制圆角 V 形箭头（两段线，round cap/join）"""
    w, h = size
    # 每像素 4 通道 RGBA
    px = [[(0, 0, 0, 0) for _ in range(w)] for _ in range(h)]

    def _coverage_round_segment(p0, p1, radius):
        """对线段做超采样覆盖（2x2），返回 alpha 像素图"""
        from math import hypot
        x0, y0 = p0
        x1, y1 = p1
        seg_dx, seg_dy = x1 - x0, y1 - y0
        seg_len = hypot(seg_dx, seg_dy)
        if seg_len == 0:
            return
        ux, uy = seg_dx / seg_len, seg_dy / seg_len
        nx, ny = -uy, ux
        # 包围盒
        minx = int(min(x0, x1) - radius) - 1
        maxx = int(max(x0, x1) + radius) + 1
        miny = int(min(y0, y1) - radius) - 1
        maxy = int(max(y0, y1) + radius) + 1
        for yy in range(max(miny, 0), min(maxy, h)):
            for xx in range(max(minx, 0), min(maxx, w)):
                # 超采样 2x2
                hit = 0
                for sy in (0.25, 0.75):
                    for sx in (0.25, 0.75):
                        qx, qy = xx + sx, yy + sy
                        # 到线段的距离
                        t = ((qx - x0) * seg_dx + (qy - y0) * seg_dy) / (seg_len * seg_len)
                        t = max(0.0, min(1.0, t))
                        cx, cy = x0 + t * seg_dx, y0 + t * seg_dy
                        d = hypot(qx - cx, qy - cy)
                        if d <= radius:
                            hit += 1
                if hit:
                    px[yy][xx] = (color[0], color[1], color[2],
                                  min(255, px[yy][xx][3] + int(255 * hit / 4)))

    # V 形：M(1,1) → L(5,5) → L(9,1)，线段半径 0.9（约 1.5px 宽）
    r = 0.9
    _coverage_round_segment((1, 1), (5, 5), r)
    _coverage_round_segment((5, 5), (9, 1), r)

    # 组装 RGBA 行
    raw = b""
    for row in px:
        raw += b"\x00" + b"".join(bytes(c for c in pix) for pix in row)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)  # 8bit RGBA
    return (b"\x89PNG\r\n\x1a\n" +
            _png_chunk(b"IHDR", ihdr) +
            _png_chunk(b"IDAT", zlib.compress(raw, 9)) +
            _png_chunk(b"IEND", b""))


def ensure_arrow_pngs() -> str:
    """生成 arrow_dark.png / arrow_light.png，返回资源目录"""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(d, exist_ok=True)
    specs = (("arrow_dark.png", (168, 168, 163)),   # #a8a8a3
             ("arrow_light.png", (135, 135, 131)))  # #878783
    for name, color in specs:
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            with open(path, "wb") as f:
                f.write(_make_arrow_png(color))
    return d


if __name__ == "__main__":
    d = ensure_arrow_pngs()
    print("生成到:", d)
    for n in ("arrow_dark.png", "arrow_light.png"):
        p = os.path.join(d, n)
        print(f"  {n}: {os.path.getsize(p)} bytes")

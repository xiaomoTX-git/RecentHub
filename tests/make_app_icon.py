# -*- coding: utf-8 -*-
"""RecentHub 应用图标生成器

单一 SVG 矢量源 -> 各尺寸原生渲染, 输出:
    app/resources/app_icon.png   512x512 高清 PNG (窗口图标 / 高清位图母版)
    app/resources/app_icon.ico   多尺寸 ICO (16/24/32/48/64/128/256)

设计: 半环时钟 + 向外溢出的记录条 (靖蓝底 #3B4FD8)

为什么要逐尺寸原生渲染:
    旧图标 ICO 里只有一帧 256x256。任务栏/托盘实际是 16~48px, 全靠系统
    把 256 缩下来, 边缘发虚。这里每个尺寸都从矢量重新栅格化, 小尺寸自己
    决定像素落点, 因此 16px 也是锐利的。
    ICO 帧格式 <=64px 用 BMP(DIB) 以兼容旧式外壳, 128/256 用 PNG 压体积。

用法:
    .venv\\Scripts\\python.exe tests\\make_app_icon.py
"""

import os
import struct

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, QRectF, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES_DIR = os.path.join(PROJECT_ROOT, "app", "resources")

ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZE = 512
BMP_MAX_SIZE = 64  # 该尺寸及以下用 DIB 帧, 以上用 PNG 帧

APP_ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
  <rect width="256" height="256" rx="56" fill="#3B4FD8"/>
  <path d="M100 72 A 56 56 0 0 0 100 184" fill="none" stroke="#FFFFFF"
        stroke-width="20" stroke-linecap="round"/>
  <circle cx="100" cy="72" r="15" fill="#7BA4FF"/>
  <rect x="162" y="92" width="52" height="14" rx="7" fill="#FFFFFF"/>
  <rect x="162" y="122" width="34" height="14" rx="7" fill="#FFFFFF" fill-opacity="0.75"/>
  <rect x="162" y="152" width="20" height="14" rx="7" fill="#FFFFFF" fill-opacity="0.5"/>
</svg>"""


def render(size: int) -> QImage:
    """把 SVG 以指定尺寸原生栅格化 (矢量 -> 像素, 每个尺寸独立抗锯齿)"""
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    QSvgRenderer(QByteArray(APP_ICON_SVG.encode("utf-8"))).render(
        painter, QRectF(0, 0, size, size)
    )
    painter.end()
    return img


def png_bytes(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    buf.close()
    return bytes(buf.data())


def dib_bytes(img: QImage) -> bytes:
    """ICO 内嵌的 DIB 帧: BITMAPINFOHEADER + BGRA 自下而上 + AND 掩码

    biHeight 必须写 2 倍高度 (上半为 XOR 位图, 下半为 AND 掩码)。
    32bpp 下透明度由 alpha 通道决定, AND 掩码给全 0 即可, 但必须存在。
    """
    w, h = img.width(), img.height()
    img = img.convertToFormat(QImage.Format_ARGB32)  # 直通 alpha, 便于取像素
    header = struct.pack("<IiiHHIIiiII", 40, w, h * 2, 1, 32, 0, 0, 0, 0, 0, 0)
    pixels = bytearray()
    for y in range(h - 1, -1, -1):  # DIB 行序自下而上
        for x in range(w):
            c = img.pixelColor(x, y)
            pixels += bytes((c.blue(), c.green(), c.red(), c.alpha()))
    mask_row_bytes = ((w + 31) // 32) * 4  # 1bpp 行按 4 字节对齐
    return header + bytes(pixels) + bytes(mask_row_bytes * h)


def build_ico(entries) -> bytes:
    """entries: [(size, payload)] -> 完整 .ico 文件字节"""
    out = bytearray(struct.pack("<HHH", 0, 1, len(entries)))
    offset = 6 + 16 * len(entries)
    for size, data in entries:
        dim = 0 if size >= 256 else size  # 256 在目录项里记作 0
        out += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    for _, data in entries:
        out += data
    return bytes(out)


def main() -> None:
    os.makedirs(RES_DIR, exist_ok=True)

    png_path = os.path.join(RES_DIR, "app_icon.png")
    render(PNG_SIZE).save(png_path, "PNG")

    entries = []
    for size in ICO_SIZES:
        img = render(size)
        entries.append((size, dib_bytes(img) if size <= BMP_MAX_SIZE else png_bytes(img)))

    ico_path = os.path.join(RES_DIR, "app_icon.ico")
    with open(ico_path, "wb") as f:
        f.write(build_ico(entries))

    print(f"PNG  {png_path}  {PNG_SIZE}x{PNG_SIZE}  {os.path.getsize(png_path) / 1024:.1f} KB")
    print(f"ICO  {ico_path}  {os.path.getsize(ico_path) / 1024:.1f} KB")
    for size, data in entries:
        kind = "DIB" if size <= BMP_MAX_SIZE else "PNG"
        print(f"     {size:>3}x{size:<3} {kind}  {len(data) / 1024:.1f} KB")


if __name__ == "__main__":
    main()

import sys
from PySide6.QtGui import QImage, QColor

shots = [
    "RecentHub/screenshot_glass_50_wechat.png",
    "RecentHub/screenshot_mode_b_perfect.png"
]

for s in shots:
    img = QImage(s)
    w, h = img.width(), img.height()
    print(f"--- File: {s} (Format: {img.format()}, Size: {w}x{h}) ---")
    pts = [(w // 2, 20), (w // 2, 70), (w // 2, h - 20)]
    for x, y in pts:
        if y < h:
            c = QColor(img.pixel(x, y))
            print(f"Point ({x}, {y}): RGBA = ({c.red()}, {c.green()}, {c.blue()}, {c.alpha()}) / Hex = {c.name()}")

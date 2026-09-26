
import sys
import os
from PIL import Image

# 查找最近的截图文件
shots = [
    "RecentHub/screenshot_glass_50_wechat.png",
    "RecentHub/screenshot_mode_b_perfect.png"
]

for s in shots:
    if os.path.exists(s):
        im = Image.open(s)
        # 获取中心空白区域像素
        w, h = im.size
        # 采样 10 个背景点
        sample_pts = [(w // 2, 30), (w // 2, 70), (w // 2, h // 2)]
        print(f"--- File: {s} (Mode: {im.mode}, Size: {im.size}) ---")
        for pt in sample_pts:
            if pt[1] < h:
                px = im.getpixel(pt)
                print(f"Point {pt}: RGBA = {px}")

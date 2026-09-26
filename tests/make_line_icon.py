
import os
from PySide6.QtGui import (
    QImage, QPainter, QColor, QLinearGradient, QPainterPath,
    QPen, QBrush
)
from PySide6.QtCore import Qt, QRectF, QPointF

def generate_minimal_line_icon(size=256):
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    # 1. 极简浅灰白透底板
    margin = size * 0.05
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    radius = size * 0.22
    
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    
    # 半透明微白底
    painter.fillPath(path, QColor(255, 255, 255, 220))
    # 1px 细线边框
    border_pen = QPen(QColor(0, 0, 0, 30), 2.0)
    painter.setPen(border_pen)
    painter.drawPath(path)

    # 2. 极简线条时光轮转 (Recent Arc) - 细线艺术
    arc_rect = QRectF(size * 0.25, size * 0.25, size * 0.50, size * 0.50)
    line_pen = QPen(QColor(30, 30, 40, 220), size * 0.038, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(line_pen)
    painter.drawArc(arc_rect, int(40 * 16), int(280 * 16))

    # 3. 中心极简四芒星/聚焦中心
    cx, cy = size * 0.5, size * 0.5
    s1, s2 = size * 0.14, size * 0.035
    core_path = QPainterPath()
    core_path.moveTo(cx, cy - s1)
    core_path.quadTo(cx, cy, cx + s1, cy)
    core_path.quadTo(cx, cy, cx, cy + s1)
    core_path.quadTo(cx, cy, cx - s1, cy)
    core_path.quadTo(cx, cy, cx, cy - s1)
    
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(20, 20, 30, 240))
    painter.fillPath(core_path, QColor(20, 20, 30, 240))

    # 4. 轨迹小端点
    dot_center = QPointF(size * 0.68, size * 0.35)
    painter.setBrush(QColor(40, 110, 255, 240))  # 灵动微蓝
    painter.drawEllipse(dot_center, size * 0.035, size * 0.035)

    painter.end()
    return img

icon_img = generate_minimal_line_icon(256)
icon_img.save("RecentHub/app/resources/app_icon.png")
icon_img.save("RecentHub/app/resources/app_icon.ico")
print("Saved minimalist line app_icon.png and app_icon.ico")

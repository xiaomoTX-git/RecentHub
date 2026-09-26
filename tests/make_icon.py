
import os
from PySide6.QtGui import (
    QImage, QPainter, QColor, QLinearGradient, QPainterPath,
    QPen, QBrush, QFont, QRadialGradient
)
from PySide6.QtCore import Qt, QRectF, QPointF

def generate_recenthub_icon(size=256):
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    
    # 1. 绘制 macOS Squircle 圆角底板 (56px 圆角)
    margin = size * 0.06
    rect = QRectF(margin, margin, size - 2 * margin, size - 2 * margin)
    
    bg_gradient = QLinearGradient(0, 0, size, size)
    bg_gradient.setColorAt(0.0, QColor("#1e1035"))   # 深邃暗紫
    bg_gradient.setColorAt(0.4, QColor("#161a3f"))   # 科技深蓝
    bg_gradient.setColorAt(1.0, QColor("#0c2540"))   # 极光深青
    
    radius = size * 0.22
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    
    painter.fillPath(path, bg_gradient)
    
    # 1.1 内边缘微妙发光线条
    highlight_pen = QPen(QColor(255, 255, 255, 45), 2.5)
    painter.setPen(highlight_pen)
    painter.drawPath(path)
    
    # 2. 绘制中心微光聚光灯 (Radial Gradient Glow)
    center = QPointF(size * 0.5, size * 0.48)
    radial_glow = QRadialGradient(center, size * 0.4)
    radial_glow.setColorAt(0.0, QColor(0, 180, 255, 60))
    radial_glow.setColorAt(0.7, QColor(130, 80, 255, 20))
    radial_glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.fillPath(path, radial_glow)

    # 3. 绘制时光回旋环 (Recent History Orbit - 代表最近轨迹)
    arc_rect = QRectF(size * 0.24, size * 0.22, size * 0.52, size * 0.52)
    arc_gradient = QLinearGradient(size * 0.2, size * 0.2, size * 0.8, size * 0.8)
    arc_gradient.setColorAt(0.0, QColor("#00d2ff"))  # 霓虹青
    arc_gradient.setColorAt(0.5, QColor("#7928ca"))  # 赛博紫
    arc_gradient.setColorAt(1.0, QColor("#ff007f"))  # 极光品红
    
    arc_pen = QPen(QBrush(arc_gradient), size * 0.045, Qt.SolidLine, Qt.RoundCap)
    painter.setPen(arc_pen)
    # 逆时针回旋 280 度
    painter.drawArc(arc_rect, int(35 * 16), int(290 * 16))

    # 4. 绘制中心聚焦罗盘/闪电搜索核心 (Hub Core)
    # 中心绘制一个精致的四芒星/聚焦菱形
    core_path = QPainterPath()
    cx, cy = size * 0.5, size * 0.48
    s1, s2 = size * 0.16, size * 0.05
    core_path.moveTo(cx, cy - s1)
    core_path.quadTo(cx, cy, cx + s1, cy)
    core_path.quadTo(cx, cy, cx, cy + s1)
    core_path.quadTo(cx, cy, cx - s1, cy)
    core_path.quadTo(cx, cy, cx, cy - s1)
    
    core_gradient = QLinearGradient(cx - s1, cy - s1, cx + s1, cy + s1)
    core_gradient.setColorAt(0.0, QColor("#ffffff"))
    core_gradient.setColorAt(0.3, QColor("#d0f0ff"))
    core_gradient.setColorAt(1.0, QColor("#00c6ff"))
    painter.fillPath(core_path, core_gradient)
    
    # 4.1 中心光晕小白点
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(255, 255, 255, 240))
    painter.drawEllipse(QPointF(cx, cy), size * 0.02, size * 0.02)
    
    # 5. 轨迹起点小圆珠 (代表历史记录点)
    dot_center = QPointF(size * 0.69, size * 0.32)
    painter.setBrush(QColor("#00ffff"))
    painter.drawEllipse(dot_center, size * 0.035, size * 0.035)

    painter.end()
    return img

os.makedirs("RecentHub/app/resources", exist_ok=True)
icon_img = generate_recenthub_icon(256)
icon_img.save("RecentHub/app/resources/app_icon.png")

# 保存 ico
icon_img.save("RecentHub/app/resources/app_icon.ico")
print("Saved app_icon.png and app_icon.ico (256x256)")

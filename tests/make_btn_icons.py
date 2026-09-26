
from PySide6.QtGui import QImage, QPainter, QColor, QPen, QPainterPath
from PySide6.QtCore import Qt, QRectF

def make_workbench_line_icon(size=48):
    # 展开工作台图标：三列/多行工作台极简线框
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    
    pen = QPen(QColor(80, 80, 95), 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    
    # 外部圆角矩形
    rect = QRectF(6, 8, size - 12, size - 16)
    painter.drawRoundedRect(rect, 4, 4)
    
    # 顶部表头分割线
    painter.drawLine(6, 18, size - 6, 18)
    # 中间垂直分割线
    painter.drawLine(20, 18, 20, size - 8)
    
    painter.end()
    return img

def make_capsule_line_icon(size=48):
    # 收起极简条图标：单行极简胶囊搜索条线框
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    
    pen = QPen(QColor(80, 80, 95), 3.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    
    # 单行圆角胶囊
    rect = QRectF(6, 14, size - 12, size - 28)
    painter.drawRoundedRect(rect, 8, 8)
    
    # 内部小透镜/小圆点
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(90, 90, 105))
    painter.drawEllipse(13, 21, 6, 6)
    
    painter.end()
    return img

wb_icon = make_workbench_line_icon(48)
wb_icon.save("RecentHub/app/resources/icon_workbench.png")

cap_icon = make_capsule_line_icon(48)
cap_icon.save("RecentHub/app/resources/icon_capsule.png")
print("Saved icon_workbench.png and icon_capsule.png")

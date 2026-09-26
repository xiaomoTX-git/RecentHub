
from PySide6.QtGui import QImage, QPainter, QColor, QPen
from PySide6.QtCore import Qt, QPointF

def make_chevron_icon(direction="up", size=48):
    img = QImage(size, size, QImage.Format_ARGB32_Premultiplied)
    img.fill(Qt.transparent)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing, True)
    
    pen = QPen(QColor(80, 80, 95), 3.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    
    mid = size / 2.0
    if direction == "up":
        # 上箭头 ^
        painter.drawLine(QPointF(mid - 9, mid + 4), QPointF(mid, mid - 5))
        painter.drawLine(QPointF(mid, mid - 5), QPointF(mid + 9, mid + 4))
    else:
        # 下箭头 v
        painter.drawLine(QPointF(mid - 9, mid - 4), QPointF(mid, mid + 5))
        painter.drawLine(QPointF(mid, mid + 5), QPointF(mid + 9, mid - 4))
        
    painter.end()
    return img

up_img = make_chevron_icon("up", 48)
up_img.save("RecentHub/app/resources/icon_up.png")

down_img = make_chevron_icon("down", 48)
down_img.save("RecentHub/app/resources/icon_down.png")
print("Saved icon_up.png and icon_down.png")

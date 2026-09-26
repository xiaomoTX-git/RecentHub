"""
RecentHub 现代化柔和极简右键菜单组件 (Windows 11 Fluent + macOS 顶流微光质感)
- 12px 柔和圆角卡片，完全消除原生直角与灰边框
- 精致的 1.5px 纯线条矢量图标，极简呼吸感
- 随系统/主窗口主题动态自适应 (深色黑曜石微光 / 浅色通透冷白冰霜)
- 柔和的胶囊形悬停反馈与微透极细分割线
"""

import math
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath


def create_vector_menu_icon(kind: str, color_hex: str = "#666677", size: int = 32) -> QIcon:
    """动态绘制高精度的 32x32 极简矢量线条菜单图标 (在 HiDPI 屏幕下极度细腻清晰)"""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    pen = QPen(QColor(color_hex), 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    pad = 4.0
    w = float(size) - pad * 2
    h = float(size) - pad * 2
    
    if kind == "show":
        # 视窗/展开矩形加小圆点
        painter.drawRoundedRect(QRectF(pad + 1, pad + 3, w - 2, h - 5), 3.0, 3.0)
        painter.drawLine(QPointF(pad + 1, pad + 9), QPointF(pad + w - 1, pad + 9))
        painter.drawEllipse(QPointF(pad + 5.5, pad + 6), 1.2, 1.2)
        painter.drawEllipse(QPointF(pad + 9.5, pad + 6), 1.2, 1.2)
    elif kind == "scan":
        # 极简双弧线循环刷新箭头
        r = QRectF(pad + 2.5, pad + 2.5, w - 5, h - 5)
        painter.drawArc(r, 45 * 16, 180 * 16)
        painter.drawArc(r, 225 * 16, 180 * 16)
        painter.drawLine(QPointF(pad + w - 3, pad + 8), QPointF(pad + w - 3, pad + 2.5))
        painter.drawLine(QPointF(pad + w - 8.5, pad + 2.5), QPointF(pad + w - 3, pad + 2.5))
        painter.drawLine(QPointF(pad + 3, pad + h - 8), QPointF(pad + 3, pad + h - 2.5))
        painter.drawLine(QPointF(pad + 8.5, pad + h - 2.5), QPointF(pad + 3, pad + h - 2.5))
    elif kind == "settings":
        # 极简线条齿轮
        cx = size / 2.0
        cy = size / 2.0
        painter.drawEllipse(QPointF(cx, cy), 4.5, 4.5)
        for i in range(6):
            ang = i * (math.pi / 3.0)
            x1 = cx + 6.8 * math.cos(ang)
            y1 = cy + 6.8 * math.sin(ang)
            x2 = cx + 9.8 * math.cos(ang)
            y2 = cy + 9.8 * math.sin(ang)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    elif kind == "clear":
        # 极简圆角垃圾桶
        painter.drawLine(QPointF(pad + 3, pad + 5.5), QPointF(pad + w - 3, pad + 5.5))
        painter.drawLine(QPointF(pad + 8, pad + 2.5), QPointF(pad + w - 8, pad + 2.5))
        body = QPainterPath()
        body.moveTo(pad + 5.5, pad + 5.5)
        body.lineTo(pad + 7.5, pad + h)
        body.quadTo(pad + 7.5, pad + h + 2, pad + 9.5, pad + h + 2)
        body.lineTo(pad + w - 9.5, pad + h + 2)
        body.quadTo(pad + w - 7.5, pad + h + 2, pad + w - 7.5, pad + h)
        body.lineTo(pad + w - 5.5, pad + 5.5)
        painter.drawPath(body)
    elif kind == "exit":
        # 极简退出门与箭头
        painter.drawRoundedRect(QRectF(pad + 2, pad + 2, w - 8, h - 4), 2.5, 2.5)
        painter.drawLine(QPointF(pad + 9, pad + h / 2.0), QPointF(pad + w - 1, pad + h / 2.0))
        painter.drawLine(QPointF(pad + w - 4, pad + h / 2.0 - 3.5), QPointF(pad + w - 1, pad + h / 2.0))
        painter.drawLine(QPointF(pad + w - 4, pad + h / 2.0 + 3.5), QPointF(pad + w - 1, pad + h / 2.0))
    elif kind == "open":
        # 极简打开/启动箭头
        painter.drawLine(QPointF(pad + 4, pad + h - 4), QPointF(pad + w - 3, pad + 3))
        painter.drawLine(QPointF(pad + w - 9, pad + 3), QPointF(pad + w - 3, pad + 3))
        painter.drawLine(QPointF(pad + w - 3, pad + 9), QPointF(pad + w - 3, pad + 3))
    elif kind == "folder":
        # 极简文件夹
        painter.drawRoundedRect(QRectF(pad + 2, pad + 6, w - 4, h - 8), 2.5, 2.5)
        painter.drawLine(QPointF(pad + 3, pad + 6), QPointF(pad + 8, pad + 2.5))
        painter.drawLine(QPointF(pad + 8, pad + 2.5), QPointF(pad + 14, pad + 2.5))
        painter.drawLine(QPointF(pad + 14, pad + 2.5), QPointF(pad + 16, pad + 6))
    elif kind == "admin":
        # 极简盾牌
        shield = QPainterPath()
        shield.moveTo(pad + w / 2.0, pad + 2)
        shield.lineTo(pad + w - 2, pad + 6)
        shield.quadTo(pad + w - 2, pad + h - 4, pad + w / 2.0, pad + h + 1)
        shield.quadTo(pad + 2, pad + h - 4, pad + 2, pad + 6)
        shield.closeSubpath()
        painter.drawPath(shield)
    elif kind == "copy":
        # 极简复制双层文档
        painter.drawRoundedRect(QRectF(pad + 6, pad + 6, w - 8, h - 8), 2.0, 2.0)
        painter.drawPolyline([
            QPointF(pad + 2, pad + h - 5),
            QPointF(pad + 2, pad + 2),
            QPointF(pad + w - 5, pad + 2)
        ])
    elif kind == "pin":
        # 极简图钉
        cx = size / 2.0
        painter.drawLine(QPointF(cx - 5, pad + 4), QPointF(cx + 5, pad + 4))
        painter.drawLine(QPointF(cx, pad + 4), QPointF(cx, pad + h - 3))
        painter.drawRoundedRect(QRectF(cx - 3.5, pad + 7, 7, 8), 1.5, 1.5)
    elif kind == "delete":
        # 极简叉号/删除
        d = 5.0
        painter.drawLine(QPointF(pad + d, pad + d), QPointF(pad + w - d, pad + h - d))
        painter.drawLine(QPointF(pad + w - d, pad + d), QPointF(pad + d, pad + h - d))
    
    painter.end()
    return QIcon(pix)


def build_modern_menu_qss(is_dark: bool) -> str:
    """构建现代柔和简约的 QMenu 专属样式表"""
    if is_dark:
        bg = "rgba(30, 30, 38, 0.95)"
        border = "1px solid rgba(255, 255, 255, 0.16)"
        text = "#F3F4F6"
        hover_bg = "rgba(255, 255, 255, 0.12)"
        hover_text = "#FFFFFF"
        sep = "rgba(255, 255, 255, 0.08)"
    else:
        bg = "rgba(255, 255, 255, 0.96)"
        border = "1px solid rgba(0, 0, 0, 0.10)"
        text = "#1F2328"
        hover_bg = "rgba(0, 0, 0, 0.06)"
        hover_text = "#111118"
        sep = "rgba(0, 0, 0, 0.06)"

    return f"""
    QMenu {{
        background-color: {bg};
        border: {border};
        border-radius: 12px;
        padding: 6px 5px;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 13px;
        color: {text};
    }}
    QMenu::item {{
        background-color: transparent;
        border-radius: 7px;
        padding: 7px 22px 7px 10px;
        margin: 2px 2px;
        color: {text};
    }}
    QMenu::item:selected {{
        background-color: {hover_bg};
        color: {hover_text};
    }}
    QMenu::separator {{
        height: 1px;
        background-color: {sep};
        margin: 5px 8px;
    }}
    QMenu::icon {{
        padding-left: 4px;
        margin-right: 8px;
    }}
    """


def setup_modern_menu(menu: QMenu, is_dark: bool = False) -> QMenu:
    """配置无边框透明背景并注入现代柔和样式表"""
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setStyleSheet(build_modern_menu_qss(is_dark))
    return menu

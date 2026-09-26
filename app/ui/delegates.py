"""
RecentHub 现代化行渲染委托 (Windows 11 Fluent + Raycast 极简微光无缝胶囊)
- 消除列与列之间的垂直割裂线，实现真正的一体化通透高光长胶囊
- 选中态提供精致的 Fluent Accent Indicator (左侧 3px 纯净呼吸指示条)
- 悬停态提供柔光半透明高斯质感微边缘 (Hover Pill)
- 完美规整文本与图标留白，消除焦点框杂质
"""

import re
from PySide6.QtCore import Qt, QRectF, QEvent
from PySide6.QtWidgets import QStyledItemDelegate, QStyle, QStyleOptionViewItem
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen


def parse_css_color(color_str: str) -> QColor:
    c = color_str.strip()
    if c.startswith("rgba"):
        m = re.match(r"rgba\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d\.]+)\s*\)", c)
        if m:
            return QColor(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(float(m.group(4)) * 255))
    elif c.startswith("rgb"):
        m = re.match(r"rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", c)
        if m:
            return QColor(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return QColor(c)


class ModernRowDelegate(QStyledItemDelegate):
    def __init__(self, parent_view=None, accent_color: str = "#0067C0", on_row_selected=None):
        super().__init__(parent_view)
        self.parent_view = parent_view
        self.hovered_row = -1
        self.selected_row = 0
        self.on_row_selected = on_row_selected
        self.accent_color = QColor(accent_color)
        self.bg_selected = QColor(255, 255, 255, 180)
        self.border_selected = QColor(255, 255, 255, 220)
        self.bg_hover = QColor(255, 255, 255, 75)
        self.border_hover = QColor(255, 255, 255, 125)

    def set_selected_row(self, row: int):
        """纳秒级设置当前高亮行号，消除重入 Qt 选择模型的多重跨层调用开销"""
        self.selected_row = row

    def set_theme_colors(self, accent: str, bg_sel: str, border_sel: str, bg_h: str, border_h: str):
        self.accent_color = parse_css_color(accent)
        self.bg_selected = parse_css_color(bg_sel)
        self.border_selected = parse_css_color(border_sel)
        self.bg_hover = parse_css_color(bg_h)
        self.border_hover = parse_css_color(border_h)
        if self.parent_view and hasattr(self.parent_view, 'viewport') and self.parent_view.viewport():
            self.parent_view.viewport().update()
        
        # 激活视口鼠标移动跟踪，实现行级平滑悬停感知
        if self.parent_view:
            self.parent_view.setMouseTracking(True)
            if hasattr(self.parent_view, 'viewport') and self.parent_view.viewport():
                self.parent_view.viewport().setMouseTracking(True)
                self.parent_view.viewport().installEventFilter(self)

    def eventFilter(self, obj, event):
        try:
            if self.parent_view and hasattr(self.parent_view, 'viewport'):
                vp = self.parent_view.viewport()
                if vp and obj == vp:
                    t = event.type()
                    if t == QEvent.Type.MouseMove:
                        pos = event.position().toPoint()
                        idx = self.parent_view.indexAt(pos)
                        new_row = idx.row() if idx.isValid() else -1
                        if new_row != self.hovered_row:
                            self.hovered_row = new_row
                            vp.update()
                    elif t in (QEvent.Type.Leave, QEvent.Type.FocusOut):
                        if self.hovered_row != -1:
                            self.hovered_row = -1
                            vp.update()
                    elif t == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                        pos = event.position().toPoint()
                        idx = self.parent_view.indexAt(pos)
                        if idx.isValid():
                            click_row = idx.row()
                            self.selected_row = click_row
                            vp.update()
                            if self.on_row_selected:
                                self.on_row_selected(click_row)
        except RuntimeError:
            pass
        return super().eventFilter(obj, event)

    def paint(self, painter: QPainter, option, index):
        row = index.row()
        col = index.column()
        
        # 严格单一数据源 (Single Source of Truth)：以纯整数 selected_row 为唯一标准
        is_selected = (row == self.selected_row)
        is_hovered = (row == self.hovered_row) and not is_selected
        
        # 1. 绘制无缝一体化微光玻璃长胶囊 (仅在选中或悬停时执行局部精细抗锯齿渲染，普通行 0 开销)
        if is_selected or is_hovered:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

            bg_color = self.bg_selected if is_selected else self.bg_hover
            border_color = self.border_selected if is_selected else self.border_hover
            
            rect = option.rect
            r = 6.0
            f_rect = QRectF(rect.x(), rect.y() + 2, rect.width(), rect.height() - 4)
            total_cols = index.model().columnCount() if index.model() else 1
            
            # (1) 填充底色 (无缝平铺)
            fill_path = QPainterPath()
            if total_cols <= 1:
                fill_path.addRoundedRect(f_rect, r, r)
            elif col == 0:
                fill_path.moveTo(f_rect.right(), f_rect.top())
                fill_path.lineTo(f_rect.left() + r, f_rect.top())
                fill_path.quadTo(f_rect.left(), f_rect.top(), f_rect.left(), f_rect.top() + r)
                fill_path.lineTo(f_rect.left(), f_rect.bottom() - r)
                fill_path.quadTo(f_rect.left(), f_rect.bottom(), f_rect.left() + r, f_rect.bottom())
                fill_path.lineTo(f_rect.right(), f_rect.bottom())
                fill_path.closeSubpath()
            elif col == total_cols - 1:
                fill_path.moveTo(f_rect.left(), f_rect.top())
                fill_path.lineTo(f_rect.right() - r, f_rect.top())
                fill_path.quadTo(f_rect.right(), f_rect.top(), f_rect.right(), f_rect.top() + r)
                fill_path.lineTo(f_rect.right(), f_rect.bottom() - r)
                fill_path.quadTo(f_rect.right(), f_rect.bottom(), f_rect.right() - r, f_rect.bottom())
                fill_path.lineTo(f_rect.left(), f_rect.bottom())
                fill_path.closeSubpath()
            else:
                fill_path.addRect(f_rect)
            painter.fillPath(fill_path, bg_color)
            
            # (2) 精细勾勒外轮廓 (重点：完全消除列与列接触处的接缝竖线！)
            painter.setPen(QPen(border_color, 1.0))
            if total_cols <= 1:
                painter.drawPath(fill_path)
            elif col == 0:
                line_path = QPainterPath()
                line_path.moveTo(f_rect.right(), f_rect.top())
                line_path.lineTo(f_rect.left() + r, f_rect.top())
                line_path.quadTo(f_rect.left(), f_rect.top(), f_rect.left(), f_rect.top() + r)
                line_path.lineTo(f_rect.left(), f_rect.bottom() - r)
                line_path.quadTo(f_rect.left(), f_rect.bottom(), f_rect.left() + r, f_rect.bottom())
                line_path.lineTo(f_rect.right(), f_rect.bottom())
                painter.drawPath(line_path)
            elif col == total_cols - 1:
                line_path = QPainterPath()
                line_path.moveTo(f_rect.left(), f_rect.top())
                line_path.lineTo(f_rect.right() - r, f_rect.top())
                line_path.quadTo(f_rect.right(), f_rect.top(), f_rect.right(), f_rect.top() + r)
                line_path.lineTo(f_rect.right(), f_rect.bottom() - r)
                line_path.quadTo(f_rect.right(), f_rect.bottom(), f_rect.right() - r, f_rect.bottom())
                line_path.lineTo(f_rect.left(), f_rect.bottom())
                painter.drawPath(line_path)
            else:
                painter.drawLine(f_rect.left(), f_rect.top(), f_rect.right(), f_rect.top())
                painter.drawLine(f_rect.left(), f_rect.bottom(), f_rect.right(), f_rect.bottom())

            # (3) Fluent Design 专属选中高亮指示灯
            if is_selected and col == 0:
                ind_path = QPainterPath()
                ind_path.addRoundedRect(QRectF(f_rect.left() + 2.0, f_rect.top() + (f_rect.height() - 16.0) / 2.0, 3.0, 16.0), 1.5, 1.5)
                painter.fillPath(ind_path, self.accent_color)
            
            painter.restore()
                
        # 2. 正常绘制文本与图标内容 (消除原生虚线焦点框与原生选中样式多余竖线干扰)
        if option.state & (QStyle.StateFlag.State_HasFocus | QStyle.StateFlag.State_Selected):
            clean_option = QStyleOptionViewItem(option)
            clean_option.state = clean_option.state & ~QStyle.StateFlag.State_HasFocus & ~QStyle.StateFlag.State_Selected
            super().paint(painter, clean_option, index)
        else:
            super().paint(painter, option, index)

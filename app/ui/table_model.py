"""
RecentHub 高性能虚拟化表格数据模型 (QAbstractTableModel)
- 纳秒级纯内存结构映射
- 支持流式增量追加 (Streamed Append)，实现打字即显、无卡顿流式检索
- 专为 120fps/144fps 高刷滚动调优
"""

import time
from typing import List
from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont
from app.core.models import RecentItem
from app.services.icon_service import IconService


def format_relative_time(timestamp: int) -> str:
    """格式化相对时间 (轻量数学运算，绝无昂贵系统调用)"""
    if not timestamp:
        return "未知"
    now = int(time.time())
    diff = now - timestamp
    if diff <= 0:
        return "刚刚"
    if diff < 60:
        return "刚刚"
    elif diff < 3600:
        return f"{diff // 60} 分钟前"
    elif diff < 86400:
        return f"{diff // 3600} 小时前"
    elif diff < 86400 * 2:
        return "昨天"
    elif diff < 86400 * 7:
        return f"{diff // 86400} 天前"
    else:
        # 简单整除避免 strftime 格式化开销
        lt = time.localtime(timestamp)
        return f"{lt.tm_year}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"


TYPE_LABELS = {
    'app': '应用',
    'file': '文档',
    'folder': '文件夹',
    'url': '链接'
}


class RecentTableModel(QAbstractTableModel):
    HEADERS_FULL = ["名称", "类型", "最后使用", "完整路径"]
    HEADERS_COMPACT = ["名称", "类型", "最后使用"]

    def __init__(self, icon_service: IconService, compact_mode: bool = False):
        super().__init__()
        self.icon_service = icon_service
        self.compact_mode = compact_mode
        self._items: List[RecentItem] = []
        self.is_dark = False
        self._update_colors()

    def set_theme_mode(self, is_dark: bool):
        if self.is_dark != is_dark:
            self.is_dark = is_dark
            self._update_colors()
            if self._items:
                top_left = self.index(0, 0)
                bottom_right = self.index(len(self._items) - 1, self.columnCount() - 1)
                self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.ForegroundRole])

    def _update_colors(self):
        if self.is_dark:
            # 深色模式：高对比度纯净亮白与温润银灰，与深色卡片背景鲜明反差
            self.color_primary = QColor(245, 246, 252)      # 名称：极纯高亮白
            self.color_secondary = QColor(210, 214, 228)    # 类型：微亮银白灰
            self.color_tertiary = QColor(165, 170, 188)     # 时间与路径：清透副文本灰
        else:
            # 浅色模式：高对比度深墨灰反差色，与白霜毛玻璃高反差
            self.color_primary = QColor(20, 20, 28)         # 名称：深邃墨黑
            self.color_secondary = QColor(70, 70, 88)       # 类型：深墨灰
            self.color_tertiary = QColor(115, 118, 136)     # 时间与路径：中性灰

    def set_compact_mode(self, compact: bool):
        self.beginResetModel()
        self.compact_mode = compact
        self.endResetModel()

    def set_items(self, items: List[RecentItem]):
        """全量重设数据集"""
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def append_items(self, new_items: List[RecentItem]):
        """流式增量追加数据集 (零闪烁、保持当前选区、极速流式展开)"""
        if not new_items:
            return
        first = len(self._items)
        last = first + len(new_items) - 1
        self.beginInsertRows(QModelIndex(), first, last)
        self._items.extend(new_items)
        self.endInsertRows()

    def get_item(self, row: int) -> RecentItem:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.HEADERS_COMPACT) if self.compact_mode else len(self.HEADERS_FULL)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            headers = self.HEADERS_COMPACT if self.compact_mode else self.HEADERS_FULL
            if 0 <= section < len(headers):
                return headers[section]
        return None

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        row = index.row()
        col = index.column()
        if row >= len(self._items):
            return None

        item = self._items[row]

        # 1. 纳秒级图标获取
        if role == Qt.ItemDataRole.DecorationRole and col == 0:
            return self.icon_service.get_icon(item)

        # 2. 文本显示
        if role == Qt.ItemDataRole.DisplayRole:
            if self.compact_mode:
                if col == 0:
                    return item.display_name
                elif col == 1:
                    return TYPE_LABELS.get(item.item_type, '文件')
                elif col == 2:
                    return format_relative_time(item.last_used_at)
            else:
                if col == 0:
                    return item.display_name
                elif col == 1:
                    return TYPE_LABELS.get(item.item_type, '文件')
                elif col == 2:
                    return format_relative_time(item.last_used_at)
                elif col == 3:
                    return item.target_path

        # 3. 颜色映射 (高反差色：深色模式纯净高亮白，浅色模式深邃墨黑)
        if role == Qt.ItemDataRole.ForegroundRole:
            if col == 0:
                return self.color_primary
            elif col == 1:
                return self.color_secondary
            else:
                return self.color_tertiary

        # 4. 置顶高亮字体
        if role == Qt.ItemDataRole.FontRole and col == 0 and item.pinned:
            f = QFont()
            f.setBold(True)
            return f

        return None

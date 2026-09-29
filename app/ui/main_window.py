"""
RecentHub 核心主窗口 (50% 纯白毛玻璃 + 极简线条风)
- 整体背景 50% 半透明通透毛玻璃质感 (Windows 11 DWM 亚克力磨砂 + 纯白高光微折射边缘)
- 鼠标在搜索输入框内同样支持拖动窗口 (基于 startDragDistance 阈值判定，单击输入与拖拽两不误)
- 筛选类别全扩容: 全部 | Word | Excel | PDF | 应用 | 文件夹 | 代码
- 彻底去除“打开次数”列与左下角“发现 200 条匹配记录”
- 恒定 720px 黄金宽度，0 滚动条，电竞级 25ms 跟手流式检索
"""

import os
import sys
import time
import ctypes
from typing import Optional, List, Set

user32 = ctypes.windll.user32 if sys.platform == "win32" else None
VK_DOWN = 0x28
VK_UP = 0x26
from PySide6.QtCore import (
    Qt, QEvent, QTimer, QThread, Signal, QModelIndex, QPoint, QSize, QRect,
    QVariantAnimation, QEasingCurve, QItemSelectionModel
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QTableView, QPushButton, QLabel, QMenu, QHeaderView,
    QAbstractItemView, QApplication, QFrame, QSizePolicy,
    QProxyStyle, QStyle, QButtonGroup
)
from PySide6.QtGui import (
    QKeySequence, QShortcut, QAction, QClipboard, QCursor,
    QIcon, QPixmap, QPainter, QPen, QColor
)

# GetAsyncKeyState 句柄惰性初始化缓存 (None=未初始化, False=不可用)
_GAKS = None

from app.core.config import ConfigManager
from app.core.paths import resource_dir
from app.storage.db import StorageDB, item_matches_filters
from app.parsers.query_parser import parse_query
from app.services.scan_service import ScanService
from app.services.open_service import OpenService
from app.core.models import RecentItem
from app.services.icon_service import IconService
from app.services.file_search_service import FileSearchService
from app.services.live_search_worker import PersistentSearchWorker
from app.ui.table_model import RecentTableModel
from app.ui.delegates import ModernRowDelegate
from app.ui.style import STYLE_WHITE_GLASS
from app.ui.effects import apply_acrylic, apply_light_acrylic
from app.ui.themes import THEMES, get_theme, build_qss, is_windows_dark_mode, get_effective_theme_id
from app.ui.settings_dialog import SettingsDialog
from app.ui.menu_utils import create_vector_menu_icon, setup_modern_menu


class CleanItemViewStyle(QProxyStyle):
    """消除 Windows 11 原生逐列重复绘制粗糙指示条 (PE_PanelItemViewRow)，交由委托统一绘制极致行级长胶囊"""
    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_PanelItemViewRow:
            return
        super().drawPrimitive(element, option, painter, widget)


class SearchLoadingIndicator(QWidget):
    """深度全盘检索进行中的极简旋转指示器 (圆头弧线匀速自转，配色随主题)

    挂在搜索行下方的居中 loading 行里，与"正在全盘检索…"文案一起出现，
    结果到达或兜底超时后整行隐去，不占用常规布局高度。
    """

    def __init__(self, parent=None, size: int = 18):
        super().__init__(parent)
        self.setFixedSize(size, size)
        # 纯展示控件：不接受鼠标事件，避免在搜索框下方形成一个"死区"
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._angle = 0
        self._color = QColor(139, 92, 246)
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60FPS 匀速旋转
        self._timer.timeout.connect(self._tick)

    def set_color(self, color_hex: str):
        self._color = QColor(color_hex)
        self.update()

    def start(self):
        if not self._timer.isActive():
            self._angle = 0
            self._timer.start()
        self.update()

    def stop(self):
        self._timer.stop()
        self.update()

    def _tick(self):
        self._angle = (self._angle + 12) % 360
        self.update()

    def paintEvent(self, event):
        # 空闲态不绘制任何像素：控件本身常驻布局（避免输入框宽度随检索反复伸缩跳动），
        # 但未检索时完全不占用视觉，保持极简条的干净
        if not self._timer.isActive():
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = self.rect().adjusted(2, 2, -2, -2)

        # 底圈轨道：同色低透明度，交代"正在旋转"的完整圆环轮廓
        track = QColor(self._color)
        track.setAlpha(45)
        pen_track = QPen(track, 2)
        pen_track.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_track)
        p.drawArc(rect, 0, 360 * 16)

        # 高亮弧：约 100° 的圆头弧线，负角度即顺时针旋转
        pen_arc = QPen(self._color, 2)
        pen_arc.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_arc)
        p.drawArc(rect, -self._angle * 16, -100 * 16)
        p.end()


class ScanWorker(QThread):
    scan_finished = Signal(int)

    def __init__(self, scan_service: ScanService):
        super().__init__()
        self.scan_service = scan_service

    def run(self):
        try:
            count = self.scan_service.scan_all()
            self.scan_finished.emit(count)
        except Exception:
            self.scan_finished.emit(0)


# 旧版瞬态 AsyncLiveSearchWorker 已升级为单例常驻持久化 PersistentSearchWorker


class MainWindow(QMainWindow):
    WINDOW_WIDTH = 780  # 宽屏大气横向长方形，彻底告别窄长竖立形变

    def __init__(self, db: StorageDB, scan_service: ScanService, auto_scan: bool = True):
        super().__init__()
        self.db = db
        self.scan_service = scan_service
        self.icon_service = IconService()
        self.worker: Optional[ScanWorker] = None
        
        # 读取用户持久化宽高与比例配置
        (self.custom_width,
         self.custom_workbench_height,
         self.custom_dropdown_height,
         self.custom_bar_height) = ConfigManager.get_window_size()
        self.WINDOW_WIDTH = self.custom_width

        self.current_mode = "A"
        # Mode A 空查询时是否强制展开下拉列表 (用户按上下键直接选取最近记录时置位)
        self._panel_forced_open = False
        # 当前高亮行；-1 表示尚未建立选中态 (首按键应落在首行/末行)
        self._current_selected_row = -1
        # 表头排序状态：-1 表示未启用排序 (保持 DB 默认的置顶 + 时间倒序)
        self._sort_column = -1
        self._sort_order = Qt.SortOrder.AscendingOrder
        # 类型筛选 (Mode B 顶部药丸)：'all' 表示不过滤
        self._current_item_type = "all"
        # 空列表时的上下键加载去重标记，避免巡航期间 50Hz 重复查库
        self._nav_ensure_key = None
        # 长按巡航状态机：是否已收到过 OS 自动重复 / 巡航起点 / 系统首重复延迟
        self._saw_repeat = False
        self._cruise_started_at = 0.0
        self._repeat_delay_sec = self._keyboard_repeat_delay()
        
        # 拖拽移动与边缘Resize状态变量
        self._is_dragging = False
        self._drag_offset: Optional[QPoint] = None
        self._user_has_dragged = False
        self._input_press_pos: Optional[QPoint] = None
        self._is_input_dragging = False
        self._is_resizing = False
        self._resize_edge = ""
        self._resize_start_geom: Optional[QRect] = None
        self._resize_start_global: Optional[QPoint] = None
        
        # 单例持久化后台全盘检索工作线程 (彻底根治 QThread 频繁创建与析构崩溃)
        self.live_search_worker = PersistentSearchWorker()
        self.live_search_worker.results_ready.connect(self._on_async_results_ready)
        self.live_search_worker.start()
        self._current_seen_paths: Set[str] = set()

        self.res_dir = resource_dir()
        # 用多尺寸 .ico 而非单张 .png：ico 内含 16~256px 各档原生渲染帧，
        # 窗口/任务栏按实际像素密度取帧，高 DPI 下不会因缩放而发虚
        icon_path = os.path.join(self.res_dir, "app_icon.ico")
        self.app_icon = QIcon(icon_path) if os.path.exists(icon_path) else QIcon()
        self.setWindowIcon(self.app_icon)

        wb_icon_path = os.path.join(self.res_dir, "icon_workbench.png")
        cap_icon_path = os.path.join(self.res_dir, "icon_capsule.png")
        self.wb_icon = QIcon(wb_icon_path) if os.path.exists(wb_icon_path) else QIcon()
        self.cap_icon = QIcon(cap_icon_path) if os.path.exists(cap_icon_path) else QIcon()

        self._init_ui()
        self._init_shortcuts()
        self._init_connections()
        self._init_drag_surfaces()

        self._center_window()
        if auto_scan:
            self.trigger_background_scan()

    def _init_ui(self):
        self.setStyleSheet(STYLE_WHITE_GLASS)
        self.setWindowTitle("RecentHub")

        # 开启透明与无边框 (支持手动拖拽Resize)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(560, 42)
        self.setMaximumSize(1400, 1000)
        self.resize(self.custom_width, self.custom_workbench_height if self.current_mode == "B" else self.custom_bar_height)

        # 核心通透毛玻璃质感主卡片 (开启 WA_StyledBackground 确保完美半透明渲染)
        self.central_card = QWidget(self)
        self.central_card.setObjectName("CentralCard")
        self.central_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(self.central_card)

        self.card_layout = QVBoxLayout(self.central_card)
        self.card_layout.setContentsMargins(14, 10, 14, 10)
        self.card_layout.setSpacing(6)

        # 1. 顶部搜索行 (自然呼吸留白，告别硬线条)
        self.search_row = QWidget()
        self.search_row.setObjectName("SearchRow")
        search_layout = QHBoxLayout(self.search_row)
        search_layout.setContentsMargins(2, 2, 2, 4)
        search_layout.setSpacing(10)

        # 搜索框左侧极简线性放大镜图标 (支持窗口拖动锚点)
        self.search_icon_label = QLabel()
        self.search_icon_label.setObjectName("SearchIconLabel")
        search_icon_p = os.path.join(self.res_dir, "icon_search_light.png")
        if os.path.exists(search_icon_p):
            pix = QPixmap(search_icon_p)
            self.search_icon_label.setPixmap(pix.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.search_icon_label.setCursor(QCursor(Qt.CursorShape.SizeAllCursor))
        self.search_icon_label.setToolTip("按住可拖动窗口")
        search_layout.addWidget(self.search_icon_label)
        self.logo_label = self.search_icon_label

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("SearchInput")
        self.search_edit.setFixedHeight(30)
        self.search_edit.setPlaceholderText("键入以秒搜最近记录 (支持拼音如 wz、文件名、扩展名)...")
        self.search_edit.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_edit)

        # 右上角偏好设置按钮 (极简精致纯线条齿轮图标)
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("SettingsBtn")
        self.settings_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.settings_btn.setIconSize(QSize(16, 16))
        self.settings_btn.setToolTip("设置")
        settings_icon_p = os.path.join(self.res_dir, "icon_settings_light.png")
        if os.path.exists(settings_icon_p):
            self.settings_btn.setIcon(QIcon(settings_icon_p))
        search_layout.addWidget(self.settings_btn)

        # 右上角模式切换按钮 (极简精致透光图标按钮)
        self.mode_toggle_btn = QPushButton()
        self.mode_toggle_btn.setObjectName("ModeActionBtn")
        self.mode_toggle_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mode_toggle_btn.setIconSize(QSize(16, 16))
        search_layout.addWidget(self.mode_toggle_btn)

        self.search_row.setFixedHeight(34)
        self.search_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.card_layout.addWidget(self.search_row, 0, Qt.AlignmentFlag.AlignTop)

        # 2. 核心结果表格 (去除分割线与筛选器，空间纯净呼吸，一体化悬浮呈现)
        self.table_view = QTableView()
        # 严禁把已有样式作为 base 传入：QProxyStyle 会夺取 base 样式的所有权，
        # 而 table_view.style() / QApplication.style() 的样式由 Qt 自己持有并销毁，
        # 退出时便会双重释放导致进程 Abort 崩溃。不传 base 时 QProxyStyle
        # 会自动回落到 QApplication::style()，效果完全一致且无所有权风险。
        self.clean_view_style = CleanItemViewStyle()
        self.table_view.setStyle(self.clean_view_style)
        self.table_model = RecentTableModel(self.icon_service, compact_mode=True)
        self.table_view.setModel(self.table_model)
        
        cfg = ConfigManager.load()
        accent = cfg.get("accent_color", "#8B5CF6")
        row_h = cfg.get("row_height", 38)
        
        self.row_delegate = ModernRowDelegate(
            self.table_view,
            accent_color=accent,
            on_row_selected=self._on_delegate_row_selected
        )
        self.table_view.setItemDelegate(self.row_delegate)
        
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.setShowGrid(False)
        # QTableView 的 wordWrap 默认为 True：长路径会在反斜杠处被硬折成两行
        # ("C:" 一行 + "\Users\..." 一行)，行高被撑破且语义割裂。
        # 关掉后由委托按 ElideRight 单行截断为 "C:\Users\...\RecentH..."，干净且易读
        self.table_view.setWordWrap(False)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(row_h)
        self.table_view.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table_view.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # 极致高刷虚拟化加速：固定行高与快速整行滚动 (免除全表昂贵的逐行几何测量与微像素卡顿)
        self.table_view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerItem)
        self.table_view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table_view.horizontalHeader().setHighlightSections(False)
        # 表头文字与数据单元格同为左对齐：Qt 表头默认居中，窄列 (类型/最后使用)
        # 上表头与左对齐的数据明显错位，视觉上像两套体系
        self.table_view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # 表头可点击排序 (Mode B)：仅开启点击与指示箭头，绝不启用 setSortingEnabled
        self.table_view.horizontalHeader().setSectionsClickable(True)
        self.table_view.horizontalHeader().setSortIndicatorShown(True)
        if self.table_view.viewport():
            self.table_view.viewport().setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        
        # 彻底关闭横向与纵向原生滚动条
        self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # 检索 loading 行：位于搜索行正下方、水平居中 (比原来挤在输入框右侧更醒目)
        self.loading_row = QWidget()
        self.loading_row.setObjectName("LoadingRow")
        loading_layout = QHBoxLayout(self.loading_row)
        loading_layout.setContentsMargins(0, 2, 0, 2)
        loading_layout.setSpacing(8)
        loading_layout.addStretch()
        self.search_loading = SearchLoadingIndicator(size=18)
        loading_layout.addWidget(self.search_loading)
        self.loading_label = QLabel("正在全盘检索…")
        self.loading_label.setObjectName("LoadingLabel")
        loading_layout.addWidget(self.loading_label)
        loading_layout.addStretch()
        # 空闲时整行不占任何高度：极简条仍保持 48px，不会被撑高
        self.loading_row.hide()
        self.card_layout.addWidget(self.loading_row)

        # 类型筛选药丸行：仅 Mode B 工作台显示，Mode A 极简条隐藏 (见 _apply_mode_ui)
        self.filter_row = QWidget()
        self.filter_row.setObjectName("FilterRow")
        filter_layout = QHBoxLayout(self.filter_row)
        filter_layout.setContentsMargins(2, 0, 2, 2)
        filter_layout.setSpacing(6)

        self.filter_btn_group = QButtonGroup(self.filter_row)
        self.filter_btn_group.setExclusive(True)
        self.filter_buttons = {}
        for type_key, label in (
            ("all", "全部"),
            ("word", "文档"),
            ("excel", "表格"),
            ("pdf", "PDF"),
            ("code", "代码"),
            ("app", "应用"),
            ("folder", "文件夹"),
        ):
            btn = QPushButton(label)
            btn.setObjectName("FilterPill")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            btn.setChecked(type_key == "all")
            btn.clicked.connect(lambda checked, k=type_key: self._select_item_type(k))
            self.filter_btn_group.addButton(btn)
            self.filter_buttons[type_key] = btn
            filter_layout.addWidget(btn)
        filter_layout.addStretch()
        self.filter_row.hide()
        self.card_layout.addWidget(self.filter_row)

        self.card_layout.addWidget(self.table_view)

        # 3. 底部极简状态栏 (Raycast / Fluent 现代按键徽标风格)
        self.status_bar = QWidget()
        self.status_bar.setObjectName("StatusBar")
        status_layout = QHBoxLayout(self.status_bar)
        status_layout.setContentsMargins(2, 2, 2, 2)
        status_layout.addStretch()
        
        self.shortcut_hint = QLabel()
        kbd_style = "background: rgba(255, 255, 255, 0.72); border: 1px solid rgba(255, 255, 255, 0.95); border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 600; color: #2A2A38;"
        self.shortcut_hint.setText(
            f'<span style="{kbd_style}">↵ Enter</span> <span style="color:#666677; font-size:11px;">打开</span>'
            f'&nbsp;&nbsp;&nbsp;&nbsp;'
            f'<span style="{kbd_style}">Alt + ↵</span> <span style="color:#666677; font-size:11px;">定位目录</span>'
            f'&nbsp;&nbsp;&nbsp;&nbsp;'
            f'<span style="{kbd_style}">Esc</span> <span style="color:#666677; font-size:11px;">隐藏</span>'
        )
        status_layout.addWidget(self.shortcut_hint)
        self.card_layout.addWidget(self.status_bar)
        self.status_bar.hide()  # 遵循极简设计，默认隐藏底部栏

        # 动态加载并应用当前已配置的主题皮肤 (默认跟随系统)
        cfg = ConfigManager.load()
        saved_theme = cfg.get("theme", "system")
        self.apply_theme(saved_theme)

        # 跟随系统主题定时器 (仅在前台激活时运行，后台自动暂停消除 CPU 轮询)
        self.system_theme_timer = QTimer(self)
        self.system_theme_timer.setInterval(1500)
        self.system_theme_timer.timeout.connect(self._check_system_theme_change)
        self.system_theme_timer.start()

        # 后台深度休眠定时器 (隐藏 2500ms 后自动执行物理内存修剪与垃圾回收，高频唤醒 0ms 秒开，长期闲置极度省内存)
        self._hibernate_timer = QTimer(self)
        self._hibernate_timer.setSingleShot(True)
        self._hibernate_timer.setInterval(2500)
        self._hibernate_timer.timeout.connect(self._do_deep_hibernate)

        self._apply_mode_ui(recenter=False)

    def _calc_edge(self, pos: QPoint) -> str:
        """计算鼠标在窗口中的边缘方向 (10px 灵敏边缘感应区，全模式全面支持宽高调整)"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        m = 10

        if x < 0 or y < 0 or x > w or y > h:
            return ""

        on_left = (x <= m)
        on_right = (x >= w - m)
        on_top = (y <= m)
        on_bottom = (y >= h - m)

        # 四角拉伸 (对角调整)
        if on_top and on_left:
            return "top_left"
        if on_top and on_right:
            return "top_right"
        if on_bottom and on_left:
            return "bottom_left"
        if on_bottom and on_right:
            return "bottom_right"

        # 四边拉伸 (水平 / 垂直自由调整)
        if on_left:
            return "left"
        if on_right:
            return "right"
        if on_top:
            return "top"
        if on_bottom:
            return "bottom"
        return ""

    def _cursor_for_edge(self, edge: str):
        if edge in ("left", "right"):
            return Qt.CursorShape.SizeHorCursor
        if edge in ("top", "bottom"):
            return Qt.CursorShape.SizeVerCursor
        if edge in ("top_left", "bottom_right"):
            return Qt.CursorShape.SizeFDiagCursor
        if edge in ("top_right", "bottom_left"):
            return Qt.CursorShape.SizeBDiagCursor
        return Qt.CursorShape.ArrowCursor

    def _handle_resize_move(self, global_pt: QPoint):
        if not self._is_resizing or not self._resize_start_geom or not self._resize_start_global:
            return

        delta = global_pt - self._resize_start_global
        orig = self._resize_start_geom

        new_x, new_y = orig.x(), orig.y()
        new_w, new_h = orig.width(), orig.height()

        MIN_W, MAX_W = 560, 1400

        # 水平拉伸
        if "right" in self._resize_edge:
            new_w = max(MIN_W, min(orig.width() + delta.x(), MAX_W))
        elif "left" in self._resize_edge:
            target_w = max(MIN_W, min(orig.width() - delta.x(), MAX_W))
            new_x = orig.right() - target_w + 1
            new_w = target_w

        # 垂直拉伸 (全模式全面支持高度调整与自适应)
        if self.current_mode == "B":
            MIN_H, MAX_H = 280, 900
            if "bottom" in self._resize_edge:
                new_h = max(MIN_H, min(orig.height() + delta.y(), MAX_H))
            elif "top" in self._resize_edge:
                target_h = max(MIN_H, min(orig.height() - delta.y(), MAX_H))
                new_y = orig.bottom() - target_h + 1
                new_h = target_h
            self.custom_workbench_height = new_h
        else:
            # Mode A 搜索模式
            if self.table_view.isVisible():
                # 下拉结果列表展开态：支持拖动底边与角落自由拉伸下拉面板高度
                MIN_H, MAX_H = 140, 850
                if "bottom" in self._resize_edge:
                    new_h = max(MIN_H, min(orig.height() + delta.y(), MAX_H))
                elif "top" in self._resize_edge:
                    target_h = max(MIN_H, min(orig.height() - delta.y(), MAX_H))
                    new_y = orig.bottom() - target_h + 1
                    new_h = target_h
                self.custom_dropdown_height = new_h
            else:
                # 纯搜索胶囊条：支持微调搜索框本身的高度厚度
                MIN_H, MAX_H = 42, 72
                if "bottom" in self._resize_edge:
                    new_h = max(MIN_H, min(orig.height() + delta.y(), MAX_H))
                elif "top" in self._resize_edge:
                    target_h = max(MIN_H, min(orig.height() - delta.y(), MAX_H))
                    new_y = orig.bottom() - target_h + 1
                    new_h = target_h
                self.custom_bar_height = new_h

        self.setGeometry(new_x, new_y, new_w, new_h)
        self.custom_width = new_w
        self.WINDOW_WIDTH = new_w

    def _save_window_config(self):
        ConfigManager.save_window_size(
            self.custom_width,
            self.custom_workbench_height,
            self.custom_dropdown_height,
            self.custom_bar_height
        )

    def _init_drag_surfaces(self):
        """安装平滑拖拽监听器 (含搜索输入框支持拖拽与无边框边缘Resize)"""
        self.draggable_surfaces = [
            self.central_card,
            self.search_row,
            self.logo_label,
            self.status_bar,
            self.shortcut_hint
        ]
        self.setMouseTracking(True)
        self.central_card.setMouseTracking(True)
        for w in self.draggable_surfaces:
            w.setMouseTracking(True)
            w.installEventFilter(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._calc_edge(pos)
            if edge:
                self._is_resizing = True
                self._resize_edge = edge
                self._resize_start_geom = self.geometry()
                self._resize_start_global = event.globalPosition().toPoint()
                self._user_has_dragged = True
                event.accept()
                return

            self._is_dragging = True
            self._drag_offset = event.globalPosition().toPoint() - self.pos()
            self._user_has_dragged = True
            event.accept()

    def mouseMoveEvent(self, event):
        global_pt = event.globalPosition().toPoint()
        if self._is_resizing:
            self._handle_resize_move(global_pt)
            event.accept()
            return
        elif not (event.buttons() & Qt.MouseButton.LeftButton):
            edge = self._calc_edge(event.position().toPoint())
            if edge:
                self.setCursor(self._cursor_for_edge(edge))
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

        if self._is_dragging and (event.buttons() & Qt.MouseButton.LeftButton) and self._drag_offset is not None:
            self.move(global_pt - self._drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_resizing:
                self._is_resizing = False
                self._resize_edge = ""
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self._save_window_config()
                event.accept()
                return

            self._is_dragging = False
            self._drag_offset = None
            event.accept()

    def eventFilter(self, obj, event):
        # 0. 全局无边框窗口边缘 Resize 感应与拖拽
        if event.type() in (event.Type.MouseMove, event.Type.MouseButtonPress, event.Type.MouseButtonRelease):
            global_pt = event.globalPosition().toPoint()
            window_pt = self.mapFromGlobal(global_pt)
            edge = self._calc_edge(window_pt)

            if event.type() == event.Type.MouseMove:
                if self._is_resizing:
                    self._handle_resize_move(global_pt)
                    return True
                elif not (event.buttons() & Qt.MouseButton.LeftButton):
                    if edge:
                        self.setCursor(self._cursor_for_edge(edge))
                    else:
                        if obj != self.search_edit:
                            self.setCursor(Qt.CursorShape.ArrowCursor)

            elif event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if edge:
                    self._is_resizing = True
                    self._resize_edge = edge
                    self._resize_start_geom = self.geometry()
                    self._resize_start_global = global_pt
                    self._user_has_dragged = True
                    return True

            elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if self._is_resizing:
                    self._is_resizing = False
                    self._resize_edge = ""
                    self.setCursor(Qt.CursorShape.ArrowCursor)
                    self._save_window_config()
                    return True

        # 1. 核心特性：鼠标在搜索输入框内也能拖动窗口 (基于 startDragDistance 阈值判定)
        if obj == self.search_edit:
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._input_press_pos = event.position().toPoint()
                self._drag_offset = event.globalPosition().toPoint() - self.pos()
                self._is_input_dragging = False
            elif event.type() == event.Type.MouseMove and (event.buttons() & Qt.MouseButton.LeftButton):
                if hasattr(self, '_input_press_pos') and self._input_press_pos is not None:
                    delta = (event.position().toPoint() - self._input_press_pos).manhattanLength()
                    if delta > QApplication.startDragDistance():
                        self._is_input_dragging = True
                        self._user_has_dragged = True
                        self.search_edit.deselect()
                        if self._drag_offset is not None:
                            self.move(event.globalPosition().toPoint() - self._drag_offset)
                        return True
            elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                if getattr(self, '_is_input_dragging', False):
                    self._is_input_dragging = False
                    return True

        # 2. 其它空白表面拖动 (严格排除表格视口，确保列表项单击响应绝对不受拖拽影响)
        if hasattr(self, 'draggable_surfaces') and obj in self.draggable_surfaces:
            vp = getattr(getattr(self, 'table_view', None), 'viewport', lambda: None)()
            if obj != vp:
                if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                    self._is_dragging = True
                    self._drag_offset = event.globalPosition().toPoint() - self.pos()
                    self._user_has_dragged = True
                    return True
                elif event.type() == event.Type.MouseMove and (event.buttons() & Qt.MouseButton.LeftButton):
                    if self._is_dragging and self._drag_offset is not None:
                        self.move(event.globalPosition().toPoint() - self._drag_offset)
                        return True
                elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                    self._is_dragging = False
                    self._drag_offset = None
                    return True

        # 3. 键盘上下导航引擎 (心跳续命安全状态机：单按0ms + 190ms起跑隔离 + 50Hz巡航 + 多重刹车)
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                self._handle_nav_key_press(key, event.isAutoRepeat())
                return True
            elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._stop_all_navigation()
                self._open_selected_item()
                return True
        elif event.type() == QEvent.Type.KeyRelease:
            if event.key() in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                # 仅"真实松手"才刹车。Windows 长按时会成对投递
                # KeyPress(isAutoRepeat=True) + KeyRelease(isAutoRepeat=True)，
                # 若对自动重复的 Release 也刹车，长按会在刚起跑时被反复掐断，
                # 表现就是"长按只滚一两下就彻底不动"。
                if not event.isAutoRepeat():
                    self._stop_all_navigation()
                return True
        return super().eventFilter(obj, event)

    def _keyboard_repeat_delay(self) -> float:
        """读取系统首次自动重复延迟 (SPI_GETKEYBOARDDELAY: 0~3 → 250/500/750/1000ms)"""
        try:
            val = ctypes.c_int(0)
            if ctypes.windll.user32.SystemParametersInfoW(0x0016, 0, ctypes.byref(val), 0):
                return 0.25 + max(0, min(3, val.value)) * 0.25
        except Exception:
            pass
        return 0.5

    def _handle_nav_key_press(self, key, is_auto_repeat: bool):
        """上下键按下统一入口 (eventFilter 与 keyPressEvent 共用，保证不会双重步进)"""
        if is_auto_repeat:
            # OS 自动重复到达：证明手指仍在按着。步频一律交给巡航定时器统一控制
            # (自动重复本身不步进)，此处只续命心跳。
            self._heartbeat = time.perf_counter()
            self._saw_repeat = True
            # 关键：状态若被意外清空 (平台补发自动重复 Release 等)，必须重新接管长按，
            # 否则后续自动重复全部被丢弃 -> 长按滚一两下就彻底不动。
            if self._held_key is None:
                self._held_key = key
            if (hasattr(self, '_hold_detect_timer')
                    and not self._hold_detect_timer.isActive()
                    and not (hasattr(self, '_cruise_timer') and self._cruise_timer.isActive())):
                self._hold_detect_timer.start(400)
            return
        # 物理新按压：立即无条件步进 1 行 + 启动长按起跑侦测
        self._stop_all_navigation()
        self._held_key = key
        self._heartbeat = time.perf_counter()
        self._saw_repeat = False
        if key == Qt.Key.Key_Down:
            self.select_next_row()
        else:
            self.select_prev_row()
        if hasattr(self, '_hold_detect_timer'):
            # 400ms 起跑门限：普通轻敲(通常 80~150ms)绝不触发巡航，
            # 只有真正按住才进入自动滚动，避免"轻按一下却自己滚个不停"
            self._hold_detect_timer.start(400)

    def _apply_mode_ui(self, recenter: bool = False):
        q = self.search_edit.text().strip()

        if self.current_mode == "A":
            if hasattr(self, 'settings_btn'):
                self.settings_btn.hide()
            # 类型药丸仅属于工作台，极简条下隐藏
            if hasattr(self, 'filter_row'):
                self.filter_row.hide()
            self.table_model.set_compact_mode(True)
            self.table_view.horizontalHeader().setVisible(False)
            self.mode_toggle_btn.setIcon(self.wb_icon)
            self.mode_toggle_btn.setToolTip("展开至工作台 (Tab)")

            h_header = self.table_view.horizontalHeader()
            h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            h_header.resizeSection(1, 55)
            h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            h_header.resizeSection(2, 95)

            if not q and not self._panel_forced_open:
                # 收起为极简条时立即隐藏表格和状态栏，消除缩短高度过程中的挤压抖动
                self.table_view.hide()
                self.status_bar.hide()
                if self.isVisible():
                    # 高度收敛到极简条；未被拖动过才回屏幕正中 (居中悬浮形态)
                    self._animate_mode_height(self.custom_bar_height)
                else:
                    self.resize(self.custom_width, self.custom_bar_height)
                    if not self._user_has_dragged:
                        self._center_window()
            else:
                self.table_view.show()
                if abs(self.height() - self.custom_dropdown_height) > 4:
                    self._animate_height(self.custom_dropdown_height)
        else:
            if hasattr(self, 'settings_btn'):
                self.settings_btn.show()
            if hasattr(self, 'filter_row'):
                self.filter_row.show()
            self.table_view.show()
            self.table_model.set_compact_mode(False)
            self.table_view.horizontalHeader().setVisible(True)
            self.mode_toggle_btn.setIcon(self.cap_icon)
            self.mode_toggle_btn.setToolTip("收起为极简条 (Tab)")

            # Mode B: 用户自定义宽高自适应布局
            h_header = self.table_view.horizontalHeader()
            h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            h_header.resizeSection(0, max(180, int(self.custom_width * 0.28)))
            h_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            h_header.resizeSection(1, 65)
            h_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            h_header.resizeSection(2, 100)
            h_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

            # 工作台是大面板，高度收敛；位置策略同上 (拖动过后绝不闪回正中)
            self._animate_mode_height(self.custom_workbench_height)

        if recenter and not self._user_has_dragged:
            self._center_window()

        self.search_edit.setFocus()

    def _animate_height(self, target_h: int, on_finished=None):
        cur_h = self.height()
        if cur_h == target_h or not self.isVisible():
            self.resize(self.custom_width, target_h)
            if on_finished:
                on_finished()
            return

        if hasattr(self, '_height_anim') and self._height_anim.state() == QVariantAnimation.State.Running:
            self._height_anim.stop()

        self._height_anim = QVariantAnimation(self)
        self._height_anim.setDuration(160)
        self._height_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._height_anim.setStartValue(cur_h)
        self._height_anim.setEndValue(target_h)
        self._height_anim.valueChanged.connect(lambda val: self.resize(self.custom_width, int(val)))
        if on_finished:
            self._height_anim.finished.connect(on_finished)
        self._height_anim.start()

    def _on_collapse_finished(self):
        if not self.search_edit.text().strip() and self.current_mode == "A":
            self.table_view.hide()
            self.status_bar.hide()

    def _animate_mode_height(self, target_h: int):
        """模式切换高度动画的位置策略：
        - 用户从未拖动过窗口：收敛后回到屏幕正中 (保持"居中悬浮"的启动器形态)
        - 用户已拖走窗口：位置归用户所有，仅改高度并做屏幕边界夹取，
          绝不闪回正中 (否则拖到侧边后一切换模式就跳走，像被抢走一样)"""
        if not self._user_has_dragged:
            self._animate_height(target_h, on_finished=self._center_window)
            return

        def _keep_position():
            # 高度变化后仅夹取边界：底部不越过任务栏、顶部不出屏、左右不出屏
            from PySide6.QtGui import QGuiApplication
            screen = self.screen() or QGuiApplication.primaryScreen()
            if not screen:
                return
            geo = screen.availableGeometry()
            x, y = self.x(), self.y()
            max_y = geo.bottom() - self.height() + 1
            if y > max_y:
                y = max(geo.top(), max_y)
            max_x = geo.right() - self.width() + 1
            if x > max_x:
                x = max(geo.left(), max_x)
            self.move(x, y)

        self._animate_height(target_h, on_finished=_keep_position)

    def _center_window(self):
        """将窗口移动至当前活动屏幕正中间 (智能避开底部任务栏并支持多屏定位)"""
        from PySide6.QtGui import QGuiApplication, QCursor
        screen = QGuiApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)

    def _is_on_any_screen(self) -> bool:
        """窗口与任一屏幕可用区是否相交 (用于拔掉显示器后找回窗口的兜底判断)"""
        from PySide6.QtGui import QGuiApplication
        r = self.geometry()
        return any(r.intersects(s.availableGeometry()) for s in QGuiApplication.screens())

    def hide(self):
        self._prepare_background_hibernation()
        super().hide()

    def _prepare_background_hibernation(self):
        # 1. 彻底停止后台前端定时器，实现 0% CPU 占用
        if hasattr(self, 'system_theme_timer') and self.system_theme_timer.isActive():
            self.system_theme_timer.stop()
        if hasattr(self, 'async_search_timer') and self.async_search_timer.isActive():
            self.async_search_timer.stop()
        if hasattr(self, 'live_search_worker') and self.live_search_worker:
            self.live_search_worker.cancel_pending()
        # 检索任务已全部作废，指示器同步熄灭，避免窗口唤醒后仍残留旋转动画
        self._stop_search_loading()

        # 2. 如果在 Mode A 且无搜索文本，清空列表释放行对象缓存
        self._panel_forced_open = False
        if self.current_mode == "A" and not self.search_edit.text().strip():
            self.table_model.set_items([])
            self._current_seen_paths.clear()

        # 3. 启动后台深度休眠定时器 (800ms 防抖)
        if hasattr(self, '_hibernate_timer') and not self._hibernate_timer.isActive():
            self._hibernate_timer.start()
    def _do_deep_hibernate(self):
        """进入深度后台休眠：收缩 SQLite 缓存、回收 Python 瞬态垃圾、调用 Windows 原生工作集修剪将物理内存降至最低"""
        if self.isVisible():
            return
        try:
            import gc
            gc.collect()
        except Exception:
            pass

        try:
            if hasattr(self, 'db') and self.db:
                self.db.shrink_memory()
        except Exception:
            pass

        if sys.platform == "win32":
            try:
                import ctypes
                h_proc = ctypes.windll.kernel32.GetCurrentProcess()
                
                # 1. 尝试 psapi.EmptyWorkingSet
                try:
                    psapi = ctypes.windll.psapi
                    psapi.EmptyWorkingSet.argtypes = [ctypes.c_void_p]
                    psapi.EmptyWorkingSet.restype = ctypes.c_int
                    psapi.EmptyWorkingSet(h_proc)
                except Exception:
                    pass

                # 2. 调用 kernel32.SetProcessWorkingSetSize 彻底释放非活动物理内存页面
                try:
                    kernel32 = ctypes.windll.kernel32
                    kernel32.SetProcessWorkingSetSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
                    kernel32.SetProcessWorkingSetSize.restype = ctypes.c_int
                    kernel32.SetProcessWorkingSetSize(h_proc, 0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)
                except Exception:
                    pass
            except Exception:
                pass
    def show_and_activate(self):
        """唤醒主窗口并复位选择状态至首行

        定位策略：用户从未拖动过窗口 -> 回当前屏幕正中 (启动器形态)；
        拖动过 -> 尊重用户摆放，恢复上次位置，仅在窗口完全落到所有
        屏幕之外 (如拔掉外接显示器) 时才兜底回正中，避免窗口丢失。
        """
        if hasattr(self, '_hibernate_timer') and self._hibernate_timer.isActive():
            self._hibernate_timer.stop()
        if hasattr(self, 'system_theme_timer') and not self.system_theme_timer.isActive():
            self._check_system_theme_change()
            self.system_theme_timer.start()

        if not (self._user_has_dragged and self._is_on_any_screen()):
            self._center_window()
        self.show()
        self.raise_()
        self.activateWindow()
        self.search_edit.setFocus()
        self.search_edit.selectAll()

        # 若曾因 close() 停止过后台线程，此处复活，恢复 Tier2 异步全盘检索
        self._ensure_background_tasks()

        # 唤醒时重建列表：隐藏期间 Mode A 会清空行缓存以省内存，
        # 且期间可能有新的使用记录，不重载会出现"唤出后列表空白/过时"
        self.reload_data()

        # 唤出时高亮与视口复位至第0项 (与主流启动器一致，清爽如初)
        if self.table_model.rowCount() > 0:
            self._navigate_to_row(0, -1)
            vsb = self.table_view.verticalScrollBar()
            if vsb:
                vsb.setValue(0)
        else:
            self._current_selected_row = -1
            if hasattr(self, 'row_delegate') and self.row_delegate:
                self.row_delegate.set_selected_row(-1)

    def toggle_mode(self):
        self.current_mode = "B" if self.current_mode == "A" else "A"
        self.reload_data()
        self._apply_mode_ui(recenter=False)

    def apply_theme(self, theme_id: str):
        """动态无缝切换皮肤主题 (支持 system / light / dark，实时重载 QSS、委托颜色、Kbd 徽标及深浅图标)"""
        self.theme_pref = theme_id
        th = get_theme(theme_id)
        self.current_theme_def = th
        cfg = ConfigManager.load()
        self.current_opacity = float(cfg.get("card_opacity", 1.0))
        self.setStyleSheet(build_qss(th, opacity=self.current_opacity))
        if hasattr(self, 'row_delegate'):
            self.row_delegate.set_theme_colors(
                th.accent_color,
                th.row_selected_bg,
                th.row_selected_border,
                th.row_hover_bg,
                th.row_hover_border
            )
        if hasattr(self, 'shortcut_hint'):
            kbd_style = f"background: {th.kbd_bg}; border: 1px solid {th.kbd_border}; border-radius: 4px; padding: 1px 6px; font-size: 10px; font-weight: 600; color: {th.kbd_text};"
            self.shortcut_hint.setText(
                f'<span style="{kbd_style}">↵ Enter</span> <span style="color:{th.text_secondary}; font-size:11px;">打开</span>'
                f'&nbsp;&nbsp;&nbsp;&nbsp;'
                f'<span style="{kbd_style}">Alt + ↵</span> <span style="color:{th.text_secondary}; font-size:11px;">定位目录</span>'
                f'&nbsp;&nbsp;&nbsp;&nbsp;'
                f'<span style="{kbd_style}">Esc</span> <span style="color:{th.text_secondary}; font-size:11px;">隐藏</span>'
            )
        if hasattr(self, 'search_icon_label'):
            s_icon_file = "icon_search_dark.png" if th.is_dark else "icon_search_light.png"
            sp = os.path.join(self.res_dir, s_icon_file)
            if os.path.exists(sp):
                pix = QPixmap(sp)
                self.search_icon_label.setPixmap(pix.scaled(18, 18, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        if hasattr(self, 'settings_btn'):
            icon_file = "icon_settings_dark.png" if th.is_dark else "icon_settings_light.png"
            p = os.path.join(self.res_dir, icon_file)
            if os.path.exists(p):
                self.settings_btn.setIcon(QIcon(p))
        if hasattr(self, 'search_loading'):
            # 指示器取主题强调色：深色下是沉浸紫，浅色下是高对比蓝，两级都足够醒目
            self.search_loading.set_color(th.accent_color)
        if hasattr(self, 'mode_toggle_btn'):
            wb_file = "icon_workbench_dark.png" if th.is_dark else "icon_workbench_light.png"
            cap_file = "icon_capsule_dark.png" if th.is_dark else "icon_capsule_light.png"
            self.wb_icon = QIcon(os.path.join(self.res_dir, wb_file))
            self.cap_icon = QIcon(os.path.join(self.res_dir, cap_file))
            self.mode_toggle_btn.setIcon(self.cap_icon if self.current_mode == "B" else self.wb_icon)
        if hasattr(self, 'central_card') and self.central_card:
            self.central_card.update()
        if hasattr(self, 'table_model') and self.table_model:
            self.table_model.set_theme_mode(th.is_dark)
        if hasattr(self, 'table_view') and hasattr(self.table_view, 'viewport') and self.table_view.viewport():
            self.table_view.viewport().update()
        if hasattr(self, 'tray_service') and self.tray_service:
            self.tray_service.update_theme(th.is_dark)

    def _check_system_theme_change(self):
        """当处于跟随系统模式时，轻量轮询检测 Windows 10/11 系统深浅色偏好变动"""
        cfg = ConfigManager.load()
        if cfg.get("theme", "system") == "system":
            sys_dark = is_windows_dark_mode()
            cur_is_dark = getattr(self.current_theme_def, 'is_dark', False)
            if sys_dark != cur_is_dark:
                self.apply_theme("system")

    def apply_opacity(self, opacity: float):
        """实时响应背景透明度滑块拖拽调整 (毫秒级热更新 QSS)"""
        self.current_opacity = opacity
        th = getattr(self, 'current_theme_def', get_theme("frost_white"))
        self.setStyleSheet(build_qss(th, opacity=opacity))
        if hasattr(self, 'central_card') and self.central_card:
            self.central_card.update()

    def _show_settings_dialog(self):
        """弹出非模态偏好设置对话框 (完全不阻塞主窗口点击与空白处操作)"""
        if not hasattr(self, 'settings_dialog') or self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(
                parent=self,
                on_theme_changed=self.apply_theme,
                on_opacity_changed=self.apply_opacity
            )
            self.settings_dialog.setWindowFlags(
                Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
            )
        
        if self.settings_dialog.isVisible():
            self.settings_dialog.hide()
            return

        # 默认出现在当前活动屏幕的正中心 (避开底部任务栏，智能多屏跟随)
        from PySide6.QtGui import QGuiApplication, QCursor
        screen = QGuiApplication.screenAt(QCursor.pos()) or self.screen() or QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            dlg_x = geo.x() + (geo.width() - self.settings_dialog.width()) // 2
            dlg_y = geo.y() + (geo.height() - self.settings_dialog.height()) // 2
            self.settings_dialog.move(dlg_x, dlg_y)
        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def hideEvent(self, event):
        """窗口隐藏统一入口 (此前存在两个同名定义相互覆盖，导致休眠调度成为死代码)"""
        self._prepare_background_hibernation()
        self._stop_all_navigation()
        if hasattr(self, 'settings_dialog') and self.settings_dialog and self.settings_dialog.isVisible():
            self.settings_dialog.hide()
        super().hideEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            self._stop_all_navigation()
        super().changeEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            # 与 eventFilter 共用同一实现，避免同一按键被两处各步进一次造成"跳行/失控"
            self._handle_nav_key_press(key, event.isAutoRepeat())
            return
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        # 上下键的按下/松开全部由 eventFilter 统一处理 (见 _handle_nav_key)，
        # 此处不再重复处理，避免同一次按键触发两次跳行
        super().keyReleaseEvent(event)

    def _init_shortcuts(self):
        cfg = ConfigManager.load()
        mode_key = cfg.get("mode_toggle_shortcut", "Tab")
        self.tab_shortcut = QShortcut(QKeySequence(mode_key), self.search_edit)
        self.tab_shortcut.activated.connect(self.toggle_mode)

        self.esc_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.esc_shortcut.activated.connect(self.hide)

        self.alt_enter = QShortcut(QKeySequence("Alt+Return"), self.table_view)
        self.alt_enter.activated.connect(self._open_selected_folder)
        self.alt_enter2 = QShortcut(QKeySequence("Alt+Return"), self.search_edit)
        self.alt_enter2.activated.connect(self._open_selected_folder)

    def update_mode_shortcut(self, new_key: str):
        """实时更新工作台变形快捷键"""
        if hasattr(self, 'tab_shortcut'):
            self.tab_shortcut.setKey(QKeySequence(new_key))
        if hasattr(self, 'mode_toggle_btn'):
            self.mode_toggle_btn.setToolTip(f"工作台模式切换 ({new_key})")

    def pause_shortcuts(self):
        """快捷键录制编辑期间，临时禁用窗口内所有快捷键"""
        for sc in (getattr(self, 'tab_shortcut', None),
                   getattr(self, 'esc_shortcut', None),
                   getattr(self, 'alt_enter', None),
                   getattr(self, 'alt_enter2', None)):
            if sc:
                sc.setEnabled(False)

    def resume_shortcuts(self):
        """快捷键录制编辑结束后，恢复窗口内所有快捷键"""
        for sc in (getattr(self, 'tab_shortcut', None),
                   getattr(self, 'esc_shortcut', None),
                   getattr(self, 'alt_enter', None),
                   getattr(self, 'alt_enter2', None)):
            if sc:
                sc.setEnabled(True)

    def _init_connections(self):
        # 异步深层磁盘全盘搜索定时器 (80ms 极轻防抖，仅在用户输入停顿间隙排队，绝不卡死打字主线程)
        self.async_search_timer = QTimer(self)
        self.async_search_timer.setSingleShot(True)
        self.async_search_timer.setInterval(80)
        self.async_search_timer.timeout.connect(self._on_async_search_timeout)

        # 检索 loading 兜底超时：若外部 Everything/Windows Search 迟迟不返回，
        # 也不能让指示器永久旋转（视觉上会像"卡死"）
        self._loading_timeout = QTimer(self)
        self._loading_timeout.setSingleShot(True)
        self._loading_timeout.setInterval(5000)
        self._loading_timeout.timeout.connect(self._stop_search_loading)

        self.search_edit.textChanged.connect(self._on_text_changed)
        self.search_edit.returnPressed.connect(self._open_selected_item)
        self.search_edit.installEventFilter(self)
        self.table_view.installEventFilter(self)
        if hasattr(self.table_view, 'viewport') and self.table_view.viewport():
            self.table_view.viewport().installEventFilter(self)
        self.central_card.installEventFilter(self)

        # 心跳续命安全导航引擎：纯内存状态追踪 + OS AutoRepeat 心跳续命 + 超时自杀
        self._held_key = None
        self._heartbeat = 0
        self._cruise_steps = 0

        # 1. 190ms 敏捷起跑侦测 (单次定时器，严密隔离单点与长按)
        self._hold_detect_timer = QTimer(self)
        self._hold_detect_timer.setSingleShot(True)
        self._hold_detect_timer.timeout.connect(self._on_hold_detect_timeout)

        # 2. 50Hz 电竞巡航定时器 (20ms 步频, 主线程占用率 < 15%)
        self._cruise_timer = QTimer(self)
        self._cruise_timer.setInterval(20)
        self._cruise_timer.timeout.connect(self._on_cruise_tick)

        self.settings_btn.clicked.connect(self._show_settings_dialog)
        self.mode_toggle_btn.clicked.connect(self.toggle_mode)
        self.table_view.clicked.connect(self._on_table_row_clicked)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        # 表头点击排序 (不用 setSortingEnabled：避免 Qt 在 reset 后自动重排并二次触发)
        self.table_view.horizontalHeader().sectionClicked.connect(self._on_header_clicked)

    def _on_text_changed(self, text: str):
        if not text.strip():
            # 用户主动清空搜索框：撤销"按上下键强制展开"状态，恢复极简胶囊形态
            self._panel_forced_open = False
        # 1. Tier 1 本地轻量缓存检索 (0ms 零延迟瞬间响应，打字即见，不产生丝毫按键等待感)
        self.reload_local_data()
        if self.current_mode == "A":
            self._apply_mode_ui(recenter=False)

        # 2. Tier 2 全盘深度异步检索 (极轻防抖排队)
        q = text.strip()
        if q and len(q) >= 2:
            self.async_search_timer.start()
        else:
            self.async_search_timer.stop()
            if hasattr(self, 'live_search_worker') and self.live_search_worker:
                self.live_search_worker.cancel_pending()
            self._stop_search_loading()

    def _start_search_loading(self):
        """进入深度检索态：点亮搜索行下方的旋转指示器 + 提示文案"""
        if hasattr(self, 'loading_row'):
            self.loading_row.show()
        if hasattr(self, 'search_loading'):
            self.search_loading.start()
        if hasattr(self, '_loading_timeout'):
            self._loading_timeout.start()

    def _stop_search_loading(self):
        """退出检索态：整行隐去 (结果到达 / 清空输入 / 窗口隐藏 / 兜底超时统一入口)"""
        if hasattr(self, 'search_loading'):
            self.search_loading.stop()
        if hasattr(self, 'loading_row'):
            self.loading_row.hide()
        if hasattr(self, '_loading_timeout'):
            self._loading_timeout.stop()

    def _on_async_search_timeout(self):
        spec = parse_query(self.search_edit.text())
        q = spec.text
        if q and len(q) >= 2 and hasattr(self, 'live_search_worker') and self.live_search_worker:
            self.live_search_worker.submit_search(q)
            self._start_search_loading()

    def _select_item_type(self, type_key: str):
        """类型药丸切换：按新类型重新检索并刷新视图

        必须走 reload_data() 重触发 Tier 2 全盘异步检索：像 "excel" 这种
        关键词的命中几乎全部来自全盘通道，只跑 Tier 1 本地库会得到空列表，
        且切回「全部」也保持空白，逼用户重新输入才能恢复搜索。
        异步 live 结果返回后由谓词按当前药丸过滤 (_on_async_results_ready)。
        """
        self._current_item_type = type_key
        self._nav_ensure_key = None
        self.reload_data()
        self.search_edit.setFocus()

    def reload_local_data(self):
        """Tier 1 本地瞬间秒出：毫秒级完成本地已索引历史命中并即时刷新视图 (0ms延迟)"""
        raw = self.search_edit.text()
        spec = parse_query(raw)
        q = spec.text
        # 数据可能已变化，放行上下键重新尝试加载空列表场景
        self._nav_ensure_key = None

        # 仅当完全未输入时才保持 Mode A 空列表；ext:xxx 等纯语法串仍应正常检索
        if self.current_mode == "A" and not raw.strip():
            self.table_model.set_items([])
            self._current_seen_paths.clear()
            return

        items = self.db.query_items(
            query=q,
            item_type=spec.type_key or self._current_item_type,
            limit=150,
            exts=spec.exts,
            mtime_after=spec.mtime_after
        )
        self._current_seen_paths = {it.target_path.lower() for it in items}
        self.table_model.set_items(items)
        # 数据被整体替换，排序若处于启用状态需重新套用，否则表头箭头与真实顺序不一致
        self._reapply_active_sort(preserve_selection=False)
        if items:
            self._navigate_to_row(0, -1)
        else:
            self._current_selected_row = -1
            if hasattr(self, 'row_delegate') and self.row_delegate:
                self.row_delegate.set_selected_row(-1)
            vp = getattr(self.table_view, 'viewport', lambda: None)()
            if vp:
                vp.update()

    def reload_data(self):
        """兼容接口：执行 Tier 1 本地检索并立即触发 Tier 2 异步检索"""
        self.reload_local_data()
        spec = parse_query(self.search_edit.text())
        q = spec.text
        # Tier 2 异步流式全盘检索 (交由单例常驻 Worker 安全排队，彻底消除多线程撕裂与闪退)
        if q and len(q) >= 2 and hasattr(self, 'live_search_worker') and self.live_search_worker:
            self.live_search_worker.submit_search(q)
            self._start_search_loading()

    def _on_async_results_ready(self, query: str, live_items: List[RecentItem]):
        spec = parse_query(self.search_edit.text())
        if query != spec.text:
            # 结果属于已过时的旧查询：新查询仍在途中，指示器必须继续旋转
            return
        self._stop_search_loading()

        item_type = spec.type_key or self._current_item_type
        to_append = []
        for lf in live_items:
            # 全盘 live 结果未经 SQL 过滤，这里按当前药丸/搜索语法做一次等价过滤
            if not item_matches_filters(lf, item_type, spec.exts, spec.mtime_after):
                continue
            path_lower = lf.target_path.lower()
            if path_lower not in self._current_seen_paths:
                self._current_seen_paths.add(path_lower)
                to_append.append(lf)

        if to_append:
            self.table_model.append_items(to_append)
            # 流式追加会让新条目落到末尾，启用排序时必须重排以维持顺序
            self._reapply_active_sort()
            total = self.table_model.rowCount()
            if self.current_mode == "A":
                self.resize(self.custom_width, self.custom_dropdown_height)

    def _on_header_clicked(self, column: int):
        """Mode B 表头点击排序：同列再点翻转升降序，换列则从升序开始。

        刻意不使用 setSortingEnabled(True)：Qt 会在模型 reset 后按旧指示器
        自动重排并再次触发排序，与数据源反复打架。这里只响应点击。
        """
        if column == self._sort_column:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = column
            self._sort_order = Qt.SortOrder.AscendingOrder

        self.table_view.horizontalHeader().setSortIndicator(self._sort_column, self._sort_order)
        self._reapply_active_sort()
        # 排序后把焦点还给搜索框，避免抢走焦点破坏上下键导航与直接输入
        self.search_edit.setFocus()

    def _reapply_active_sort(self, preserve_selection: bool = True):
        """按当前排序状态就地重排 (未启用排序时为空操作)。

        preserve_selection=True 时按 target_path 记忆并回填选中行，
        因为重排会让行号整体漂移，不回填的话高亮会落到其它条目上。
        """
        if self._sort_column < 0:
            return

        cur_item = None
        if preserve_selection:
            cur_row = getattr(self, '_current_selected_row', -1)
            if 0 <= cur_row:
                cur_item = self.table_model.get_item(cur_row)

        self.table_model.sort(self._sort_column, self._sort_order)

        if cur_item:
            for r in range(self.table_model.rowCount()):
                it = self.table_model.get_item(r)
                if it and it.target_path == cur_item.target_path:
                    self._navigate_to_row(r, -1)
                    break

    def trigger_background_scan(self):
        # 严禁在旧扫描线程仍在运行时覆盖引用：被覆盖的 QThread 会在存活状态下析构，
        # 触发 Qt qFatal → __fastfail (0xC0000409) 整个进程硬崩
        if self.worker and self.worker.isRunning():
            return
        self.worker = ScanWorker(self.scan_service)
        self.worker.scan_finished.connect(self._on_scan_finished)
        self.worker.start()

    def _on_scan_finished(self, new_count: int):
        self.reload_data()

    def get_selected_row(self) -> int:
        """获取当前高亮或聚焦行号 (纳秒级缓存读取，消除跨层循环探测)"""
        total = self.table_model.rowCount()
        if total == 0:
            return -1
        cur = getattr(self, '_current_selected_row', 0)
        if 0 <= cur < total:
            return cur
        ci = self.table_view.currentIndex()
        if ci.isValid() and 0 <= ci.row() < total:
            self._current_selected_row = ci.row()
            return ci.row()
        return 0

    def _ensure_navigable_data(self) -> bool:
        """上下键前置保障：Mode A 空查询时列表按设计保持为空，
        此时应先加载最近使用记录并展开下拉面板，否则按上下键永远"没反应"。"""
        if self.table_model.rowCount() > 0:
            return True
        query_key = self.search_edit.text()
        if query_key.strip():
            return False
        # 同一查询串只尝试加载一次，防止巡航状态机高频触碰数据库
        if self._nav_ensure_key == query_key:
            return False
        self._nav_ensure_key = query_key
        items = self.db.query_items(query="", item_type=self._current_item_type, limit=150)
        if not items:
            return False
        self._panel_forced_open = True
        self._current_seen_paths = {it.target_path.lower() for it in items}
        self.table_model.set_items(items)
        self._reapply_active_sort(preserve_selection=False)
        self._current_selected_row = -1
        self._apply_mode_ui(recenter=False)
        return True

    def select_next_row(self):
        """向下逐行切换选中 (0延迟瞬时原子响应，循环到底后返回第0行)"""
        if not self._ensure_navigable_data():
            return
        total = self.table_model.rowCount()
        cur_row = getattr(self, '_current_selected_row', -1)
        # 尚未建立选中态时，第一次按键落在首行，避免从"默认0行"再加1而跳过首项
        next_row = 0 if not (0 <= cur_row < total) else (cur_row + 1) % total
        self._navigate_to_row(next_row, cur_row)

    def select_prev_row(self):
        """向上逐行切换选中 (0延迟瞬时原子响应，循环到顶后返回最后一行)"""
        if not self._ensure_navigable_data():
            return
        total = self.table_model.rowCount()
        cur_row = getattr(self, '_current_selected_row', -1)
        prev_row = (total - 1) if not (0 <= cur_row < total) else (cur_row - 1 + total) % total
        self._navigate_to_row(prev_row, cur_row)

    def _stop_all_navigation(self):
        """全量无条件刹车：瞬间切断全部定时器与状态，绝对死死定格"""
        self._held_key = None
        self._heartbeat = 0
        self._cruise_steps = 0
        self._saw_repeat = False
        if hasattr(self, '_hold_detect_timer'):
            self._hold_detect_timer.stop()
        if hasattr(self, '_cruise_timer'):
            self._cruise_timer.stop()

    def _key_physical_state(self, key) -> Optional[bool]:
        """返回按键真实物理状态：True=仍按住, False=已松开, None=本平台无法查询。
        GetAsyncKeyState 是唯一直接查询硬件按键状态的依据 (实测空闲 0x0000 /
        按住 0x8000 / 松开 0x0000)，因此它是刹车的第一权威来源，比依赖
        KeyRelease 或自动重复心跳都要可靠得多。"""
        if sys.platform != "win32":
            return None
        global _GAKS
        if _GAKS is None:
            try:
                fn = ctypes.windll.user32.GetAsyncKeyState
                fn.argtypes = [ctypes.c_int]
                fn.restype = ctypes.c_short
                _GAKS = fn
            except Exception:
                _GAKS = False
        if not _GAKS:
            return None
        try:
            vk = 0x28 if key == Qt.Key.Key_Down else 0x26  # VK_DOWN / VK_UP
            return bool(_GAKS(vk) & 0x8000)
        except Exception:
            return None

    def _on_hold_detect_timeout(self):
        """400ms 起跑超时：确认长按意图后切入约 28Hz 平顺巡航"""
        if self._held_key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            self._heartbeat = time.perf_counter()
            self._cruise_steps = 0
            self._cruise_started_at = time.perf_counter()
            if hasattr(self, '_cruise_timer'):
                self._cruise_timer.start(35)

    def _on_cruise_tick(self):
        """巡航回调：物理按键检测为主 + 心跳/看门狗兜底 + 绝对熔断"""
        # 保护 1：状态已清空则立刻停止
        if not self._held_key:
            self._stop_all_navigation()
            return

        elapsed = time.perf_counter() - self._cruise_started_at

        # 保护 2：物理按键检测 (第一权威，最快路径)。真实松手瞬间刹停，
        # 且完全不依赖 KeyRelease / 自动重复是否被投递。
        state = self._key_physical_state(self._held_key)
        if state is False:
            self._stop_all_navigation()
            return

        if state is None:
            # 保护 3/4：仅在本平台无法查询物理按键时才退化为心跳兜底。
            # 若把心跳刹车无条件启用，正常长按会被误判成"丢失松手消息"，
            # 表现就是"长按只滚一两下就停"。
            if self._saw_repeat and (time.perf_counter() - self._heartbeat) > 0.6:
                self._stop_all_navigation()
                return
            if not self._saw_repeat and elapsed > max(1.5, self._repeat_delay_sec + 1.0):
                self._stop_all_navigation()
                return

        # 保护 5：绝对时长兜底熔断，防御按键物理卡死等极端情况
        if elapsed > 12.0:
            self._stop_all_navigation()
            return

        self._cruise_steps += 1
        if self._held_key == Qt.Key.Key_Down:
            self.select_next_row()
        elif self._held_key == Qt.Key.Key_Up:
            self.select_prev_row()

    def _navigate_to_row(self, target_row: int, old_row: int):
        """原子级无损快速设置选中行：纯内存标记 + 纳秒级轻量更新，0主线程阻塞"""
        self._current_selected_row = target_row
        if hasattr(self, 'row_delegate') and self.row_delegate:
            self.row_delegate.set_selected_row(target_row)
            self.row_delegate.hovered_row = -1 # 键盘介入时清除鼠标残留悬停

        idx = self.table_model.index(target_row, 0)
        sm = self.table_view.selectionModel()
        if sm:
            # 采用轻量 NoUpdate，免除全表扫描、选区重建与广播风暴
            sm.setCurrentIndex(idx, QItemSelectionModel.SelectionFlag.NoUpdate)

        vp = self.table_view.viewport()
        if vp:
            # 原生 EnsureVisible 自动平滑滚动对齐，配合无条件瞬时重绘，100% 杜绝 DWM 亚克力磨砂漏刷高亮行
            self.table_view.scrollTo(idx, QAbstractItemView.ScrollHint.EnsureVisible)
            vp.update()

    def _get_current_selected_item(self) -> Optional[RecentItem]:
        row = self.get_selected_row()
        if row >= 0:
            return self.table_model.get_item(row)
        return None

    def _open_selected_item(self):
        item = self._get_current_selected_item()
        if item:
            OpenService.open_item(item)
            self.hide()

    def _open_selected_folder(self):
        item = self._get_current_selected_item()
        if item:
            OpenService.open_containing_folder(item)
            self.hide()

    def _on_delegate_row_selected(self, row: int):
        """鼠标左键在视口按下即刻 0ms 瞬间响应：统一驱动单一数据源 _navigate_to_row 并保留搜索框聚焦"""
        old_row = getattr(self, '_current_selected_row', 0)
        self._navigate_to_row(row, old_row)
        self.search_edit.setFocus()

    def _on_table_row_clicked(self, index: QModelIndex):
        """鼠标单击行：统一驱动单一数据源 _navigate_to_row，确保全局唯一高亮选中"""
        if not index.isValid():
            return
        row = index.row()
        old_row = getattr(self, '_current_selected_row', 0)
        self._navigate_to_row(row, old_row)
        self.search_edit.setFocus()

    def _on_table_double_clicked(self, index: QModelIndex):
        """双击行：同步更新单一选中状态并打开目标文件/应用"""
        if not index.isValid():
            return
        row = index.row()
        old_row = getattr(self, '_current_selected_row', 0)
        self._navigate_to_row(row, old_row)
        item = self.table_model.get_item(row)
        if item:
            OpenService.open_item(item)
            self.hide()

    def _show_context_menu(self, pos: QPoint):
        item = self._get_current_selected_item()
        if not item:
            return

        is_dark = False
        if hasattr(self, 'current_theme_def') and self.current_theme_def:
            is_dark = getattr(self.current_theme_def, 'is_dark', False)
        icon_col = "#9CA3AF" if is_dark else "#666677"

        menu = QMenu(self)
        setup_modern_menu(menu, is_dark=is_dark)

        open_act = menu.addAction(create_vector_menu_icon("open", icon_col), "打开")
        open_act.triggered.connect(lambda: OpenService.open_item(item))

        if item.item_type == "app":
            admin_act = menu.addAction(create_vector_menu_icon("admin", icon_col), "以管理员身份运行")
            admin_act.triggered.connect(lambda: OpenService.run_as_admin(item))

        folder_act = menu.addAction(create_vector_menu_icon("folder", icon_col), "打开所在文件夹")
        folder_act.triggered.connect(lambda: OpenService.open_containing_folder(item))

        menu.addSeparator()

        copy_act = menu.addAction(create_vector_menu_icon("copy", icon_col), "复制文件路径")
        copy_act.triggered.connect(lambda: QApplication.clipboard().setText(item.target_path))

        pin_text = "取消置顶" if item.pinned else "置顶此项"
        pin_act = menu.addAction(create_vector_menu_icon("pin", icon_col), pin_text)
        pin_act.triggered.connect(lambda: self._toggle_pin(item))

        menu.addSeparator()
        del_act = menu.addAction(create_vector_menu_icon("delete", icon_col), "移除此记录")
        del_act.triggered.connect(lambda: self._delete_item(item))

        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def _toggle_pin(self, item: RecentItem):
        new_pinned = not bool(item.pinned)
        self.db.set_pinned(item.id, new_pinned)
        self.reload_data()

    def _delete_item(self, item: RecentItem):
        self.db.delete_item(item.id)
        self.reload_data()

    def stop_background_tasks(self):
        """统一回收全部后台 QThread。进程退出前必须调用：
        QThread 在仍运行时被析构会触发 Qt qFatal → __fastfail (0xC0000409) 硬崩。
        幂等：退出路径 (aboutToQuit / closeEvent / exec 返回后) 会重复调用。
        注意：不 disconnect 信号——连接需保留，否则 show_and_activate 复活线程后
        异步全盘检索结果将无人接收。"""
        if getattr(self, '_tasks_stopped', False):
            return
        self._tasks_stopped = True
        w = getattr(self, 'worker', None)
        if w and w.isRunning():
            if not w.wait(3000):
                w.terminate()
                w.wait(1000)
        lw = getattr(self, 'live_search_worker', None)
        if lw:
            lw.stop()

    def _ensure_background_tasks(self):
        """唤出时确保后台线程存活：窗口曾被 close() 停止后自动复活，避免搜索能力永久失效"""
        lw = getattr(self, 'live_search_worker', None)
        if lw and not lw.isRunning():
            lw.ensure_started()
        self._tasks_stopped = False

    def closeEvent(self, event):
        self.stop_background_tasks()
        super().closeEvent(event)

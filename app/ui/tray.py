"""
RecentHub 现代化系统托盘服务 (极简纯净菜单，无生硬Emoji，无粗糙旧式下划线)
"""

import os
from PySide6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QFileIconProvider
from PySide6.QtGui import QIcon, QAction
from PySide6.QtCore import QObject
from app.ui.menu_utils import create_vector_menu_icon, setup_modern_menu
from app.core.paths import resource_dir


class TrayService(QObject):
    def __init__(self, main_window, db, scan_service):
        super().__init__()
        self.main_window = main_window
        self.db = db
        self.scan_service = scan_service

        self.tray_icon = QSystemTrayIcon(self.main_window)
        
        # 加载专属高清极简图标
        icon_path = os.path.join(resource_dir(), "app_icon.png")
        if os.path.exists(icon_path):
            self.icon = QIcon(icon_path)
        else:
            provider = QFileIconProvider()
            self.icon = provider.icon(QFileIconProvider.IconType.Computer)
            
        self.tray_icon.setIcon(self.icon)
        self.tray_icon.setToolTip("RecentHub")

        self._init_menu()
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _init_menu(self):
        is_dark = False
        if hasattr(self.main_window, 'current_theme_def') and self.main_window.current_theme_def:
            is_dark = getattr(self.main_window.current_theme_def, 'is_dark', False)

        icon_col = "#9CA3AF" if is_dark else "#666677"
        menu = QMenu()
        setup_modern_menu(menu, is_dark=is_dark)

        show_act = menu.addAction(create_vector_menu_icon("show", icon_col), "显示 RecentHub")
        show_act.triggered.connect(self.show_window)

        scan_act = menu.addAction(create_vector_menu_icon("scan", icon_col), "重新扫描记录")
        scan_act.triggered.connect(self.main_window.trigger_background_scan)

        settings_act = menu.addAction(create_vector_menu_icon("settings", icon_col), "设置")
        settings_act.triggered.connect(self.main_window._show_settings_dialog)

        menu.addSeparator()

        clear_act = menu.addAction(create_vector_menu_icon("clear", icon_col), "清空所有缓存")
        clear_act.triggered.connect(self._clear_cache)

        menu.addSeparator()

        exit_act = menu.addAction(create_vector_menu_icon("exit", icon_col), "退出")
        exit_act.triggered.connect(QApplication.instance().quit)

        self.menu = menu
        self.tray_icon.setContextMenu(menu)

    def update_theme(self, is_dark: bool):
        """当主窗口切换主题模式时，热重载托盘右键菜单样式与矢量图标"""
        self._init_menu()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_window()

    def toggle_window(self, from_hotkey: bool = False):
        if self.main_window.isVisible():
            self.main_window.hide()
        else:
            if from_hotkey and self._is_fullscreen_dnd():
                return
            self.main_window.show_and_activate()

    def show_window(self):
        """幂等唤出主窗口并置前

        用于「再次双击/启动 exe」与托盘菜单「显示 RecentHub」——语义是"把窗口叫到
        前面来"，因此窗口已可见时不隐藏，只重新置前并聚焦输入框。
        桌面软件惯例如此：重复双击图标永远是唤出，不会把窗口收起来。
        (窗口显隐开关才走 toggle_window，绑在全局热键上，保持 Spotlight 手感)
        """
        self.main_window.show_and_activate()

    def _is_fullscreen_dnd(self) -> bool:
        """全屏免打扰：处于全屏 (游戏/观影) 时返回 True，快捷键唤出应静默忽略"""
        from app.core.config import ConfigManager
        if not ConfigManager.load().get("fullscreen_dnd", True):
            return False
        from app.services.fullscreen_service import FullscreenService
        win_id = int(self.main_window.winId()) if self.main_window else 0
        return FullscreenService.is_fullscreen_active(ignore_hwnd=win_id)

    def _clear_cache(self):
        self.db.clear_all()
        self.main_window.reload_data()

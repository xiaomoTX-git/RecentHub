"""
RecentHub 现代化极简偏好设置面板 (Minimalist Settings)
- 极致纯净：去除一切死板方框与繁冗文字，回归纯粹极简交互
- 皮肤管理：一排灵动精致的色彩药丸胶囊 (Pill Tags)，单选即换肤
- 透明度拖拽调整：支持 20% ~ 100% 自由滑块拖拽，实时毫秒级响应
- 快捷键自定义设置：全局唤出快捷键与工作台变形快捷键，点击即可快速录制
- 开机自启：原生极简复选开关
- 非模态友好设计：打开时完全不阻塞主窗口点击与空白处操作
"""

import os
from typing import Callable, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QWidget, QSlider, QScrollArea, QLineEdit,
    QListWidget, QListWidgetItem, QButtonGroup, QFrame
)
from PySide6.QtCore import Qt, QPoint, Signal, QTimer
from PySide6.QtGui import QCursor, QFont, QKeySequence

from app.core.config import ConfigManager
from app.core.paths import log_dir
from app.ui.themes import THEMES, get_theme, get_card_bg_with_opacity
from app.services.autostart_service import AutoStartService
from app.services.hotkey_service import HotkeyService


class SmoothOpacitySlider(QSlider):
    """丝滑流体透明度滑块组件 (点击即达、连续平滑无卡顿拖动)"""
    def __init__(self, parent=None):
        super().__init__(Qt.Orientation.Horizontal, parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            width = self.width() - 16
            if width > 0:
                pos = max(0, min(width, event.position().x() - 8))
                val = int(self.minimum() + (pos / width) * (self.maximum() - self.minimum()))
                self.setValue(val)
        super().mousePressEvent(event)



class ShortcutRecordButton(QPushButton):
    """极简现代快捷键录制按钮 (独占键盘输入、临时暂停全局/本地快捷键防误触、录制完平滑恢复)"""
    hotkey_recorded = Signal(str)
    recording_started = Signal()
    recording_finished = Signal()

    def __init__(self, hotkey_str: str = "Alt+Space", parent=None):
        super().__init__(parent)
        self.hotkey_str = hotkey_str
        self.is_recording = False
        self._update_label()
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clicked.connect(self._toggle_record)

    def _update_label(self):
        self.setText(f" {self.hotkey_str} ")

    def set_hotkey(self, hotkey_str: str):
        self.hotkey_str = hotkey_str
        self._stop_recording()

    def _toggle_record(self):
        if not self.is_recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        self.is_recording = True
        self.setText(" 请按下快捷键... ")

        # 1. 临时暂停全局热键，避免按下快捷键时触发唤出/收起窗口
        hk_svc = HotkeyService.get_instance()
        if hk_svc:
            hk_svc.pause()

        # 2. 独占捕获键盘输入，阻止事件向父级窗口及其他控件冒泡
        try:
            self.grabKeyboard()
        except Exception:
            pass

        self.setFocus()
        self.recording_started.emit()
        self.update()

    def _stop_recording(self):
        if not self.is_recording:
            self._update_label()
            return

        self.is_recording = False
        try:
            self.releaseKeyboard()
        except Exception:
            pass

        # 恢复全局热键
        hk_svc = HotkeyService.get_instance()
        if hk_svc:
            hk_svc.resume()

        self._update_label()
        self.clearFocus()
        self.recording_finished.emit()
        self.update()

    def focusOutEvent(self, event):
        if self.is_recording:
            self._stop_recording()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if not self.is_recording:
            super().keyPressEvent(event)
            return

        # 录制期间强行拦截消费所有按键，绝不传递给任何外部快捷键或父级窗口
        event.accept()

        key = event.key()
        modifiers = event.modifiers()

        # 单独按下 Esc 视为取消录制，恢复原样，决不关闭窗口
        if key == Qt.Key.Key_Escape and not modifiers:
            self._stop_recording()
            return

        # 智能双击修饰键检测 (连续敲击两下 Ctrl 键自动识别录制为 "双击 Ctrl")
        if key in (Qt.Key.Key_Control,):
            import time
            now = time.time()
            if hasattr(self, '_last_ctrl_tap_time') and (0.05 <= now - self._last_ctrl_tap_time <= 0.45):
                self.hotkey_str = "双击 Ctrl"
                self._stop_recording()
                self.hotkey_recorded.emit("双击 Ctrl")
                return
            self._last_ctrl_tap_time = now
            return

        if key in (Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        parts = []
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("Win")

        key_name = ""
        if key == Qt.Key.Key_Space:
            key_name = "Space"
        elif key == Qt.Key.Key_Tab:
            key_name = "Tab"
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            key_name = "Enter"
        elif Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12:
            key_name = f"F{key - Qt.Key.Key_F1 + 1}"
        else:
            key_name = QKeySequence(key).toString().strip()

        if not key_name:
            return

        parts.append(key_name)
        new_hotkey = "+".join(parts)

        self.hotkey_str = new_hotkey
        self._stop_recording()
        self.hotkey_recorded.emit(new_hotkey)


class SettingsDialog(QDialog):
    def __init__(
        self,
        parent=None,
        on_theme_changed: Optional[Callable[[str], None]] = None,
        on_opacity_changed: Optional[Callable[[float], None]] = None
    ):
        super().__init__(parent)
        self.parent_window = parent
        self.on_theme_changed = on_theme_changed
        self.on_opacity_changed = on_opacity_changed
        self.cfg = ConfigManager.load()
        saved_th = self.cfg.get("theme", "system")
        if saved_th in ("frost_white", "sunset_amber"):
            saved_th = "light"
        elif saved_th in ("obsidian_dark", "nord_aurora", "cyberpunk_neon"):
            saved_th = "dark"
        self.current_theme_id = saved_th
        self.current_opacity = float(self.cfg.get("card_opacity", 1.0))

        # 防抖持久化定时器 (解耦拖动时的高频写磁盘，保证 60FPS 极速丝滑)
        self.opacity_save_timer = QTimer(self)
        self.opacity_save_timer.setSingleShot(True)
        self.opacity_save_timer.setInterval(200)
        self.opacity_save_timer.timeout.connect(self._persist_opacity)

        self.setWindowTitle("RecentHub 设置")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(540, 600)

        self._drag_pos: Optional[QPoint] = None
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(10, 10, 10, 10)

        self.card = QWidget(self)
        self.card.setObjectName("SettingsCard")
        self.card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 18, 22, 18)
        card_layout.setSpacing(14)
        root_layout.addWidget(self.card)

        # 1. 顶部标题行
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QLabel("设置")
        t_font = QFont()
        t_font.setBold(True)
        t_font.setPixelSize(15)
        self.title_label.setFont(t_font)
        title_row.addWidget(self.title_label)

        title_row.addStretch()

        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("CloseBtn")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_btn.clicked.connect(self.close)
        title_row.addWidget(self.close_btn)
        card_layout.addLayout(title_row)

        # 中部滚动区：设置项较多，小屏 / 高缩放下可滚动查看全部内容
        scroll = QScrollArea()
        scroll.setObjectName("SettingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("SettingsContent")
        body = QVBoxLayout(content)
        body.setContentsMargins(0, 0, 8, 0)
        body.setSpacing(14)
        scroll.setWidget(content)
        card_layout.addWidget(scroll, 1)

        # 2. 皮肤管理 (一行极简灵动药丸胶囊)
        theme_section = QVBoxLayout()
        theme_section.setSpacing(8)

        sec_title = QLabel("界面主题")
        sec_title.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.7;")
        theme_section.addWidget(sec_title)

        pills_layout = QHBoxLayout()
        pills_layout.setSpacing(8)
        self.theme_btns = {}

        THEME_CHOICES = [
            ("system", "跟随系统"),
            ("light", "浅色"),
            ("dark", "深色")
        ]
        for tid, tname in THEME_CHOICES:
            btn = QPushButton(f"● {tname}")
            btn.setObjectName("ThemePill")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            if tid == self.current_theme_id:
                btn.setChecked(True)
            btn.clicked.connect(lambda checked, t=tid: self._select_theme(t))
            self.theme_btns[tid] = btn
            pills_layout.addWidget(btn)

        theme_section.addLayout(pills_layout)
        body.addLayout(theme_section)

        # 3. 背景透明度拖拽调节 (20% ~ 100%)
        opacity_section = QVBoxLayout()
        opacity_section.setSpacing(6)
        
        op_header = QHBoxLayout()
        op_title = QLabel("背景透明度")
        op_title.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.7;")
        op_header.addWidget(op_title)
        op_header.addStretch()

        saved_op_pct = int(self.current_opacity * 100)
        self.opacity_val_lbl = QLabel(f"{saved_op_pct}%")
        self.opacity_val_lbl.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.85;")
        op_header.addWidget(self.opacity_val_lbl)
        opacity_section.addLayout(op_header)

        self.opacity_slider = SmoothOpacitySlider(self)
        self.opacity_slider.setObjectName("OpacitySlider")
        self.opacity_slider.setRange(20, 100)
        self.opacity_slider.setValue(saved_op_pct)
        self.opacity_slider.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.opacity_slider.valueChanged.connect(self._on_opacity_slider_changed)
        self.opacity_slider.sliderReleased.connect(self._persist_opacity)
        opacity_section.addWidget(self.opacity_slider)
        body.addLayout(opacity_section)

        # 4. 快捷键设置 (支持全局热键与模式变形按键自定义录制)
        hotkey_section = QVBoxLayout()
        hotkey_section.setSpacing(8)
        hk_title = QLabel("快捷键设置")
        hk_title.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.7;")
        hotkey_section.addWidget(hk_title)

        # 全局呼出热键行
        row_global = QHBoxLayout()
        lbl_global = QLabel("全局唤出 / 隐藏")
        lbl_global.setStyleSheet("font-size: 12px;")
        row_global.addWidget(lbl_global)
        row_global.addStretch()

        saved_global_hk = self.cfg.get("global_hotkey", "Alt+Space")
        self.global_hk_btn = ShortcutRecordButton(saved_global_hk)
        self.global_hk_btn.setObjectName("ShortcutBtn")
        self.global_hk_btn.hotkey_recorded.connect(self._on_global_hotkey_recorded)
        self.global_hk_btn.recording_started.connect(self._on_recording_started)
        self.global_hk_btn.recording_finished.connect(self._on_recording_finished)
        row_global.addWidget(self.global_hk_btn)

        self.double_ctrl_btn = QPushButton("双击 Ctrl")
        self.double_ctrl_btn.setObjectName("PresetHkBtn")
        self.double_ctrl_btn.setToolTip("设置为按两下 Ctrl 键盲操极速呼出")
        self.double_ctrl_btn.clicked.connect(lambda: self._on_global_hotkey_recorded("双击 Ctrl"))
        row_global.addWidget(self.double_ctrl_btn)

        self.reset_global_btn = QPushButton("默认")
        self.reset_global_btn.setObjectName("ResetHkBtn")
        self.reset_global_btn.setToolTip("恢复为默认快捷键 Alt+Space")
        self.reset_global_btn.clicked.connect(lambda: self._on_global_hotkey_recorded("Alt+Space"))
        row_global.addWidget(self.reset_global_btn)
        hotkey_section.addLayout(row_global)

        # 窗口变形热键行
        row_mode = QHBoxLayout()
        lbl_mode = QLabel("工作台变形切换")
        lbl_mode.setStyleSheet("font-size: 12px;")
        row_mode.addWidget(lbl_mode)
        row_mode.addStretch()

        saved_mode_hk = self.cfg.get("mode_toggle_shortcut", "Tab")
        self.mode_hk_btn = ShortcutRecordButton(saved_mode_hk)
        self.mode_hk_btn.setObjectName("ShortcutBtn")
        self.mode_hk_btn.hotkey_recorded.connect(self._on_mode_hotkey_recorded)
        self.mode_hk_btn.recording_started.connect(self._on_recording_started)
        self.mode_hk_btn.recording_finished.connect(self._on_recording_finished)
        row_mode.addWidget(self.mode_hk_btn)

        self.reset_mode_btn = QPushButton("默认")
        self.reset_mode_btn.setObjectName("ResetHkBtn")
        self.reset_mode_btn.setToolTip("恢复为默认快捷键 Tab")
        self.reset_mode_btn.clicked.connect(lambda: self._on_mode_hotkey_recorded("Tab"))
        row_mode.addWidget(self.reset_mode_btn)
        hotkey_section.addLayout(row_mode)

        self.hk_status_tip = QLabel("")
        self.hk_status_tip.setStyleSheet("font-size: 11px; color: #10B981; padding-left: 2px;")
        hotkey_section.addWidget(self.hk_status_tip)

        body.addLayout(hotkey_section)

        # 5. 系统集成 (开机自启)
        sys_section = QVBoxLayout()
        sys_section.setSpacing(6)
        sys_title = QLabel("系统启动")
        sys_title.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.7;")
        sys_section.addWidget(sys_title)

        self.autostart_cb = QCheckBox("开机时静默启动并常驻托盘 (不弹出主窗口)")
        self.autostart_cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.autostart_cb.setChecked(AutoStartService.is_enabled())
        self.autostart_cb.toggled.connect(self._on_autostart_toggled)
        sys_section.addWidget(self.autostart_cb)

        self.fullscreen_dnd_cb = QCheckBox("全屏免打扰：检测到打游戏或看电影时不响应快捷键唤醒")
        self.fullscreen_dnd_cb.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cfg = ConfigManager.load()
        self.fullscreen_dnd_cb.setChecked(cfg.get("fullscreen_dnd", True))
        self.fullscreen_dnd_cb.toggled.connect(self._on_fullscreen_dnd_toggled)
        sys_section.addWidget(self.fullscreen_dnd_cb)
        body.addLayout(sys_section)

        # 6. 诊断 (运行日志与自助排查入口)
        diag_section = QVBoxLayout()
        diag_section.setSpacing(6)
        diag_title = QLabel("诊断")
        diag_title.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.7;")
        diag_section.addWidget(diag_title)

        diag_row = QHBoxLayout()
        self.open_log_btn = QPushButton("打开日志目录")
        self.open_log_btn.setObjectName("PresetHkBtn")
        self.open_log_btn.setToolTip("遇到异常时可直接查看 recenthub.log 定位问题")
        self.open_log_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.open_log_btn.clicked.connect(self._open_log_dir)
        diag_row.addWidget(self.open_log_btn)
        diag_row.addStretch()
        diag_section.addLayout(diag_row)

        self.log_hint_lbl = QLabel("运行日志按 1MB 自动轮转保存在数据目录 logs 下")
        self.log_hint_lbl.setStyleSheet("font-size: 11px; opacity: 0.60; padding: 2px 0;")
        diag_section.addWidget(self.log_hint_lbl)
        body.addLayout(diag_section)

        # 7. 排除规则 (自助管理不再收录的目录 / 文件名 / 扩展名)
        rules_section = QVBoxLayout()
        rules_section.setSpacing(8)
        rules_title = QLabel("排除规则")
        rules_title.setStyleSheet("font-size: 12px; font-weight: 600; opacity: 0.7;")
        rules_section.addWidget(rules_title)

        rule_type_row = QHBoxLayout()
        rule_type_row.setSpacing(6)
        self.rule_type_group = QButtonGroup(self)
        self.rule_type_group.setExclusive(True)
        self.rule_type_btns = {}
        for rk, rlabel in (
            ("path_prefix", "目录前缀"),
            ("name_contains", "文件名包含"),
            ("extension", "扩展名"),
        ):
            rbtn = QPushButton(rlabel)
            rbtn.setObjectName("FilterPill")
            rbtn.setCheckable(True)
            rbtn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            rbtn.setChecked(rk == "path_prefix")
            self.rule_type_group.addButton(rbtn)
            self.rule_type_btns[rk] = rbtn
            rule_type_row.addWidget(rbtn)
        rule_type_row.addStretch()
        rules_section.addLayout(rule_type_row)

        rule_input_row = QHBoxLayout()
        rule_input_row.setSpacing(6)
        self.rule_input = QLineEdit()
        self.rule_input.setObjectName("RuleInput")
        self.rule_input.setPlaceholderText("如 D:\\Temp   或  缓存   或  .tmp")
        self.rule_input.returnPressed.connect(self._on_add_rule)
        rule_input_row.addWidget(self.rule_input, 1)
        self.add_rule_btn = QPushButton("添加")
        self.add_rule_btn.setObjectName("PresetHkBtn")
        self.add_rule_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.add_rule_btn.clicked.connect(self._on_add_rule)
        rule_input_row.addWidget(self.add_rule_btn)
        rules_section.addLayout(rule_input_row)

        self.rule_list = QListWidget()
        self.rule_list.setObjectName("RuleList")
        self.rule_list.setFixedHeight(96)
        rules_section.addWidget(self.rule_list)

        rule_action_row = QHBoxLayout()
        rule_action_row.addStretch()
        self.remove_rule_btn = QPushButton("删除选中")
        self.remove_rule_btn.setObjectName("ResetHkBtn")
        self.remove_rule_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.remove_rule_btn.clicked.connect(self._on_remove_rule)
        rule_action_row.addWidget(self.remove_rule_btn)
        self.clear_rules_btn = QPushButton("清空")
        self.clear_rules_btn.setObjectName("ResetHkBtn")
        self.clear_rules_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.clear_rules_btn.clicked.connect(self._on_clear_rules)
        rule_action_row.addWidget(self.clear_rules_btn)
        rules_section.addLayout(rule_action_row)

        self.rule_hint_lbl = QLabel("命中的已收录条目会立即从列表中移除")
        self.rule_hint_lbl.setStyleSheet("font-size: 11px; opacity: 0.60;")
        rules_section.addWidget(self.rule_hint_lbl)
        body.addLayout(rules_section)

        # 8. 极简速查说明 (仅一行轻质中性提示)
        self.shortcut_hint_lbl = QLabel(
            "↓/↑ 键盘选词  ·  Enter 立即打开  ·  Alt+Enter 定位目录  ·  Esc 隐藏"
        )
        self.shortcut_hint_lbl.setStyleSheet("font-size: 11px; opacity: 0.60; padding: 2px 0;")
        body.addWidget(self.shortcut_hint_lbl)

        # 9. 底部完成按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.done_btn = QPushButton("完成")
        self.done_btn.setObjectName("DoneBtn")
        self.done_btn.setFixedSize(72, 28)
        self.done_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.done_btn.clicked.connect(self.close)
        btn_row.addWidget(self.done_btn)
        card_layout.addLayout(btn_row)

        # 首次呈现时载入既有排除规则
        self._refresh_rules()

    def _on_opacity_slider_changed(self, val: int):
        op_float = val / 100.0
        self.current_opacity = op_float
        self.opacity_val_lbl.setText(f"{val}%")
        
        # 内存级热重绘，毫秒级无损 60FPS 响应
        self._apply_style()
        if self.on_opacity_changed:
            self.on_opacity_changed(op_float)

        self.opacity_save_timer.start()

    def _persist_opacity(self):
        """防抖异步持久化透明度配置到磁盘"""
        cfg = ConfigManager.load()
        cfg["card_opacity"] = self.current_opacity
        ConfigManager.save(cfg)

    def _on_recording_started(self):
        if self.parent_window and hasattr(self.parent_window, "pause_shortcuts"):
            self.parent_window.pause_shortcuts()

    def _on_recording_finished(self):
        if self.parent_window and hasattr(self.parent_window, "resume_shortcuts"):
            self.parent_window.resume_shortcuts()

    def keyPressEvent(self, event):
        # 录制期间强行拦截 Esc，防止对话框意外关闭
        is_rec_global = getattr(self.global_hk_btn, 'is_recording', False)
        is_rec_mode = getattr(self.mode_hk_btn, 'is_recording', False)
        if is_rec_global or is_rec_mode:
            event.accept()
            return
        super().keyPressEvent(event)

    def _on_global_hotkey_recorded(self, new_hk: str):
        hk_svc = HotkeyService.get_instance()
        if hk_svc:
            ok = hk_svc.update_hotkey(new_hk)
            if ok:
                self.global_hk_btn.set_hotkey(new_hk)
                self.hk_status_tip.setText(f"✓ 全局热键已生效：{new_hk}")
                self.hk_status_tip.setStyleSheet("font-size: 11px; color: #10B981;")
            else:
                self.hk_status_tip.setText(f"✕ 快捷键 [{new_hk}] 冲突被系统占用，请尝试其他组合")
                self.hk_status_tip.setStyleSheet("font-size: 11px; color: #EF4444;")
        else:
            cfg = ConfigManager.load()
            cfg["global_hotkey"] = new_hk
            ConfigManager.save(cfg)
            self.global_hk_btn.set_hotkey(new_hk)
            self.hk_status_tip.setText(f"✓ 已保存全局热键：{new_hk}")

    def _on_mode_hotkey_recorded(self, new_hk: str):
        cfg = ConfigManager.load()
        cfg["mode_toggle_shortcut"] = new_hk
        ConfigManager.save(cfg)
        self.mode_hk_btn.set_hotkey(new_hk)
        if self.parent_window and hasattr(self.parent_window, "update_mode_shortcut"):
            self.parent_window.update_mode_shortcut(new_hk)
        self.hk_status_tip.setText(f"✓ 工作台变形热键已更新为：{new_hk}")
        self.hk_status_tip.setStyleSheet("font-size: 11px; color: #10B981;")

    def _select_theme(self, theme_id: str):
        self.current_theme_id = theme_id
        for tid, btn in self.theme_btns.items():
            btn.setChecked(tid == theme_id)

        cfg = ConfigManager.load()
        cfg["theme"] = theme_id
        th = get_theme(theme_id)
        cfg["accent_color"] = th.accent_color
        cfg["accent_hover_color"] = th.accent_hover
        ConfigManager.save(cfg)

        self._apply_style()
        if self.on_theme_changed:
            self.on_theme_changed(theme_id)

    def _on_autostart_toggled(self, checked: bool):
        AutoStartService.set_enabled(checked)
        cfg = ConfigManager.load()
        cfg["auto_start"] = checked
        ConfigManager.save(cfg)

    def _on_fullscreen_dnd_toggled(self, checked: bool):
        cfg = ConfigManager.load()
        cfg["fullscreen_dnd"] = checked
        ConfigManager.save(cfg)

    def _open_log_dir(self):
        """打开日志目录，便于用户自助排查运行异常"""
        try:
            os.startfile(log_dir())
        except Exception:
            # 资源管理器不可用等极端情况：静默忽略，绝不因诊断按钮而弹错
            pass

    # ---- 排除规则管理 ----

    RULE_TYPE_LABELS = {
        "path_prefix": "目录",
        "name_contains": "文件名",
        "extension": "扩展名",
    }

    def _db(self):
        """取主窗口持有的数据库实例 (取不到时调用方静默降级)"""
        return getattr(self.parent_window, "db", None)

    def _current_rule_type(self) -> str:
        for rk, btn in self.rule_type_btns.items():
            if btn.isChecked():
                return rk
        return "path_prefix"

    def _refresh_rules(self):
        """把库中既有规则渲染到列表 (id 存在 UserRole 里，供删除时定位)"""
        db = self._db()
        if db is None or not hasattr(self, 'rule_list'):
            return
        self.rule_list.clear()
        for rule in db.get_excluded_rules():
            label = self.RULE_TYPE_LABELS.get(rule.rule_type, rule.rule_type)
            list_item = QListWidgetItem(f"{label} · {rule.pattern}")
            list_item.setData(Qt.ItemDataRole.UserRole, rule.id)
            self.rule_list.addItem(list_item)

    def _on_add_rule(self):
        db = self._db()
        pattern = self.rule_input.text().strip()
        if db is None or not pattern:
            return
        db.add_excluded_rule(self._current_rule_type(), pattern)
        self.rule_input.clear()
        self._apply_rules_now()

    def _on_remove_rule(self):
        db = self._db()
        current = self.rule_list.currentItem()
        if db is None or current is None:
            return
        rule_id = current.data(Qt.ItemDataRole.UserRole)
        if rule_id is not None:
            db.remove_excluded_rule(int(rule_id))
        self._apply_rules_now()

    def _on_clear_rules(self):
        db = self._db()
        if db is None:
            return
        db.clear_excluded_rules()
        self._apply_rules_now()

    def _apply_rules_now(self):
        """规则变更后立即清除已入库的命中条目并刷新主窗口列表 (即时生效)"""
        db = self._db()
        if db is None:
            return
        db.purge_excluded_items(db.get_excluded_rules())
        self._refresh_rules()
        pw = self.parent_window
        if pw is not None and hasattr(pw, "reload_data"):
            pw.reload_data()

    def _apply_style(self):
        th = get_theme(self.current_theme_id)
        card_bg = get_card_bg_with_opacity(th.card_bg, self.current_opacity)
        
        for tid, btn in self.theme_btns.items():
            b_th = get_theme(tid)
            is_active = (tid == self.current_theme_id)
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton#ThemePill {{
                        background: {b_th.accent_color};
                        color: #FFFFFF;
                        border: 1px solid {b_th.accent_color};
                        border-radius: 8px;
                        padding: 6px 14px;
                        font-size: 11px;
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton#ThemePill {{
                        background: {th.btn_bg};
                        color: {th.text_primary};
                        border: 1px solid {th.btn_border};
                        border-radius: 8px;
                        padding: 6px 14px;
                        font-size: 11px;
                        font-weight: 500;
                    }}
                    QPushButton#ThemePill:hover {{
                        background: {th.btn_hover_bg};
                    }}
                """)

        self.setStyleSheet(f"""
            QDialog {{
                background: transparent;
            }}
            #SettingsCard {{
                background-color: {card_bg};
                border: {th.card_border};
                border-radius: 14px;
            }}
            QLabel {{
                color: {th.text_primary};
                border: none;
                background: transparent;
            }}
            QCheckBox {{
                color: {th.text_primary};
                font-size: 12px;
                border: none;
                background: transparent;
                spacing: 8px;
            }}
            QSlider#OpacitySlider {{
                min-height: 22px;
            }}
            QSlider#OpacitySlider::groove:horizontal {{
                height: 4px;
                background: {th.btn_border};
                border-radius: 2px;
            }}
            QSlider#OpacitySlider::sub-page:horizontal {{
                background: {th.accent_color};
                border-radius: 2px;
            }}
            QSlider#OpacitySlider::handle:horizontal {{
                background: #FFFFFF;
                border: 1px solid rgba(0, 0, 0, 0.15);
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider#OpacitySlider::handle:horizontal:hover {{
                border-color: {th.accent_color};
            }}
            #ShortcutBtn {{
                background-color: {th.btn_bg};
                border: 1px solid {th.btn_border};
                border-radius: 6px;
                color: {th.text_primary};
                font-size: 12px;
                font-weight: 600;
                padding: 4px 10px;
                min-width: 100px;
            }}
            #ShortcutBtn:focus, #ShortcutBtn:hover {{
                border-color: {th.accent_color};
                background-color: {th.btn_hover_bg};
            }}
            #PresetHkBtn {{
                background: {th.btn_bg};
                border: 1px solid {th.btn_border};
                border-radius: 6px;
                color: {th.text_primary};
                font-size: 11px;
                font-weight: 500;
                padding: 4px 8px;
            }}
            #PresetHkBtn:hover {{
                color: {th.accent_color};
                border-color: {th.accent_color};
                background: {th.btn_hover_bg};
            }}
            #ResetHkBtn {{
                background: transparent;
                border: none;
                color: {th.text_secondary};
                font-size: 11px;
                padding: 4px 6px;
            }}
            #ResetHkBtn:hover {{
                color: {th.accent_color};
            }}
            #CloseBtn {{
                background: transparent;
                border: none;
                color: {th.text_secondary};
                font-size: 12px;
                border-radius: 11px;
            }}
            #CloseBtn:hover {{
                background: rgba(255, 0, 0, 0.15);
                color: #FF4D4F;
            }}
            #SettingsScroll, #SettingsContent {{
                background: transparent;
                border: none;
            }}
            #FilterPill {{
                background-color: {th.btn_bg};
                border: 1px solid {th.btn_border};
                border-radius: 9px;
                color: {th.text_secondary};
                font-size: 11px;
                font-weight: 500;
                padding: 3px 10px;
            }}
            #FilterPill:hover {{
                background-color: {th.btn_hover_bg};
                color: {th.text_primary};
            }}
            #FilterPill:checked {{
                background-color: {th.accent_color};
                border-color: {th.accent_color};
                color: #FFFFFF;
                font-weight: 600;
            }}
            #RuleInput {{
                background-color: {th.btn_bg};
                border: 1px solid {th.btn_border};
                border-radius: 6px;
                color: {th.text_primary};
                font-size: 12px;
                padding: 4px 8px;
            }}
            #RuleInput:focus {{
                border-color: {th.accent_color};
            }}
            #RuleList {{
                background-color: {th.btn_bg};
                border: 1px solid {th.btn_border};
                border-radius: 6px;
                color: {th.text_primary};
                font-size: 12px;
                outline: none;
            }}
            #RuleList::item {{
                padding: 4px 6px;
                border-radius: 4px;
            }}
            #RuleList::item:selected {{
                background-color: {th.accent_color};
                color: #FFFFFF;
            }}
            #DoneBtn {{
                background-color: {th.accent_color};
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }}
            #DoneBtn:hover {{
                background-color: {th.accent_hover};
            }}
        """)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

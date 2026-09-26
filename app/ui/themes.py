"""
RecentHub 现代化黑白极简主题系统 (Minimalist Black & White System)
只保留纯净纯粹的两套设计与系统自适应：
1. system - 跟随系统 (自动检测 Windows 10/11 深浅色设置并实时跟随)
2. light  - 浅色纯白 (透白冰霜微光，经典灵动)
3. dark   - 深色暗夜 (Raycast 级黑曜石深邃黑，沉浸专注)
"""

import sys
import winreg
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ThemeDefinition:
    id: str
    name: str
    description: str
    is_dark: bool
    card_bg: str
    card_border: str
    accent_color: str
    accent_hover: str
    text_primary: str
    text_secondary: str
    text_placeholder: str
    row_selected_bg: str
    row_selected_border: str
    row_hover_bg: str
    row_hover_border: str
    kbd_bg: str
    kbd_border: str
    kbd_text: str
    btn_bg: str
    btn_border: str
    btn_hover_bg: str


# 核心两套极致黑白质感设计
THEMES: Dict[str, ThemeDefinition] = {
    # 1. 浅色 (通透冷白微霜，明朗通透)
    "light": ThemeDefinition(
        id="light",
        name="浅色",
        description="纯净透亮冷白微霜，Windows 经典雅致",
        is_dark=False,
        card_bg="rgba(255, 255, 255, 0.65)",
        card_border="1px solid rgba(255, 255, 255, 0.90)",
        accent_color="#0067C0",
        accent_hover="#1875D1",
        text_primary="#181824",
        text_secondary="#666677",
        text_placeholder="#8A8C9E",
        row_selected_bg="rgba(0, 103, 192, 0.10)",
        row_selected_border="rgba(0, 103, 192, 0.50)",
        row_hover_bg="rgba(0, 0, 0, 0.04)",
        row_hover_border="rgba(0, 0, 0, 0.08)",
        kbd_bg="rgba(255, 255, 255, 0.85)",
        kbd_border="rgba(0, 0, 0, 0.10)",
        kbd_text="#2C2C3A",
        btn_bg="rgba(0, 0, 0, 0.05)",
        btn_border="rgba(0, 0, 0, 0.08)",
        btn_hover_bg="rgba(0, 0, 0, 0.10)"
    ),

    # 2. 深色 (Raycast 黑曜石深邃黑，沉浸通透)
    "dark": ThemeDefinition(
        id="dark",
        name="深色",
        description="Raycast 纯黑曜石深邃沉浸，专注无扰",
        is_dark=True,
        card_bg="rgba(22, 22, 28, 0.72)",
        card_border="1px solid rgba(255, 255, 255, 0.16)",
        accent_color="#8B5CF6",
        accent_hover="#A78BFA",
        text_primary="#F3F4F6",
        text_secondary="#9CA3AF",
        text_placeholder="#6B7280",
        row_selected_bg="rgba(255, 255, 255, 0.16)",
        row_selected_border="rgba(139, 92, 246, 0.65)",
        row_hover_bg="rgba(255, 255, 255, 0.06)",
        row_hover_border="rgba(255, 255, 255, 0.12)",
        kbd_bg="rgba(255, 255, 255, 0.12)",
        kbd_border="rgba(255, 255, 255, 0.20)",
        kbd_text="#E5E7EB",
        btn_bg="rgba(255, 255, 255, 0.10)",
        btn_border="rgba(255, 255, 255, 0.16)",
        btn_hover_bg="rgba(255, 255, 255, 0.18)"
    )
}

# 兼容旧版本主题 ID 映射
_LEGACY_MAP = {
    "frost_white": "light",
    "sunset_amber": "light",
    "obsidian_dark": "dark",
    "nord_aurora": "dark",
    "cyberpunk_neon": "dark"
}


def is_windows_dark_mode() -> bool:
    """检测当前 Windows 10/11 系统是否处于深色模式"""
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return val == 0
    except Exception:
        return False


def get_effective_theme_id(pref_id: str) -> str:
    """将用户偏好 (system / light / dark) 转换为实际渲染的实体主题 (light 或 dark)"""
    norm = _LEGACY_MAP.get(pref_id, pref_id)
    if norm == "system":
        return "dark" if is_windows_dark_mode() else "light"
    if norm in THEMES:
        return norm
    return "light"


def get_theme(theme_id: str) -> ThemeDefinition:
    """获取具体的主题样式对象"""
    eff = get_effective_theme_id(theme_id)
    return THEMES.get(eff, THEMES["light"])


def get_card_bg_with_opacity(card_bg_str: str, opacity: float) -> str:
    """动态替换 rgba 颜色字符串中的 alpha 透明度通道 (精准可靠，支持 0.10 ~ 1.00)"""
    if "rgba(" in card_bg_str:
        inner = card_bg_str[card_bg_str.find("(") + 1 : card_bg_str.rfind(")")]
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) >= 3:
            return f"rgba({parts[0]}, {parts[1]}, {parts[2]}, {opacity:.2f})"
    return card_bg_str


def build_qss(theme: ThemeDefinition, opacity: Optional[float] = None) -> str:
    """构建极致极简主义的现代 QSS"""
    card_bg = get_card_bg_with_opacity(theme.card_bg, opacity) if opacity is not None else theme.card_bg
    return f"""
QMainWindow {{
    background: transparent;
}}

QWidget {{
    color: {theme.text_primary};
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 13px;
    outline: none;
}}

#CentralCard {{
    background-color: {card_bg};
    border: {theme.card_border};
    border-radius: 12px;
}}

#SearchRow {{
    background: transparent;
}}

#SearchIconLabel {{
    background: transparent;
    padding-left: 2px;
    padding-right: 2px;
}}

#SearchInput {{
    background: transparent;
    border: none;
    font-size: 14px;
    color: {theme.text_primary};
    selection-background-color: {theme.accent_color};
    selection-color: #FFFFFF;
    padding: 4px 6px;
}}

#SearchInput:focus {{
    outline: none;
}}

#ModeActionBtn, #SettingsBtn {{
    background-color: {theme.btn_bg};
    border: 1px solid {theme.btn_border};
    border-radius: 7px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
}}

#ModeActionBtn:hover, #SettingsBtn:hover {{
    background-color: {theme.btn_hover_bg};
}}

QHeaderView {{
    background-color: transparent;
    border: none;
}}

QHeaderView::section {{
    background-color: transparent;
    color: {theme.text_secondary};
    border: none;
    font-size: 11px;
    font-weight: 500;
    padding: 2px 4px;
}}

QTableView {{
    background-color: transparent;
    border: none;
    gridline-color: transparent;
    selection-background-color: transparent;
    selection-color: {theme.text_primary};
    outline: none;
}}

QTableView::item {{
    border: none;
    padding: 0px;
}}

QTableView::item:selected {{
    background: transparent;
    border: none;
    outline: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 4px;
    margin: 4px 2px 4px 0px;
}}

QScrollBar::handle:vertical {{
    background: rgba(140, 140, 160, 0.35);
    min-height: 24px;
    border-radius: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(140, 140, 160, 0.65);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

#StatusBar {{
    background: transparent;
    border-top: 1px solid {theme.btn_border};
    padding: 2px 4px;
}}
"""

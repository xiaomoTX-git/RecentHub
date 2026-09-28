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
    # 1. 浅色 (纯白高对比：白底黑字)
    "light": ThemeDefinition(
        id="light",
        name="浅色",
        description="纯白高对比，白底黑字清晰锐利",
        is_dark=False,
        # 完全不透明：卡片一旦带透明度，深色壁纸透上来会把"纯白"染成灰调，
        # 与"白底黑字"的高对比目标直接冲突。需要通透感由设置里的透明度滑块自行下调
        card_bg="rgba(255, 255, 255, 1.00)",
        card_border="1px solid rgba(0, 0, 0, 0.08)",
        accent_color="#0067C0",
        accent_hover="#1875D1",
        text_primary="#0A0A0F",
        text_secondary="#2E2E38",
        text_placeholder="#6B6B79",
        row_selected_bg="rgba(0, 103, 192, 0.12)",
        row_selected_border="rgba(0, 103, 192, 0.55)",
        row_hover_bg="rgba(0, 0, 0, 0.05)",
        row_hover_border="rgba(0, 0, 0, 0.10)",
        kbd_bg="rgba(0, 0, 0, 0.06)",
        kbd_border="rgba(0, 0, 0, 0.12)",
        kbd_text="#15151C",
        btn_bg="rgba(0, 0, 0, 0.05)",
        btn_border="rgba(0, 0, 0, 0.10)",
        btn_hover_bg="rgba(0, 0, 0, 0.10)"
    ),

    # 2. 深色 (纯黑高对比：黑底白字)
    "dark": ThemeDefinition(
        id="dark",
        name="深色",
        description="纯黑高对比，黑底白字沉浸专注",
        is_dark=True,
        # 纯黑完全不透明：半透明会让身后窗口的内容透上来，整体发灰发脏
        card_bg="rgba(10, 10, 14, 1.00)",
        card_border="1px solid rgba(255, 255, 255, 0.12)",
        accent_color="#8B5CF6",
        accent_hover="#A78BFA",
        text_primary="#FFFFFF",
        text_secondary="#D7DBE3",
        text_placeholder="#9AA0AC",
        row_selected_bg="rgba(255, 255, 255, 0.16)",
        row_selected_border="rgba(139, 92, 246, 0.65)",
        row_hover_bg="rgba(255, 255, 255, 0.06)",
        row_hover_border="rgba(255, 255, 255, 0.12)",
        kbd_bg="rgba(255, 255, 255, 0.14)",
        kbd_border="rgba(255, 255, 255, 0.22)",
        kbd_text="#FFFFFF",
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
    # 滚动条用"黑/白半透明"而不是中性灰：中性灰是最容易被察觉的脏色来源，
    # 黑白半透明与底色同源，视觉上仍然是一套纯黑纯白体系
    if theme.is_dark:
        sb_handle, sb_handle_hover = "rgba(255, 255, 255, 0.22)", "rgba(255, 255, 255, 0.40)"
    else:
        sb_handle, sb_handle_hover = "rgba(0, 0, 0, 0.20)", "rgba(0, 0, 0, 0.38)"
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

#FilterRow {{
    background: transparent;
}}

#FilterPill {{
    background-color: {theme.btn_bg};
    border: 1px solid {theme.btn_border};
    border-radius: 9px;
    color: {theme.text_secondary};
    font-size: 11px;
    font-weight: 500;
    padding: 3px 10px;
}}

#FilterPill:hover {{
    background-color: {theme.btn_hover_bg};
    color: {theme.text_primary};
}}

#FilterPill:checked {{
    background-color: {theme.accent_color};
    border-color: {theme.accent_color};
    color: #FFFFFF;
    font-weight: 600;
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
    background: {sb_handle};
    min-height: 24px;
    border-radius: 2px;
}}

QScrollBar::handle:vertical:hover {{
    background: {sb_handle_hover};
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

#LoadingRow {{
    background: transparent;
}}

#LoadingLabel {{
    background: transparent;
    color: {theme.accent_color};
    font-size: 12px;
    font-weight: 600;
}}
"""

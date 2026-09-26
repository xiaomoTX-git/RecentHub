"""
RecentHub Windows 11 原生毛玻璃 (Acrylic Glass) - 50% 超通透玻璃质感
- 扩展 DWM Frame 至整个客户区 (DwmExtendFrameIntoClientArea)
- 启用 Windows 11 原生 Acrylic (DWMWA_SYSTEMBACKDROP_TYPE = 3)
- 兼容 Windows 10/11 SetWindowCompositionAttribute 亚克力模糊增强
"""

import sys
import ctypes
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_SYSTEMBACKDROP_TYPE = 38

BACKDROP_ACRYLIC = 3
BACKDROP_MICA = 2
CORNER_ROUND = 2


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_uint),
        ("Data", ctypes.c_void_p),
        ("SizeOfData", ctypes.c_size_t),
    ]


def apply_acrylic(widget: QWidget, dark: bool = False) -> bool:
    """为窗口开启 Windows 11 原生亚克力毛玻璃 (支持浅色通透与暗夜深黑)"""
    if sys.platform != "win32":
        return False
    
    hwnd = int(widget.winId())
    success = False
    try:
        dwmapi = ctypes.windll.dwmapi
        
        # 1. 设置系统深色/浅色沉浸属性
        dark_val = ctypes.c_int(1 if dark else 0)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_val),
            ctypes.sizeof(dark_val)
        )
        
        # 2. 启用系统圆角 (12px-16px)
        corner_val = ctypes.c_int(CORNER_ROUND)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner_val),
            ctypes.sizeof(corner_val)
        )

        # 3. 将 DWM 模糊与玻璃框架延伸至全客户区 (无边框窗口核心)
        margins = MARGINS(-1, -1, -1, -1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
        
        # 4. 启用系统原生亚克力毛玻璃 (Windows 11 22H2+ / Build 22621+)
        backdrop_val = ctypes.c_int(BACKDROP_ACRYLIC)
        res = dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop_val),
            ctypes.sizeof(backdrop_val)
        )
        if res == 0:
            success = True

        # 5. 避免使用会破坏 Qt WA_TranslucentBackground Alpha 像素通道的私有 SetWindowCompositionAttribute
        # 确保窗口能够如同 SettingsDialog 一样实现 100% 真正通透的半透明
        pass

        return success
    except Exception:
        return False


def apply_light_acrylic(widget: QWidget) -> bool:
    return apply_acrylic(widget, dark=False)


def setup_light_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    """创建极简通透的柔和弥散阴影"""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(32)
    shadow.setXOffset(0)
    shadow.setYOffset(10)
    shadow.setColor(QColor(0, 0, 0, 30))
    return shadow

"""
RecentHub 全屏免打扰服务 (Fullscreen & Gaming Mode Guard)
- 检测 Windows 10/11 当前是否处于全屏状态 (Direct3D 游戏、全屏独占、全屏看电影、PPT 演示等)
- 当处于全屏状态时，自动静默阻断全局快捷键唤出，避免打断游戏、画面撕裂或退出全屏
- 采用微软官方 SHQueryUserNotificationState + 前台窗口多屏几何覆盖双重算法，耗时 < 0.01ms
"""

import sys
import ctypes
from ctypes import wintypes
from typing import Tuple

user32 = ctypes.windll.user32 if sys.platform == "win32" else None
shell32 = ctypes.windll.shell32 if sys.platform == "win32" else None


class FullscreenService:
    @classmethod
    def is_fullscreen_active(cls, ignore_hwnd: int = 0) -> bool:
        """检查当前是否有应用处于全屏覆盖状态 (看电影/打游戏等)"""
        if sys.platform != "win32" or not user32 or not shell32:
            return False

        # 1. 微软官方 Shell API: SHQueryUserNotificationState
        # QUNS_BUSY (2) = 全屏独占 (游戏/影视)
        # QUNS_RUNNING_D3D_FULL_SCREEN (3) = Direct3D 3D 全屏游戏
        # QUNS_PRESENTATION_MODE (4) = PPT / 幻灯片全屏放映
        # QUNS_APP (7) = Windows 全屏 App
        try:
            pState = wintypes.DWORD()
            res = shell32.SHQueryUserNotificationState(ctypes.byref(pState))
            if res == 0 and pState.value in (2, 3, 4, 7):
                return True
        except Exception:
            pass

        # 2. 前台活动窗口几何尺寸判定 (精准覆盖无边框全屏游戏、全屏网页视频、播放器如 PotPlayer 等)
        try:
            hwnd = user32.GetForegroundWindow()
            if not hwnd or hwnd == ignore_hwnd or hwnd == user32.GetDesktopWindow() or hwnd == user32.GetShellWindow():
                return False

            # 排除桌面与任务栏外壳
            buf = ctypes.create_unicode_buffer(256)
            user32.GetClassNameW(hwnd, buf, 256)
            cname = buf.value
            if cname in ("Progman", "WorkerW", "Shell_TrayWnd", "Windows.UI.Core.CoreWindow"):
                return False

            rect = wintypes.RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False

            # 获取该前台窗口所在显示器的物理分辨率
            hMonitor = user32.MonitorFromWindow(hwnd, 2)  # MONITOR_DEFAULTTONEAREST
            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("rcMonitor", wintypes.RECT),
                    ("rcWork", wintypes.RECT),
                    ("dwFlags", wintypes.DWORD),
                ]
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if user32.GetMonitorInfoW(hMonitor, ctypes.byref(mi)):
                m_rect = mi.rcMonitor
                # 前台窗口完全覆盖该显示器四方边界 (包含甚至盖住任务栏)
                if (rect.left <= m_rect.left and
                    rect.top <= m_rect.top and
                    rect.right >= m_rect.right and
                    rect.bottom >= m_rect.bottom):
                    return True
        except Exception:
            pass

        return False

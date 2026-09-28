"""
RecentHub Windows 全局热键与双击 Ctrl 唤出服务
- 支持原生标准 Win32 RegisterHotKey (如 Alt+Space, Ctrl+Space 等)
- 支持按两下 Ctrl (Double Ctrl) 极速盲操呼出/隐藏
- 纯净安全：仅在用户启用双击 Ctrl 时局部挂载，绝不作按键记录，其它按键 0 纳秒放行
- 支持快捷键编辑期间无冲突静默暂停与恢复
"""

import logging
import sys
import time
import ctypes
from ctypes import wintypes
from typing import Callable, Optional, Tuple

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication
from app.core.config import ConfigManager

logger = logging.getLogger(__name__)

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
RECENT_HUB_HOTKEY_ID = 0x4248  # 'RH'

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
VK_CONTROL = 0x11
VK_LCONTROL = 0xA2
VK_RCONTROL = 0xA3

user32 = ctypes.windll.user32 if sys.platform == "win32" else None

VK_MAP = {
    "SPACE": 0x20, "RETURN": 0x0D, "ENTER": 0x0D, "ESCAPE": 0x1B, "ESC": 0x1B,
    "TAB": 0x09, "BACKSPACE": 0x08, "DELETE": 0x2E, "INSERT": 0x2D,
    "HOME": 0x24, "END": 0x23, "PAGEUP": 0x21, "PAGEDOWN": 0x22,
    "UP": 0x26, "DOWN": 0x28, "LEFT": 0x25, "RIGHT": 0x27,
    "F1": 0x70, "F2": 0x71, "F3": 0x72, "F4": 0x73,
    "F5": 0x74, "F6": 0x75, "F7": 0x76, "F8": 0x77,
    "F9": 0x78, "F10": 0x79, "F11": 0x7A, "F12": 0x7B,
}


def parse_hotkey_string(hotkey_str: str) -> Tuple[int, int]:
    """将快捷键文本 (如 'Alt+Space', 'Ctrl+Shift+R') 解析为 Win32 修饰符与虚拟键码"""
    parts = [p.strip().upper() for p in hotkey_str.split("+") if p.strip()]
    mods = MOD_NOREPEAT
    vk = 0
    for p in parts:
        if p in ("ALT", "MENU", "OPTION"):
            mods |= MOD_ALT
        elif p in ("CTRL", "CONTROL", "COMMAND"):
            mods |= MOD_CONTROL
        elif p == "SHIFT":
            mods |= MOD_SHIFT
        elif p in ("WIN", "WINDOWS", "SUPER"):
            mods |= MOD_WIN
        elif p in VK_MAP:
            vk = VK_MAP[p]
        elif len(p) == 1:
            vk = ord(p)
    return mods, vk


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM) if sys.platform == "win32" else None
# LRESULT 在 64 位下为 64 位有符号整数：若按 c_long 声明会被截断，导致钩子返回值异常而吞掉/错乱按键消息
LRESULT = ctypes.c_ssize_t
HHOOK = ctypes.c_void_p


def _setup_hook_prototypes():
    """显式声明 Win32 钩子相关 API 原型，避免 ctypes 默认 32 位返回值截断句柄"""
    if sys.platform != "win32" or not user32:
        return
    try:
        user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, ctypes.c_void_p, wintypes.DWORD]
        user32.SetWindowsHookExW.restype = HHOOK
        user32.CallNextHookEx.argtypes = [HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
        user32.CallNextHookEx.restype = LRESULT
        user32.UnhookWindowsHookEx.argtypes = [HHOOK]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        user32.RegisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int, wintypes.UINT, wintypes.UINT]
        user32.RegisterHotKey.restype = wintypes.BOOL
        user32.UnregisterHotKey.argtypes = [ctypes.c_void_p, ctypes.c_int]
        user32.UnregisterHotKey.restype = wintypes.BOOL
    except Exception:
        logger.debug("Win32 钩子 API 原型声明失败", exc_info=True)


_setup_hook_prototypes()


class DoubleCtrlDetector:
    """专用的极速双击 Ctrl 探测器 (仅当用户开启按两下 Ctrl 时生效，防连击误触)"""
    def __init__(self, callback: Callable[[], None], interval: float = 0.42):
        self.callback = callback
        self.interval = interval
        self._hook = None
        self._proc = None
        self._last_ctrl_up_time = 0.0
        self._other_key_pressed = False
        self._ctrl_is_down = False

    def is_running(self) -> bool:
        return self._hook is not None

    def start(self) -> bool:
        if sys.platform != "win32" or not user32:
            return False
        if self._hook:
            return True

        _setup_hook_prototypes()

        def hook_callback(nCode, wParam, lParam):
            if nCode >= 0:
                try:
                    kb = KBDLLHOOKSTRUCT.from_address(lParam)
                    vk = kb.vkCode
                    is_ctrl = (vk in (VK_CONTROL, VK_LCONTROL, VK_RCONTROL))

                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        if is_ctrl:
                            self._ctrl_is_down = True
                        else:
                            # 期间若按下了其它键 (如 Ctrl+C、Ctrl+Tab 等)，立即取消双击判定
                            self._other_key_pressed = True
                    elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                        if is_ctrl:
                            now = time.time()
                            if not self._other_key_pressed:
                                diff = now - self._last_ctrl_up_time
                                # 50ms ~ 420ms 之间判定为连击两下 Ctrl
                                if 0.05 <= diff <= self.interval:
                                    self._last_ctrl_up_time = 0.0
                                    self._defer_callback()
                                else:
                                    self._last_ctrl_up_time = now
                            else:
                                self._last_ctrl_up_time = 0.0
                            self._other_key_pressed = False
                            self._ctrl_is_down = False
                        else:
                            if not self._ctrl_is_down:
                                self._other_key_pressed = False
                except Exception:
                    # 低级键盘钩子回调必须绝对安静且极快返回，异常仅记日志绝不外抛
                    logger.debug("双击 Ctrl 钩子回调异常", exc_info=True)

            return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

        self._proc = HOOKPROC(hook_callback)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._proc, None, 0)
        return bool(self._hook)

    def _defer_callback(self):
        """关键：绝不在低级键盘钩子内直接执行窗口显隐等重 UI 操作。
        钩子回调必须尽快返回 (Windows 超时会静默卸载钩子并错乱输入队列)，
        因此改为投递到 Qt 事件循环下一拍执行。
        """
        try:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self.callback)
        except Exception:
            logger.debug("QTimer 投递失败，改为直接同步回调", exc_info=True)
            try:
                self.callback()
            except Exception:
                logger.warning("热键触发回调执行失败", exc_info=True)

    def stop(self):
        if self._hook and user32:
            try:
                user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None
        # 注意：_proc 必须持有到对象销毁为止。若卸载失败(或句柄曾被截断)而回调被 GC，
        # 系统仍持有已释放的函数指针，将直接导致 0xC0000005 崩溃。


class HotkeyNativeEventFilter(QAbstractNativeEventFilter):
    def __init__(self, target_id: int, on_hotkey: Callable[[], None]):
        super().__init__()
        self.target_id = target_id
        self.on_hotkey = on_hotkey

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == self.target_id:
                try:
                    self.on_hotkey()
                    return True, 0
                except Exception:
                    logger.warning("WM_HOTKEY 唤出回调执行失败", exc_info=True)
        return False, 0


class HotkeyService:
    _instance: Optional['HotkeyService'] = None

    def __init__(self, on_hotkey_triggered: Optional[Callable[[], None]] = None):
        self.on_hotkey_triggered = on_hotkey_triggered
        self.is_registered = False
        self.current_hotkey_str = "Alt+Space"
        self._filter: Optional[HotkeyNativeEventFilter] = None
        self._double_ctrl: Optional[DoubleCtrlDetector] = None

        if self.on_hotkey_triggered:
            self._double_ctrl = DoubleCtrlDetector(self.on_hotkey_triggered)

        cfg = ConfigManager.load()
        saved = cfg.get("global_hotkey", "Alt+Space")
        if saved:
            self.current_hotkey_str = saved

        self._setup_event_filter()
        self.register(self.current_hotkey_str)
        HotkeyService._instance = self

    @classmethod
    def get_instance(cls) -> Optional['HotkeyService']:
        return cls._instance

    def _setup_event_filter(self):
        if sys.platform == "win32" and not self._filter and self.on_hotkey_triggered:
            self._filter = HotkeyNativeEventFilter(
                target_id=RECENT_HUB_HOTKEY_ID,
                on_hotkey=self.on_hotkey_triggered
            )
            app = QCoreApplication.instance()
            if app:
                app.installNativeEventFilter(self._filter)

    def register(self, hotkey_str: str) -> bool:
        if sys.platform != "win32":
            return False

        self.unregister()

        hk_norm = hotkey_str.strip()
        # 1. 检查是否为 "按两下 Ctrl" / "Double Ctrl" 模式
        if hk_norm.lower() in ("double ctrl", "doublectrl", "双击 ctrl", "2xctrl"):
            if self._double_ctrl:
                ok = self._double_ctrl.start()
                if ok:
                    self.is_registered = True
                    self.current_hotkey_str = "双击 Ctrl"
                    return True
            self.is_registered = False
            return False

        # 2. 常规 Win32 RegisterHotKey
        mods, vk = parse_hotkey_string(hk_norm)
        if not vk:
            return False

        try:
            if user32:
                res = user32.RegisterHotKey(None, RECENT_HUB_HOTKEY_ID, mods, vk)
                if res != 0:
                    self.is_registered = True
                    self.current_hotkey_str = hk_norm
                    return True
            self.is_registered = False
            return False
        except Exception:
            logger.warning("RegisterHotKey 注册失败: %s", hk_norm, exc_info=True)
            self.is_registered = False
            return False

    def unregister(self):
        if sys.platform != "win32":
            return
        if self._double_ctrl and self._double_ctrl.is_running():
            self._double_ctrl.stop()
        if user32:
            # 原实现传入 None 作为句柄，等于什么都没注销；此处直接按 ID 注销
            try:
                user32.UnregisterHotKey(None, RECENT_HUB_HOTKEY_ID)
            except Exception:
                logger.debug("UnregisterHotKey 失败 (可能本就未注册)", exc_info=True)
        self.is_registered = False

    def pause(self):
        """编辑快捷键时临时暂停全局热键或双击 Ctrl 监听"""
        self._was_registered_before_pause = self.is_registered
        self.unregister()

    def resume(self):
        """编辑快捷键结束时恢复全局热键或双击 Ctrl 监听"""
        if getattr(self, '_was_registered_before_pause', False):
            self.register(self.current_hotkey_str)

    def update_hotkey(self, new_hotkey_str: str) -> bool:
        ok = self.register(new_hotkey_str)
        if ok:
            cfg = ConfigManager.load()
            cfg["global_hotkey"] = self.current_hotkey_str
            ConfigManager.save(cfg)
        return ok

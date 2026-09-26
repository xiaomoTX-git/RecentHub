r"""
RecentHub Windows 开机自启动管理服务
通过 Windows 注册表 HKCU\Software\Microsoft\Windows\CurrentVersion\Run 管理自启

登记的命令恒带 --silent：开机时静默驻留系统托盘，不弹出主窗口、不抢占桌面焦点
"""

import sys
import os
import winreg
from app.core.paths import is_frozen

APP_NAME = "RecentHub"
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
SILENT_FLAG = "--silent"


class AutoStartService:
    @classmethod
    def get_executable_command(cls) -> str:
        """获取用于开机自启动的静默命令 (恒带 --silent: 开机仅驻留托盘，不弹出主窗口)"""
        # 打包运行：sys.executable 就是 RecentHub.exe，不能再拼 main.py (打包产物里没有它)
        if is_frozen():
            return f'"{sys.executable}" {SILENT_FLAG}'

        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        # 优先直接用 pythonw.exe 拉起 main.py：pythonw 无控制台窗口，开机时完全不闪黑框。
        # (不能优先用 run.bat：它会先弹一个 cmd 窗口，且 taskkill /F /IM pythonw.exe
        #  会误杀机器上其它 pythonw 进程)
        pythonw = os.path.join(base_dir, ".venv", "Scripts", "pythonw.exe")
        main_py = os.path.join(base_dir, "main.py")
        if os.path.exists(pythonw) and os.path.exists(main_py):
            return f'"{pythonw}" "{main_py}" {SILENT_FLAG}'

        run_bat = os.path.join(base_dir, "run.bat")
        if os.path.exists(run_bat):
            return f'"{run_bat}" {SILENT_FLAG}'

        return f'"{sys.executable}" "{main_py}" {SILENT_FLAG}'

    @classmethod
    def get_registered_command(cls) -> str:
        """读取当前注册表中已登记的自启命令 (未开启返回空串)"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, APP_NAME)
                return str(val)
        except Exception:
            return ""

    @classmethod
    def refresh(cls) -> None:
        """幂等修复"已失效"的自启登记。

        只处理两种确实需要修的情况：
          1. 旧格式：命令不含 --silent (老版本常指向 run.bat，开机时会直接弹出主窗口)
          2. 死链：登记的 exe 已被移动或删除，自启指向不存在的程序

        刻意**不做**"路径不同就改写"：否则用户随手运行一份绿色版/开发版
        (如 dist\\RecentHub)，它就会把安装版登记的自启悄悄改成指向自己 —— 这属于
        程序不该有的越权改写。自启指向哪个副本，应由用户在该副本的设置里显式决定。
        """
        registered = cls.get_registered_command()
        if not registered:
            return
        stripped = registered.strip()
        exe_path = cls._registered_exe_path(stripped)
        is_stale = (SILENT_FLAG not in stripped) or (bool(exe_path) and not os.path.exists(exe_path))
        if is_stale and registered != cls.get_executable_command():
            cls.set_enabled(True)

    @staticmethod
    def _registered_exe_path(command: str) -> str:
        """从登记命令里取出可执行文件路径，形如 "C:\\...\\RecentHub.exe" --silent"""
        cmd = command.strip()
        if cmd.startswith('"'):
            end = cmd.find('"', 1)
            if end > 1:
                return cmd[1:end]
        return cmd.split(" ")[0]

    @classmethod
    def is_enabled(cls) -> bool:
        """检查是否已设置开机自启"""
        return bool(cls.get_registered_command())

    @classmethod
    def set_enabled(cls, enable: bool) -> bool:
        """开启或关闭开机自启"""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
                if enable:
                    cmd = cls.get_executable_command()
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
            return True
        except Exception:
            return False

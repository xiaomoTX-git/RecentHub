"""
RecentHub 应用程序主入口
单实例互斥唤起、原生系统托盘常驻与极速启动
"""

import sys
import os

# 确保 app 根路径与虚拟环境 site-packages / win32 在 sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 打包运行 (PyInstaller) 时依赖已随 exe 一起冻结，sys.path / DLL 目录都由引导器
# 处理好，这里强行插 .venv 反而会指向不存在的路径
if not getattr(sys, "frozen", False):
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    venv_site = os.path.join(BASE_DIR, ".venv", "Lib", "site-packages")
    if os.path.exists(venv_site):
        for sub in [venv_site, os.path.join(venv_site, "win32"), os.path.join(venv_site, "win32", "lib")]:
            if sub not in sys.path and os.path.exists(sub):
                sys.path.insert(0, sub)
        pyside6_dir = os.path.join(venv_site, "PySide6")
        if os.path.exists(pyside6_dir) and hasattr(os, 'add_dll_directory'):
            try:
                os.add_dll_directory(pyside6_dir)
            except Exception:
                pass

from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtCore import Qt

from app.core.paths import resource_dir
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.services.hotkey_service import HotkeyService
from app.services.autostart_service import AutoStartService
from app.core.config import ConfigManager
from app.ui.main_window import MainWindow
from app.ui.tray import TrayService

SERVER_NAME = "RecentHub_SingleInstance_IPC"


def main():
    # 开机自启时注册表命令会带上 --silent：仅静默驻留托盘 (全局热键/托盘随时唤出)，
    # 不主动弹出主窗口、不抢占桌面焦点
    silent_start = "--silent" in sys.argv[1:]
    # 启用高分屏缩放自适应
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    from PySide6.QtGui import QIcon
    # 多尺寸 .ico：任务栏/Alt-Tab 按实际像素密度取对应帧，避免单张 png 缩放发虚
    icon_path = os.path.join(resource_dir(), "app_icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # 1. 单实例互斥检测 (内核级 Mutex + 本地命名管道 IPC 双重加锁，彻底杜绝双开打架)
    _kernel_mutex = None
    if sys.platform == "win32":
        import ctypes
        ERROR_ALREADY_EXISTS = 183
        _kernel_mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "RecentHub_SingleInstance_Mutex_Lock")
        if ctypes.windll.kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            socket = QLocalSocket()
            socket.connectToServer(SERVER_NAME)
            if socket.waitForConnected(600):
                socket.write(b"WAKEUP")
                socket.waitForBytesWritten(500)
                socket.disconnectFromServer()
            sys.exit(0)

    socket = QLocalSocket()
    socket.connectToServer(SERVER_NAME)
    if socket.waitForConnected(500):
        socket.write(b"WAKEUP")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        sys.exit(0)

    # 建立单实例 IPC 服务端
    server = QLocalServer()
    server.removeServer(SERVER_NAME)
    server.listen(SERVER_NAME)

    # 2. 初始化核心组件
    db = StorageDB()
    scan_service = ScanService(db)

    # 3. 构造界面与全局热键服务 (基于标准 Win32 RegisterHotKey)
    window = MainWindow(db, scan_service)
    tray = TrayService(window, db, scan_service)
    window.tray_service = tray
    hotkey_service = HotkeyService(on_hotkey_triggered=lambda: tray.toggle_window(from_hotkey=True))

    # 4. IPC 唤醒监听
    def on_new_connection():
        client = server.nextPendingConnection()
        if client:
            client.waitForReadyRead(300)
            msg = bytes(client.readAll())
            if msg == b"WAKEUP":
                # 用户又双击了一次图标/快捷方式：按桌面软件惯例「唤出并置前」，
                # 用 show_window 而非 toggle_window —— 否则窗口已开着时再启动一次
                # 反而会把它藏起来，看起来像"点了没反应"
                tray.show_window()
            client.disconnectFromServer()

    server.newConnection.connect(on_new_connection)

    # 5. 统一退出清理：托盘"退出"会直接 quit()，不会触发窗口 closeEvent，
    #    必须在此停止常驻搜索线程并卸载全局钩子，否则 QThread 带线程析构会直接崩溃退出
    def shutdown():
        try:
            window.stop_background_tasks()
        except Exception:
            pass
        try:
            hotkey_service.unregister()
        except Exception:
            pass
        try:
            db.close_all()
        except Exception:
            pass

    app.aboutToQuit.connect(shutdown)

    # 6. 幂等升级已登记的开机自启命令：旧版本未带 --silent (常指向 run.bat)，
    #    不刷新的话已开启自启的用户开机时仍会被弹出主窗口
    try:
        if ConfigManager.load().get("auto_start"):
            AutoStartService.refresh()
    except Exception:
        pass

    # 默认启动即唤出主窗口；开机自启 (--silent) 则不唤出，仅静默驻留托盘
    if not silent_start:
        window.show_and_activate()

    code = app.exec()
    shutdown()
    sys.exit(code)


if __name__ == "__main__":
    main()

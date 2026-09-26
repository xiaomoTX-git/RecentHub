# -*- mode: python ; coding: utf-8 -*-
r"""
RecentHub PyInstaller 打包配置 (onedir / 无控制台窗口)

构建：
    .venv\Scripts\pyinstaller.exe --noconfirm --clean RecentHub.spec

产物：
    dist\RecentHub\RecentHub.exe        <- 主程序 (窗口模式，无 cmd 黑框)
    dist\RecentHub\_internal\resources\ <- 图标等只读资源 (映射自 app\resources)

说明：
- 采用 onedir 而非 onefile：PySide6 体积大，onefile 每次启动都要把上百 MB
  解压到临时目录，冷启动要数秒；onedir 启动几乎无额外开销。
- 运行时资源通过 app/core/paths.py 的 resource_dir() 定位到
  sys._MEIPASS\resources，因此 datas 的目标目录名必须是 "resources"。
"""

import os

# spec 执行时 cwd 即项目根 (PyInstaller 以 spec 所在目录为基准)
PROJECT_ROOT = os.path.abspath(os.getcwd())
RESOURCES_SRC = os.path.join(PROJECT_ROOT, "app", "resources")
ICON_PATH = os.path.join(RESOURCES_SRC, "app_icon.ico")
# 版本资源：让资源管理器属性页显示产品名/版本/版权 (版本号与 installer\RecentHub.iss 保持一致)
VERSION_FILE = os.path.join(PROJECT_ROOT, "installer", "version_info.txt")


a = Analysis(
    ["main.py"],
    pathex=[PROJECT_ROOT],
    binaries=[],
    # 只读资源随 exe 一起分发；目标目录名 "resources" 必须与 paths.resource_dir() 一致
    datas=[(RESOURCES_SRC, "resources")],
    # pywin32 为晚期绑定 COM 调用 (Dispatch("ADODB.Connection") / WScript.Shell)，
    # 静态分析看不到，必须显式声明，否则打包后全盘检索与 .lnk 解析会静默失效
    hiddenimports=[
        "pythoncom",
        "pywintypes",
        "win32api",
        "win32timezone",
        "win32com",
        "win32com.client",
        "win32com.shell",
        "win32com.shell.shell",
        "win32com.shell.shellcon",
        "pypinyin",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 排除与本项目无关的大体积/冲突库，避免体积膨胀 (尤其 PySide6 之外的 GUI 栈)
    excludes=[
        "tkinter",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "matplotlib",
        "numpy",
        "scipy",
        "PIL",
        "pytest",
        "_pytest",
    ],
    noarchive=False,
)


pyz = PYZ(a.pure)


exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="RecentHub",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    # 窗口模式：开机自启时不闪 cmd 黑框
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_PATH,
    version=VERSION_FILE,
)


coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="RecentHub",
)
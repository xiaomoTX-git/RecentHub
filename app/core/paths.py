r"""
RecentHub 运行时路径解析 (源码运行 / PyInstaller 打包运行 双模式)

- 资源目录 (只读)：源码模式在 <项目根>\app\resources；打包模式在 PyInstaller
  的解包目录 sys._MEIPASS\resources
- 用户数据目录 (可写)：源码模式沿用 <项目根>\data；打包模式改用
  %APPDATA%\RecentHub —— 安装到 Program Files 后程序目录不可写，
  配置若继续写在那里会被静默丢弃
"""

import os
import sys


def is_frozen() -> bool:
    """是否运行在 PyInstaller 等打包产物中"""
    return bool(getattr(sys, "frozen", False))


def resource_dir() -> str:
    """只读资源目录 (图标等)"""
    if is_frozen():
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "resources")
    # app/core/paths.py -> app/ -> app/resources
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")


def user_data_dir() -> str:
    """可写的用户数据目录 (config.json 等)，确保已存在"""
    if is_frozen():
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RecentHub")
    else:
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")
    try:
        os.makedirs(base, exist_ok=True)
    except Exception:
        pass
    return base
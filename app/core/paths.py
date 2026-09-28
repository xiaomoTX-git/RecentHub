r"""
RecentHub 运行时路径解析 (源码运行 / PyInstaller 打包运行 / 便携绿色版 三模式)

- 资源目录 (只读)：源码模式在 <项目根>\app\resources；打包模式在 PyInstaller
  的解包目录 sys._MEIPASS\resources
- 用户数据目录 (可写，存 config.json / logs)：
    * 源码模式沿用 <项目根>\data
    * 安装版 (打包且非便携) 用 %APPDATA%\RecentHub —— 安装到 Program Files 后
      程序目录不可写，配置若继续写在那里会被静默丢弃
    * 便携版 (exe 同级存在 portable.flag，或设置 RECENTHUB_PORTABLE=1) 就地写入
      exe\data：整个目录拷到 U 盘即可随插随用，删除目录即为卸载
- 数据库目录：便携版随数据目录走；其余情况沿用历史 %LOCALAPPDATA%\RecentHub，
  保证已装用户的历史数据零迁移
"""

import os
import sys


def is_frozen() -> bool:
    """是否运行在 PyInstaller 等打包产物中"""
    return bool(getattr(sys, "frozen", False))


def is_portable() -> bool:
    """是否便携绿色版：环境变量显式开启，或打包产物同级存在 portable.flag 标记文件"""
    if os.environ.get("RECENTHUB_PORTABLE") == "1":
        return True
    if is_frozen():
        flag = os.path.join(os.path.dirname(sys.executable), "portable.flag")
        return os.path.exists(flag)
    return False


def _portable_data_dir() -> str:
    """便携版数据目录：exe 同级的 data 子目录"""
    return os.path.join(os.path.dirname(sys.executable), "data")


def _source_data_dir() -> str:
    r"""源码模式数据目录：<项目根>\data"""
    # app/core/paths.py -> app/ -> app/../.. == 项目根
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")


def _ensure(path: str) -> str:
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass
    return path


def resource_dir() -> str:
    """只读资源目录 (图标等)"""
    if is_frozen():
        return os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(sys.executable)), "resources")
    # app/core/paths.py -> app/ -> app/resources
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")


def user_data_dir() -> str:
    """可写的用户数据目录 (config.json / logs 等)，确保已存在"""
    if is_portable():
        base = _portable_data_dir()
    elif is_frozen():
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "RecentHub")
    else:
        base = _source_data_dir()
    return _ensure(base)


def db_dir() -> str:
    """数据库所在目录。便携版随数据目录走；其余情况沿用历史 %LOCALAPPDATA%\\RecentHub，
    避免已安装用户与源码开发者的既有数据需要迁移"""
    if is_portable():
        return _ensure(_portable_data_dir())
    return _ensure(os.path.expandvars(r"%LOCALAPPDATA%\RecentHub"))


def log_dir() -> str:
    """日志目录 (基于用户数据目录，便携版自然落到 exe\\data\\logs)"""
    return _ensure(os.path.join(user_data_dir(), "logs"))
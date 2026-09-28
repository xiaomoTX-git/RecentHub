r"""
RecentHub 统一日志与诊断体系

- 文件轮转：1MB × 3 份备份写入 <数据目录>\logs\recenthub.log，防止长期运行无限膨胀
- 全局异常钩子：主线程与后台线程未捕获异常连堆栈落盘 (先记录、再交还原钩子，不改变原有行为)
- Qt 消息转发：GUI 进程通常没有控制台，Qt 的 warning/critical 若不转发会完全丢失

设计原则：日志初始化本身绝不允许拖垮启动，任何失败都退化为静默。
"""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

from app.core.config import ConfigManager
from app.core.paths import log_dir

_logger = logging.getLogger(__name__)
_initialized = False


def setup_logging():
    """安装轮转文件日志与全局异常钩子 (幂等，可在任何位置重复调用)"""
    global _initialized
    if _initialized:
        return
    _initialized = True

    level_name = str(ConfigManager.load().get("log_level", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    try:
        handler = RotatingFileHandler(
            os.path.join(log_dir(), "recenthub.log"),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)
    except Exception:
        # 日志盘不可写 (只读介质 / 权限受限) 时静默降级：绝不能因写日志失败而无法启动
        pass

    # 主线程未捕获异常：连堆栈落盘后再交还系统原钩子，保留原有的崩溃提示行为
    prev_sys_hook = sys.excepthook

    def _sys_hook(exc_type, exc_value, exc_tb):
        logging.getLogger("RecentHub").critical(
            "未捕获异常", exc_info=(exc_type, exc_value, exc_tb)
        )
        prev_sys_hook(exc_type, exc_value, exc_tb)

    sys.excepthook = _sys_hook

    # 后台线程未捕获异常：Python 默认只打印到 stderr，GUI 进程里等于彻底丢失
    def _thread_hook(args):
        thread_name = args.thread.name if args.thread else "unknown"
        logging.getLogger("RecentHub").critical(
            "后台线程未捕获异常 (线程: %s)", thread_name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = _thread_hook

    _install_qt_message_handler()

    # 落一条启动标记：让用户打开日志目录时能立刻确认「日志确实在工作、级别与路径为何」
    _logger.info("RecentHub 日志系统就绪 (级别=%s, 目录=%s)", level_name, log_dir())


def _install_qt_message_handler():
    """把 Qt 的 warning / critical / fatal 消息统一转发进日志文件"""
    try:
        from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    except Exception:
        return

    level_map = {
        QtMsgType.QtDebugMsg: logging.DEBUG,
        QtMsgType.QtInfoMsg: logging.INFO,
        QtMsgType.QtWarningMsg: logging.WARNING,
        QtMsgType.QtCriticalMsg: logging.ERROR,
        QtMsgType.QtFatalMsg: logging.CRITICAL,
    }
    qt_logger = logging.getLogger("Qt")

    def _qt_handler(mode, context, message):
        try:
            qt_logger.log(level_map.get(mode, logging.INFO), str(message).strip())
        except Exception:
            pass

    try:
        qInstallMessageHandler(_qt_handler)
    except Exception:
        pass


def get_logger(name: str) -> logging.Logger:
    """便捷获取带命名空间的 logger"""
    return logging.getLogger(name)
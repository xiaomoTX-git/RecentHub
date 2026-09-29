"""
RecentHub 更新检查服务
- 查询 GitHub Releases 最新版本并与本地 APP_VERSION 对比
- 仅气泡提示 + 跳转下载页：不做静默下载替换 (安装版/便携版路径各异，
  自动替换 exe 风险远大于收益，保持极简克制)
- 走 urllib 标准库 (零新依赖)，自动继承系统代理设置；失败仅记日志
"""

import json
import logging
import re
import urllib.request
from typing import Optional

from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

GITHUB_API_LATEST = "https://api.github.com/repos/xiaomoTX-git/RecentHub/releases/latest"
RELEASES_PAGE = "https://github.com/xiaomoTX-git/RecentHub/releases/latest"

_REQ_HEADERS = {
    # GitHub API 强制要求 User-Agent，缺省会被 403
    "User-Agent": "RecentHub-UpdateCheck",
    "Accept": "application/vnd.github+json",
}


def parse_version(s) -> tuple:
    """'v1.2.3' / '1.2' -> (1, 2, 3)。提取首个点分段数字串，解析失败返回 ()"""
    m = re.search(r"v?(\d+(?:\.\d+)*)", str(s or ""))
    if not m:
        return ()
    return tuple(int(p) for p in m.group(1).split("."))


def is_newer(latest: str, current: str) -> bool:
    """按语义化版本比较 (缺省段补 0)，latest > current 才算新版本"""
    a, b = parse_version(latest), parse_version(current)
    if not a or not b:
        return False
    n = max(len(a), len(b))
    a += (0,) * (n - len(a))
    b += (0,) * (n - len(b))
    return a > b


def check_latest_release(timeout: float = 5.0) -> Optional[dict]:
    """同步查询最新 Release。成功返回 {'tag','url','name'}，失败返回 None (仅记日志)"""
    try:
        req = urllib.request.Request(GITHUB_API_LATEST, headers=_REQ_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {
            "tag": str(data.get("tag_name") or "").strip(),
            "url": str(data.get("html_url") or RELEASES_PAGE).strip(),
            "name": str(data.get("name") or "").strip(),
        }
    except Exception:
        # 网络不可达 / 无代理环境 / GitHub 限流 (匿名 60 次/IP·小时) 均静默降级
        logger.warning("检查更新失败 (网络不可达或被限流)", exc_info=True)
        return None


class UpdateCheckWorker(QThread):
    """后台更新检查线程：结果经信号回主线程，绝不阻塞 UI

    生命周期约定：调用方必须持有强引用并在退出时 wait()，
    绝不允许 QThread 对象在线程运行中被析构 (会 qFatal 硬崩整个进程)。
    """
    checked = Signal(dict)  # 成功 {'tag','url','name','is_newer'}；失败 {'failed': True}

    def __init__(self, timeout: float = 5.0, parent=None):
        super().__init__(parent)
        self._timeout = timeout

    def run(self):
        info = check_latest_release(self._timeout)
        if info is None:
            self.checked.emit({"failed": True})
            return
        from app.core.version import APP_VERSION
        info["is_newer"] = is_newer(info["tag"], APP_VERSION)
        self.checked.emit(info)

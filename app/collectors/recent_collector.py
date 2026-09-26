r"""
RecentCollector: 采集 %APPDATA%\Microsoft\Windows\Recent 根目录下的 .lnk 文件
"""

import os
from typing import List
from app.collectors.base import BaseCollector
from app.core.models import RecentItem
from app.parsers.lnk_parser import LnkParser
from app.aggregator.normalizer import normalize_item


class RecentCollector(BaseCollector):
    def __init__(self):
        super().__init__("recent_lnk")
        self.recent_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent")

    def is_available(self) -> bool:
        return os.path.exists(self.recent_dir)

    def collect(self) -> List[RecentItem]:
        if not self.is_available():
            return []

        # 变动检测 (若无变动直接返回空列表)
        changed, latest_mtime = self.has_changed(self.recent_dir)
        if not changed:
            return []

        items: List[RecentItem] = []
        try:
            with os.scandir(self.recent_dir) as entries:
                for entry in entries:
                    if entry.is_file() and entry.name.lower().endswith('.lnk'):
                        try:
                            lnk = LnkParser.parse_file(entry.path)
                            if lnk.is_valid:
                                item = normalize_item(
                                    target_path=lnk.target_path,
                                    arguments=lnk.arguments,
                                    last_used_at=lnk.access_time or int(entry.stat().st_mtime),
                                    use_count=1,
                                    source=self.name
                                )
                                items.append(item)
                        except Exception:
                            continue
            self.last_check_mtime = latest_mtime
        except Exception:
            pass

        return items

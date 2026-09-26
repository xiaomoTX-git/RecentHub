"""
JumpListCollector: 采集 Windows Jump Lists 跳转列表
支持 AutomaticDestinations 与 CustomDestinations
"""

import os
from typing import List
from app.collectors.base import BaseCollector
from app.core.models import RecentItem
from app.parsers.cfb_parser import CfbParser
from app.parsers.lnk_parser import LnkParser
from app.aggregator.normalizer import normalize_item


class JumpListCollector(BaseCollector):
    def __init__(self):
        super().__init__("jumplist")
        self.auto_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent\AutomaticDestinations")
        self.custom_dir = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Recent\CustomDestinations")
        self._file_mtimes = {}

    def is_available(self) -> bool:
        return os.path.exists(self.auto_dir) or os.path.exists(self.custom_dir)

    def collect(self) -> List[RecentItem]:
        items: List[RecentItem] = []

        # 1. 扫描 AutomaticDestinations
        if os.path.exists(self.auto_dir):
            try:
                with os.scandir(self.auto_dir) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.lower().endswith('.automaticdestinations-ms'):
                            try:
                                mtime = entry.stat().st_mtime
                                # 增量判断: 若该文件未被修改则跳过
                                if self._file_mtimes.get(entry.path, 0.0) >= mtime:
                                    continue
                                
                                results = CfbParser.parse_jumplist_file(entry.path)
                                for sname, lnk in results:
                                    item = normalize_item(
                                        target_path=lnk.target_path,
                                        arguments=lnk.arguments,
                                        last_used_at=lnk.access_time or lnk.write_time or int(mtime),
                                        use_count=1,
                                        source="jumplist_auto"
                                    )
                                    items.append(item)
                                self._file_mtimes[entry.path] = mtime
                            except Exception:
                                continue
            except Exception:
                pass

        # 2. 扫描 CustomDestinations (包含顺次排列的 LNK 结构)
        if os.path.exists(self.custom_dir):
            try:
                with os.scandir(self.custom_dir) as entries:
                    for entry in entries:
                        if entry.is_file() and entry.name.lower().endswith('.customdestinations-ms'):
                            try:
                                mtime = entry.stat().st_mtime
                                if self._file_mtimes.get(entry.path, 0.0) >= mtime:
                                    continue
                                
                                with open(entry.path, 'rb') as f:
                                    content = f.read()
                                
                                # CustomDestinations 通常在前若干字节后紧跟 LNK 头
                                # 搜索 LNK 头部特征 0x0000004C
                                pos = 0
                                while True:
                                    idx = content.find(b'\x4c\x00\x00\x00\x01\x14\x02\x00', pos)
                                    if idx == -1:
                                        break
                                    lnk = LnkParser.parse_bytes(content[idx:])
                                    if lnk.is_valid:
                                        item = normalize_item(
                                            target_path=lnk.target_path,
                                            arguments=lnk.arguments,
                                            last_used_at=lnk.access_time or int(mtime),
                                            use_count=1,
                                            source="jumplist_custom"
                                        )
                                        items.append(item)
                                    pos = idx + 76
                                
                                self._file_mtimes[entry.path] = mtime
                            except Exception:
                                continue
            except Exception:
                pass

        return items

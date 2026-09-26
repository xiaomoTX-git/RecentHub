"""
MruCollector: 读取 Office MRU (Word/Excel/PowerPoint) 与 Explorer RecentDocs
"""

import winreg
from typing import List
from app.collectors.base import BaseCollector
from app.core.models import RecentItem
from app.aggregator.normalizer import normalize_item
from app.parsers.time_helper import filetime_to_unix


def _parse_office_mru_time(vval: str, fallback: int) -> int:
    """从 Office MRU 值中解析 [T<十六进制FILETIME>] 时间戳，失败则回退到注册表键最后写入时间"""
    try:
        t_start = vval.find('[T')
        if t_start != -1:
            t_end = vval.find(']', t_start)
            if t_end > t_start + 2:
                ts = filetime_to_unix(int(vval[t_start + 2:t_end], 16))
                if ts > 0:
                    return ts
    except Exception:
        pass
    return fallback or 0


class MruCollector(BaseCollector):
    def __init__(self):
        super().__init__("office_mru")
        self.office_versions = ["16.0", "15.0", "14.0"]
        self.apps = ["Word", "Excel", "PowerPoint"]

    def is_available(self) -> bool:
        return True

    def collect(self) -> List[RecentItem]:
        items: List[RecentItem] = []
        
        # 1. 扫描 Office MRU
        for ver in self.office_versions:
            for app in self.apps:
                base_path = f"Software\\Microsoft\\Office\\{ver}\\{app}\\User MRU"
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base_path) as k:
                        subkeys_cnt = winreg.QueryInfoKey(k)[0]
                        for i in range(subkeys_cnt):
                            user_id = winreg.EnumKey(k, i)
                            file_mru_path = f"{base_path}\\{user_id}\\File MRU"
                            try:
                                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, file_mru_path) as fk:
                                    val_cnt = winreg.QueryInfoKey(fk)[1]
                                    try:
                                        key_mtime = filetime_to_unix(winreg.QueryInfoKey(fk)[2])
                                    except Exception:
                                        key_mtime = 0
                                    for v in range(val_cnt):
                                        vname, vval, _ = winreg.EnumValue(fk, v)
                                        if isinstance(vval, str) and '*' in vval:
                                            # Office 格式通常形如: [F00000000][T01D...]*C:\Path\To\File.docx
                                            parts = vval.split('*')
                                            if len(parts) >= 2:
                                                file_path = parts[-1]
                                                item = normalize_item(
                                                    target_path=file_path,
                                                    last_used_at=_parse_office_mru_time(vval, key_mtime),
                                                    source=f"office_{app.lower()}"
                                                )
                                                items.append(item)
                            except OSError:
                                pass
                except OSError:
                    pass

        return items

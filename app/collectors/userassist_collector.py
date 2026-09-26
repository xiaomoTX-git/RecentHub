"""
UserAssistCollector: 读取 Windows 注册表 UserAssist 运行痕迹
"""

import winreg
from typing import List
from app.collectors.base import BaseCollector
from app.core.models import RecentItem
from app.parsers.userassist_parser import UserAssistParser
from app.aggregator.normalizer import normalize_item


class UserAssistCollector(BaseCollector):
    def __init__(self):
        super().__init__("userassist")
        self.reg_base = r"Software\Microsoft\Windows\CurrentVersion\Explorer\UserAssist"

    def is_available(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_base):
                return True
        except OSError:
            return False

    def collect(self) -> List[RecentItem]:
        items: List[RecentItem] = []
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.reg_base) as base_k:
                subkey_count = winreg.QueryInfoKey(base_k)[0]
                for i in range(subkey_count):
                    guid = winreg.EnumKey(base_k, i)
                    count_path = f"{self.reg_base}\\{guid}\\Count"
                    try:
                        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, count_path) as count_k:
                            val_count = winreg.QueryInfoKey(count_k)[1]
                            for v in range(val_count):
                                name, val_bytes, _ = winreg.EnumValue(count_k, v)
                                if isinstance(val_bytes, bytes):
                                    rec = UserAssistParser.parse_value(name, val_bytes)
                                    if rec and rec.is_valid:
                                        item = normalize_item(
                                            target_path=rec.decoded_name,
                                            last_used_at=rec.last_run_time,
                                            use_count=rec.run_count,
                                            source=self.name
                                        )
                                        items.append(item)
                    except OSError:
                        continue
        except Exception:
            pass

        return items

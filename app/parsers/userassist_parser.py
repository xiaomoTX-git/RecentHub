"""
RecentHub UserAssist 注册表数据解析器
Windows UserAssist 记录了用户运行程序名称、运行频次与最后启动时间
键名经 ROT13 加密，键值为 72 字节 (Windows 7/10/11) 二进制结构
"""

import codecs
import struct
from dataclasses import dataclass
from typing import Optional
from app.parsers.time_helper import filetime_to_unix


@dataclass(slots=True)
class UserAssistRecord:
    raw_name: str
    decoded_name: str
    run_count: int
    focus_count: int
    focus_time_ms: int
    last_run_time: int  # Unix 时间戳
    is_valid: bool = False


class UserAssistParser:
    @staticmethod
    def decode_name(rot13_name: str) -> str:
        """对 ROT13 混淆字符串进行解码"""
        try:
            return codecs.decode(rot13_name, 'rot_13')
        except Exception:
            return rot13_name

    @classmethod
    def parse_value(cls, raw_name: str, raw_bytes: bytes) -> Optional[UserAssistRecord]:
        """
        解析单条 UserAssist 二进制值
        Win 7/8/10/11 结构为 72 字节:
          Offset 4..8: Run count (DWORD)
          Offset 8..12: Focus count (DWORD)
          Offset 12..16: Focus time in ms (DWORD)
          Offset 60..68: Last execution FILETIME (QWORD)
        """
        if not raw_bytes or len(raw_bytes) < 68:
            return None
        
        try:
            run_count = struct.unpack_from('<I', raw_bytes, 4)[0]
            focus_count = struct.unpack_from('<I', raw_bytes, 8)[0]
            focus_time_ms = struct.unpack_from('<I', raw_bytes, 12)[0]
            last_run_ft = struct.unpack_from('<Q', raw_bytes, 60)[0]
            
            last_run_unix = filetime_to_unix(last_run_ft)
            decoded = cls.decode_name(raw_name)
            
            # 过滤掉 GUID 辅助键、UWP 包装器及无意义噪音
            if decoded.startswith('{') and '}' in decoded and len(decoded) < 40:
                return None
            
            return UserAssistRecord(
                raw_name=raw_name,
                decoded_name=decoded,
                run_count=run_count,
                focus_count=focus_count,
                focus_time_ms=focus_time_ms,
                last_run_time=last_run_unix,
                is_valid=bool(decoded and last_run_unix > 0)
            )
        except Exception:
            return None

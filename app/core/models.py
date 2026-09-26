"""
RecentHub 核心数据模型 (轻量级 __slots__ 优化)
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class RecentItem:
    id: int = 0
    display_name: str = ""
    target_path: str = ""
    arguments: str = ""
    item_type: str = "file"      # "file" | "app" | "folder" | "url"
    extension: str = ""          # 小写扩展名，如 ".docx"
    pinyin_initials: str = ""    # 拼音首字母紧凑串，如 "gzbg"
    pinyin_full: str = ""        # 拼音全拼紧凑串，如 "mihayou" / "mhy"
    last_used_at: int = 0        # Unix 时间戳 (秒)
    use_count: int = 1           # 使用/打开次数
    exists_status: int = 1       # 1: 存在, 0: 已失效/丢失
    pinned: int = 0              # 1: 固定置顶, 0: 普通
    sources: List[str] = field(default_factory=list)  # 来源列表: ['recent_lnk', 'jumplist']
    score: float = 0.0           # 运行时动态搜索匹配与排序综合得分


@dataclass(slots=True)
class ExcludedRule:
    id: int = 0
    rule_type: str = "path_prefix"  # "path_prefix" | "extension" | "name_contains"
    pattern: str = ""

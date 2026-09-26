"""
RecentHub 采集器抽象基类
提供统一的采集接口与基于 mtime 的惰性变动检测
"""

import abc
import os
from typing import List, Tuple
from app.core.models import RecentItem


class BaseCollector(abc.ABC):
    def __init__(self, name: str):
        self.name = name
        self.last_check_mtime: float = 0.0

    @abc.abstractmethod
    def is_available(self) -> bool:
        """检查当前系统环境该数据源是否可用"""
        pass

    @abc.abstractmethod
    def collect(self) -> List[RecentItem]:
        """执行实际的数据采集并返回标准化后的条目列表"""
        pass

    def has_changed(self, target_dir_or_file: str) -> Tuple[bool, float]:
        """
        轻量级探测文件或目录自上次扫描后是否发生变动
        返回: (是否变动, 最新的mtime)
        """
        if not os.path.exists(target_dir_or_file):
            return False, 0.0
        try:
            curr_mtime = os.path.getmtime(target_dir_or_file)
            if curr_mtime > self.last_check_mtime:
                return True, curr_mtime
            return False, curr_mtime
        except Exception:
            # 探测失败时保留上次基线，避免游标被重置为 0 导致后续每次都全量重扫
            return True, self.last_check_mtime

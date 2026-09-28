"""
RecentHub 扫描与采集调度服务
负责多采集器调度、合并去重与入库
"""

import logging
import time
from typing import List, Optional
from app.collectors.recent_collector import RecentCollector
from app.collectors.jumplist_collector import JumpListCollector
from app.collectors.userassist_collector import UserAssistCollector
from app.collectors.mru_collector import MruCollector
from app.collectors.app_collector import AppCollector
from app.aggregator.merger import AggregatorMerger
from app.storage.db import StorageDB
from app.core.models import RecentItem

logger = logging.getLogger(__name__)


class ScanService:
    def __init__(self, db: StorageDB):
        self.db = db
        self.collectors = [
            RecentCollector(),
            JumpListCollector(),
            UserAssistCollector(),
            MruCollector(),
            AppCollector()
        ]

    def scan_all(self) -> int:
        """执行全源扫描并入库"""
        raw_items: List[RecentItem] = []
        for collector in self.collectors:
            try:
                if collector.is_available():
                    items = collector.collect()
                    raw_items.extend(items)
            except Exception:
                # 单个采集器失败不应中断整轮扫描，但必须留下可定位的日志
                logger.warning("采集器 %s 执行失败，已跳过", type(collector).__name__, exc_info=True)
                continue

        rules = self.db.get_excluded_rules()
        merged_items = AggregatorMerger.merge_items(raw_items, rules)
        count = self.db.upsert_items(merged_items)
        return count

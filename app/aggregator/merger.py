"""
RecentHub 聚合与去重合并器
按规范化绝对路径作为唯一键，融合多数据源的时效与频次
"""

from typing import Dict, List, Optional
from app.core.models import RecentItem, ExcludedRule


class AggregatorMerger:
    @staticmethod
    def is_excluded(item: RecentItem, rules: List[ExcludedRule]) -> bool:
        """检查条目是否符合排除规则"""
        path_lower = item.target_path.lower()
        name_lower = item.display_name.lower()
        ext_lower = item.extension.lower()
        
        for rule in rules:
            p = rule.pattern.lower().strip()
            if not p:
                continue
            if rule.rule_type == 'path_prefix' and path_lower.startswith(p):
                return True
            elif rule.rule_type == 'extension' and ext_lower == p:
                return True
            elif rule.rule_type == 'name_contains' and p in name_lower:
                return True
        return False

    @classmethod
    def merge_items(
        cls,
        raw_items: List[RecentItem],
        rules: Optional[List[ExcludedRule]] = None
    ) -> List[RecentItem]:
        """对原始条目集合进行去重、合并与排除规则过滤"""
        rules = rules or []
        merged_map: Dict[str, RecentItem] = {}
        
        for item in raw_items:
            # 基础有效性过滤
            if not item.target_path or not item.display_name:
                continue
            
            # 排除规则过滤
            if cls.is_excluded(item, rules):
                continue
            
            key = item.target_path.lower()
            if key not in merged_map:
                merged_map[key] = item
            else:
                existing = merged_map[key]
                # 合并最新访问时间 (取较大值)
                existing.last_used_at = max(existing.last_used_at, item.last_used_at)
                # 累计使用次数
                existing.use_count += item.use_count
                # 合并固定状态
                existing.pinned = max(existing.pinned, item.pinned)
                # 合并存在状态
                existing.exists_status = max(existing.exists_status, item.exists_status)
                # 合并数据来源
                for src in item.sources:
                    if src and src not in existing.sources:
                        existing.sources.append(src)
                # 若已有参数为空而新项有参数，进行补充
                if not existing.arguments and item.arguments:
                    existing.arguments = item.arguments
        
        # 默认按最后使用时间倒序排列
        return sorted(merged_map.values(), key=lambda x: (x.pinned, x.last_used_at), reverse=True)

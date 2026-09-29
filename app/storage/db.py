"""
RecentHub SQLite + FTS5 高性能本地存储层
支持 WAL 模式高并发读写、Trigram 倒排全文检索与动态打分排序
"""

import logging
import os
import sqlite3
import threading
import time
from typing import List, Optional, Tuple
from app.core import paths
from app.core.models import RecentItem, ExcludedRule, TYPE_EXTENSION_MAP
from app.parsers.pinyin_engine import match_score

logger = logging.getLogger(__name__)


def item_matches_filters(
    item: RecentItem,
    item_type: Optional[str] = None,
    exts: Optional[List[str]] = None,
    mtime_after: Optional[int] = None,
) -> bool:
    """判断单条数据是否命中全部筛选条件 (类型 / 扩展名 / 时间下界)。

    语义与 StorageDB._build_type_filter 及 query_items 的附加过滤完全对齐，
    供 UI 侧过滤流式追加的全盘检索结果使用 (那些结果不经过 SQL 过滤)。
    """
    if item_type and item_type != 'all':
        mapped = TYPE_EXTENSION_MAP.get(item_type)
        if mapped:
            if (item.extension or '').lower() not in mapped:
                return False
        elif item.item_type != item_type:
            return False
    if exts:
        if (item.extension or '').lower() not in set(exts):
            return False
    if mtime_after and (item.last_used_at or 0) < mtime_after:
        return False
    return True


class StorageDB:

    def __init__(self, db_path: Optional[str] = None):
        self._is_memory = (db_path == ":memory:")
        self._local = threading.local()
        self._mem_conn = None
        self._all_conns: List[sqlite3.Connection] = []
        if not db_path:
            base_dir = paths.db_dir()
            self.db_path = os.path.join(base_dir, "recenthub.db")
        else:
            self.db_path = db_path
            
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        """按线程复用同一连接：避免每次按键检索都新建连接并重复执行 PRAGMA"""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            return conn

        if self._is_memory:
            # 内存库需跨线程共享同一实例，否则各线程会看到彼此独立的空库
            if self._mem_conn is None:
                self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
                self._mem_conn.row_factory = sqlite3.Row
                self._all_conns.append(self._mem_conn)
            return self._mem_conn

        conn = sqlite3.connect(self.db_path, timeout=3.0)
        conn.row_factory = sqlite3.Row
        # 性能优化配置
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA cache_size = -32000;")  # 32MB 内存缓存
        conn.execute("PRAGMA busy_timeout = 3000;")  # 多线程并发写入等待而非直接抛异常
        self._local.conn = conn
        self._all_conns.append(conn)
        return conn

    def close_all(self):
        """释放所有线程已建立的连接 (退出前调用)"""
        for conn in self._all_conns:
            try:
                conn.close()
            except Exception:
                pass
        self._all_conns = []
        if hasattr(self._local, "conn"):
            self._local.conn = None

    def shrink_memory(self):
        """释放 SQLite 内部未使用的缓存池，最小化后台常驻内存"""
        try:
            with self.get_connection() as conn:
                conn.execute("PRAGMA shrink_memory;")
        except Exception:
            logger.debug("shrink_memory 执行失败 (不影响主流程)", exc_info=True)


    def _init_db(self):
        with self.get_connection() as conn:
            # 1. 主项目表
            conn.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                display_name TEXT NOT NULL,
                target_path TEXT NOT NULL UNIQUE,
                arguments TEXT DEFAULT '',
                item_type TEXT NOT NULL,
                extension TEXT DEFAULT '',
                pinyin_initials TEXT DEFAULT '',
                pinyin_full TEXT DEFAULT '',
                last_used_at INTEGER NOT NULL,
                use_count INTEGER DEFAULT 1,
                exists_status INTEGER DEFAULT 1,
                pinned INTEGER DEFAULT 0,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            );
            """)

            # 字段自动迁移补齐 (热升级兼容)
            try:
                conn.execute("ALTER TABLE items ADD COLUMN pinyin_full TEXT DEFAULT '';")
            except Exception:
                # 列已存在属预期内的正常路径，仅 DEBUG 记录
                logger.debug("items.pinyin_full 列已存在，跳过迁移", exc_info=True)

            # 2. 索引
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_last_used ON items(last_used_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_type ON items(item_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_ext ON items(extension);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_items_pinned ON items(pinned DESC, last_used_at DESC);")

            # 3. 来源表
            conn.execute("""
            CREATE TABLE IF NOT EXISTS item_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                source_type TEXT NOT NULL,
                source_detail TEXT DEFAULT '',
                discovered_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(item_id, source_type)
            );
            """)

            # 4. 排除规则表
            conn.execute("""
            CREATE TABLE IF NOT EXISTS excluded_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_type TEXT NOT NULL,
                pattern TEXT NOT NULL UNIQUE
            );
            """)

            # 5. FTS5 全文索引虚表 (Trigram)
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                display_name,
                target_path,
                extension,
                pinyin_initials,
                content='items',
                content_rowid='id',
                tokenize='trigram'
            );
            """)

            # 6. FTS5 自动同步触发器
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_items_ai AFTER INSERT ON items BEGIN
                INSERT INTO items_fts(rowid, display_name, target_path, extension, pinyin_initials)
                VALUES (new.id, new.display_name, new.target_path, new.extension, new.pinyin_initials);
            END;
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_items_ad AFTER DELETE ON items BEGIN
                INSERT INTO items_fts(items_fts, rowid, display_name, target_path, extension, pinyin_initials)
                VALUES ('delete', old.id, old.display_name, old.target_path, old.extension, old.pinyin_initials);
            END;
            """)
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS trg_items_au AFTER UPDATE ON items BEGIN
                INSERT INTO items_fts(items_fts, rowid, display_name, target_path, extension, pinyin_initials)
                VALUES ('delete', old.id, old.display_name, old.target_path, old.extension, old.pinyin_initials);
                INSERT INTO items_fts(rowid, display_name, target_path, extension, pinyin_initials)
                VALUES (new.id, new.display_name, new.target_path, new.extension, new.pinyin_initials);
            END;
            """)

    def upsert_items(self, items: List[RecentItem]) -> int:
        """批量更新/插入条目"""
        if not items:
            return 0
        
        now = int(time.time())
        inserted_or_updated = 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for it in items:
                cursor.execute("""
                INSERT INTO items (
                    display_name, target_path, arguments, item_type,
                    extension, pinyin_initials, pinyin_full, last_used_at, use_count,
                    exists_status, pinned
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(target_path) DO UPDATE SET
                    last_used_at = MAX(items.last_used_at, excluded.last_used_at),
                    use_count = MAX(items.use_count, excluded.use_count),
                    pinned = MAX(items.pinned, excluded.pinned),
                    exists_status = excluded.exists_status,
                    display_name = excluded.display_name,
                    item_type = excluded.item_type,
                    pinyin_initials = excluded.pinyin_initials,
                    pinyin_full = excluded.pinyin_full
                RETURNING id;
                """, (
                    it.display_name, it.target_path, it.arguments, it.item_type,
                    it.extension, it.pinyin_initials, it.pinyin_full or '', it.last_used_at or now,
                    it.use_count, it.exists_status, it.pinned
                ))
                row = cursor.fetchone()
                if row:
                    item_id = row[0]
                    it.id = item_id
                    inserted_or_updated += 1
                    
                    # 写入来源关联
                    for src in it.sources:
                        cursor.execute("""
                        INSERT OR IGNORE INTO item_sources (item_id, source_type, source_detail)
                        VALUES (?, ?, ?);
                        """, (item_id, src, ""))
                        
        return inserted_or_updated

    def _build_type_filter(self, item_type: Optional[str]):
        if not item_type or item_type == 'all':
            return "", []
        exts = TYPE_EXTENSION_MAP.get(item_type)
        if exts:
            return f" AND LOWER(i.extension) IN ({','.join(['?']*len(exts))})", list(exts)
        return " AND i.item_type = ?", [item_type]

    @staticmethod
    def _build_extra_filter(exts: Optional[List[str]], mtime_after: Optional[int]):
        """构建搜索语法附加过滤 (ext:xxx / >7d 时间下界)，语义与 item_matches_filters 对齐。"""
        clause = ""
        params: List = []
        if exts:
            norm = [e.lower() if e.startswith('.') else '.' + e.lower() for e in exts]
            clause += f" AND LOWER(i.extension) IN ({','.join(['?'] * len(norm))})"
            params.extend(norm)
        if mtime_after:
            clause += " AND i.last_used_at >= ?"
            params.append(int(mtime_after))
        return clause, params

    def query_items(
        self,
        query: str = "",
        item_type: Optional[str] = None,
        limit: int = 200,
        offset: int = 0,
        exts: Optional[List[str]] = None,
        mtime_after: Optional[int] = None
    ) -> List[RecentItem]:
        """
        混合高阶查询：
        1. 空查询: 按置顶与时间倒序直接拉取
        2. 关键字查询:
           - 若有关键字，结合 FTS5 与 LIKE 召回候选
           - 使用 match_score + 时间衰减进行二次精准打分重排
        exts / mtime_after 为搜索语法附加过滤，与类型过滤合并后作用于全部召回分支。
        """
        q = query.strip()
        now = time.time()
        type_clause, type_params = self._build_type_filter(item_type)
        extra_clause, extra_params = self._build_extra_filter(exts, mtime_after)
        type_clause += extra_clause
        type_params = list(type_params) + extra_params
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 情况 1: 空查询
            if not q:
                sql = """
                SELECT i.*, GROUP_CONCAT(s.source_type) AS sources
                FROM items i
                LEFT JOIN item_sources s ON i.id = s.item_id
                WHERE 1=1
                """
                sql += type_clause
                params = list(type_params)
                sql += " GROUP BY i.id ORDER BY i.pinned DESC, i.last_used_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                rows = cursor.execute(sql, params).fetchall()
                results = []
                for r in rows:
                    item = self._row_to_item(r)
                    results.append(item)
                return results

            # 情况 2: 带有搜索关键词
            candidate_map = {}
            like_pat = f"%{q}%"
            
            # FTS5 Trigram 召回 (仅当字符数>=3 时触发)
            if len(q) >= 3:
                try:
                    fts_sql = """
                    SELECT i.*, GROUP_CONCAT(s.source_type) AS sources
                    FROM items_fts f
                    JOIN items i ON f.rowid = i.id
                    LEFT JOIN item_sources s ON i.id = s.item_id
                    WHERE items_fts MATCH ?
                    """
                    fts_sql += type_clause
                    # 必须整体加双引号转为短语查询：否则 * ( ) - " 等 FTS5 语法字符会直接抛错，
                    # 导致倒排索引召回被静默跳过，退化到全表 LIKE
                    fts_params = ['"' + q.replace('"', '""') + '"'] + type_params
                    fts_sql += " GROUP BY i.id LIMIT 500"
                    
                    for r in cursor.execute(fts_sql, fts_params).fetchall():
                        candidate_map[r['id']] = r
                except Exception:
                    # FTS5 语法异常时静默降级到 LIKE 全表召回，属可接受的降级路径
                    logger.debug("FTS5 召回失败，降级到 LIKE 兜底", exc_info=True)

            # LIKE 快速兜底召回 (支持多关键词、连拼与品牌拼音智能衍生)
            q_clean = q.lower().replace(" ", "").replace("-", "").replace("_", "")
            tokens = [t.lower() for t in q.split() if t]
            kw_set = set([q.lower(), q_clean] + tokens)
            if any(k in q.lower() for k in ("miho", "mhy", "miha")):
                kw_set.update(["米哈", "mihoyo", "mihomo"])

            # 区分主干关键词 (长度>=3 或 中文)，防止单一2字母短音节如 "yu" 污染全盘结果
            long_kws = [k for k in kw_set if len(k) >= 3 or any('一' <= ch <= '鿿' for ch in k)]
            target_kws = long_kws if long_kws else [k for k in kw_set if len(k) >= 2]

            for kw in target_kws:
                pat = f"%{kw}%"
                like_sql = """
                SELECT i.*, GROUP_CONCAT(s.source_type) AS sources
                FROM items i
                LEFT JOIN item_sources s ON i.id = s.item_id
                WHERE (i.display_name LIKE ? OR i.pinyin_initials LIKE ? OR i.pinyin_full LIKE ? OR i.target_path LIKE ? OR i.extension LIKE ?)
                """
                like_sql += type_clause
                like_params = [pat, pat, pat, pat, pat] + type_params
                like_sql += " GROUP BY i.id ORDER BY i.pinned DESC, i.last_used_at DESC LIMIT 300"
                
                for r in cursor.execute(like_sql, like_params).fetchall():
                    candidate_map[r['id']] = r
            
            # 在内存中进行高阶多维度智能打分重排
            scored_items: List[RecentItem] = []
            for r in candidate_map.values():
                item = self._row_to_item(r)
                m_score = match_score(item.display_name, item.pinyin_initials, q)
                
                # 全拼与别名加权判定
                if item.pinyin_full:
                    for kw in target_kws:
                        if kw in item.pinyin_full.lower():
                            m_score = max(m_score, 85)
                            break
                if any(kw in item.display_name.lower() for kw in target_kws):
                    m_score = max(m_score, 90)
                elif any(kw in item.target_path.lower() for kw in target_kws):
                    m_score = max(m_score, 60)
                
                # 时间半衰期衰减分 (7天半衰期)
                age_days = max(0, (now - item.last_used_at) / 86400.0)
                time_weight = 100.0 * (2.0 ** (-age_days / 7.0))
                
                # 置顶额外加权
                pin_weight = 10000.0 if item.pinned else 0.0
                
                # 频次微量加权
                count_weight = min(20.0, item.use_count * 2.0)
                
                final_score = (m_score * 10.0) + time_weight + count_weight + pin_weight
                item.score = final_score
                scored_items.append(item)

            # 按评分倒序
            scored_items.sort(key=lambda x: x.score, reverse=True)
            return scored_items[offset:offset + limit]

    def _row_to_item(self, r: sqlite3.Row) -> RecentItem:
        sources_str = r['sources'] if 'sources' in r.keys() else ''
        sources_list = [s for s in sources_str.split(',') if s] if sources_str else []
        p_full = r['pinyin_full'] if 'pinyin_full' in r.keys() else ''
        return RecentItem(
            id=r['id'],
            display_name=r['display_name'],
            target_path=r['target_path'],
            arguments=r['arguments'] or '',
            item_type=r['item_type'],
            extension=r['extension'] or '',
            pinyin_initials=r['pinyin_initials'] or '',
            pinyin_full=p_full or '',
            last_used_at=r['last_used_at'],
            use_count=r['use_count'],
            exists_status=r['exists_status'],
            pinned=r['pinned'],
            sources=sources_list
        )

    def set_pinned(self, item_id: int, pinned: bool) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("UPDATE items SET pinned = ? WHERE id = ?", (1 if pinned else 0, item_id))
            return cursor.rowcount > 0

    def delete_item(self, item_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
            return cursor.rowcount > 0

    def clear_all(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM items;")
            conn.execute("DELETE FROM item_sources;")
            conn.execute("DELETE FROM items_fts;")

    def add_excluded_rule(self, rule_type: str, pattern: str):
        with self.get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO excluded_rules (rule_type, pattern) VALUES (?, ?)", (rule_type, pattern.lower().strip()))

    def get_excluded_rules(self) -> List[ExcludedRule]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM excluded_rules").fetchall()
            return [ExcludedRule(id=r['id'], rule_type=r['rule_type'], pattern=r['pattern']) for r in rows]

    def remove_excluded_rule(self, rule_id: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.execute("DELETE FROM excluded_rules WHERE id = ?", (rule_id,))
            return cursor.rowcount > 0

    def clear_excluded_rules(self):
        with self.get_connection() as conn:
            conn.execute("DELETE FROM excluded_rules;")

    @staticmethod
    def _like_escape(pattern: str) -> str:
        """转义 LIKE 通配符，确保匹配为字面量，与 merger.is_excluded 语义一致"""
        return pattern.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    def purge_excluded_items(self, rules: List[ExcludedRule]) -> int:
        """按现有排除规则删除已入库的匹配条目，使规则即时生效而非仅影响下次扫描。

        匹配语义与 app/aggregator/merger.py 的 is_excluded() 严格对齐：
        path_prefix → 路径前缀；name_contains → 文件名包含；extension → 扩展名相等。
        """
        conditions: List[str] = []
        params: List[str] = []
        for rule in rules:
            p = (rule.pattern or "").lower().strip()
            if not p:
                continue
            if rule.rule_type == 'path_prefix':
                conditions.append("LOWER(target_path) LIKE ? ESCAPE '\\'")
                params.append(self._like_escape(p) + "%")
            elif rule.rule_type == 'extension':
                conditions.append("LOWER(extension) = ?")
                params.append(p)
            elif rule.rule_type == 'name_contains':
                conditions.append("LOWER(display_name) LIKE ? ESCAPE '\\'")
                params.append("%" + self._like_escape(p) + "%")

        if not conditions:
            return 0

        where = " OR ".join(conditions)
        with self.get_connection() as conn:
            # item_sources 未开启外键级联，需显式清理，避免留下孤儿来源行
            conn.execute(f"DELETE FROM item_sources WHERE item_id IN (SELECT id FROM items WHERE {where})", params)
            cursor = conn.execute(f"DELETE FROM items WHERE {where}", params)
            return cursor.rowcount

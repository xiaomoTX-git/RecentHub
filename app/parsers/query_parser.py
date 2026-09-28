r"""
RecentHub 高级检索语法解析器

在自然语言关键词之外，支持叠加精确过滤条件：

- ``ext:pdf`` / ``ext:pdf,docx`` / ``ext:.xlsx``  扩展名过滤
- ``type:word|excel|pdf|code|doc|app|folder|url``  类型过滤 (复用 db 侧的类型键)
- ``>7d`` / ``>24h`` / ``>30m`` / ``>2w``          最后使用时间下界 (相对当前时刻)
- 其余 token 全部归入 ``text``，作为真正参与全文检索的关键词

设计约定：只输入 ``ext:pdf`` 而不含其它关键词时，``text`` 为空串，
查询会走「空查询分支」返回最近的 PDF —— 与直觉一致。
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

_EXT_RE = re.compile(r'^ext:(.+)$', re.IGNORECASE)
_TYPE_RE = re.compile(r'^type:(.+)$', re.IGNORECASE)
_AGE_RE = re.compile(r'^>(\d+)([smhdw])$', re.IGNORECASE)

_UNIT_SECONDS = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}

# type: 语法接受的类型键 (与 db.TYPE_EXTENSION_MAP / items.item_type 对齐)
VALID_TYPE_KEYS = {'word', 'excel', 'pdf', 'code', 'doc', 'app', 'folder', 'url'}


@dataclass
class QuerySpec:
    text: str = ""
    exts: List[str] = field(default_factory=list)
    type_key: Optional[str] = None
    mtime_after: Optional[int] = None


def _normalize_ext(raw: str) -> List[str]:
    """把 ext: 的值规整为带点的小写扩展名列表，容忍 .xlsx / xlsx / *.xlsx 三种写法"""
    out: List[str] = []
    for part in raw.replace(';', ',').split(','):
        e = part.strip().lower().lstrip('*')
        if not e:
            continue
        if not e.startswith('.'):
            e = '.' + e
        out.append(e)
    return out


def parse_query(raw: str) -> QuerySpec:
    """解析检索串，返回结构化 QuerySpec"""
    spec = QuerySpec()
    if not raw:
        return spec

    text_tokens: List[str] = []
    for token in raw.split():
        m = _EXT_RE.match(token)
        if m:
            spec.exts.extend(_normalize_ext(m.group(1)))
            continue

        m = _TYPE_RE.match(token)
        if m:
            key = m.group(1).strip().lower()
            # 非法类型键直接丢弃该 token：既不生效也不污染全文检索
            if key in VALID_TYPE_KEYS:
                spec.type_key = key
            continue

        m = _AGE_RE.match(token)
        if m:
            spec.mtime_after = int(time.time()) - int(m.group(1)) * _UNIT_SECONDS[m.group(2).lower()]
            continue

        text_tokens.append(token)

    spec.text = " ".join(text_tokens)

    if spec.exts:
        seen = set()
        deduped: List[str] = []
        for e in spec.exts:
            if e not in seen:
                seen.add(e)
                deduped.append(e)
        spec.exts = deduped

    return spec
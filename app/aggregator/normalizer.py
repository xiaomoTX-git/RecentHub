"""
RecentHub 路径规范化与元数据提纯器
负责环境展开、长路径转换、文件类型推断与拼音简码计算
"""

import os
import ctypes
from typing import Tuple
from app.core.models import RecentItem
from app.parsers.pinyin_engine import get_initials, get_pinyin_full

_APP_EXTENSIONS = {'.exe', '.cmd', '.bat', '.ps1', '.msi', '.vbs'}


def get_long_path(path: str) -> str:
    """使用 Win32 API 将 8.3 格式短路径转换为系统真实长路径"""
    if not path or not os.path.exists(path):
        return path
    try:
        buf = ctypes.create_unicode_buffer(1024)
        res = ctypes.windll.kernel32.GetLongPathNameW(path, buf, 1024)
        if 0 < res < 1024:
            return buf.value
    except Exception:
        pass
    return path


def infer_item_type(path: str, ext: str) -> str:
    """推断条目类型: 'app' | 'folder' | 'url' | 'file'"""
    p_lower = path.lower()
    if p_lower.startswith(('http://', 'https://', 'ftp://')):
        return 'url'
    
    if ext in _APP_EXTENSIONS:
        return 'app'
    
    # 快速探测目录
    if os.path.isdir(path):
        return 'folder'
    
    return 'file'


def normalize_item(
    target_path: str,
    display_name: str = "",
    arguments: str = "",
    last_used_at: int = 0,
    use_count: int = 1,
    source: str = "",
    pinned: int = 0
) -> RecentItem:
    """标准化并构建 RecentItem 对象"""
    # 1. 展开环境变量并清理多余字符
    path = os.path.expandvars(target_path.strip().strip('"').strip("'"))
    path = os.path.normpath(path)
    path = get_long_path(path)
    
    # 2. 提取扩展名并统一小写
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    
    # 3. 提取显示名称
    if not display_name:
        display_name = os.path.basename(path)
        if not display_name:
            display_name = path
    
    # 4. 判断类型
    item_type = infer_item_type(path, ext)
    
    # 5. 计算拼音首字母简码与全拼别名
    pinyin = get_initials(display_name)
    pinyin_full = get_pinyin_full(display_name)
    
    # 6. 探测是否存在 (先默认设为1，异步由服务层精确核验)
    exists = 1 if os.path.exists(path) else 0
    
    sources = [source] if source else []
    
    return RecentItem(
        id=0,
        display_name=display_name,
        target_path=path,
        arguments=arguments.strip(),
        item_type=item_type,
        extension=ext,
        pinyin_initials=pinyin,
        pinyin_full=pinyin_full,
        last_used_at=last_used_at,
        use_count=max(1, use_count),
        exists_status=exists,
        pinned=pinned,
        sources=sources
    )

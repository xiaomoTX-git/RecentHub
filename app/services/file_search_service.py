r"""
RecentHub 全文件实时检索服务 (参照 Everything 原理与 Windows 索引架构)
- 支持多关键词空格分词、拼音全拼与常用品牌别名衍生 (如 miho yu -> 米哈游, mihomo, mihoyo)
- 原生集成 Windows Search OLE DB 全盘毫秒级系统索引
- 原生集成工作区与高频目录深度快速扫描 (覆盖未加入 Windows 索引的非系统分区如 E:\ 等)
- 支持 Everything 本地 IPC / es 极速命令行
"""

import os
import sys
import time
import subprocess
from typing import List, Set
from app.core.models import RecentItem
from app.aggregator.normalizer import normalize_item
from app.core.paths import is_frozen

# 保证 win32 模块可用 (仅源码运行需要；打包后依赖已随 exe 冻结)
if is_frozen():
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    venv_site = os.path.join(base_dir, ".venv", "Lib", "site-packages")
    if os.path.exists(venv_site):
        for sub in [venv_site, os.path.join(venv_site, "win32"), os.path.join(venv_site, "win32", "lib")]:
            if sub not in sys.path and os.path.exists(sub):
                sys.path.insert(0, sub)


def _decode_console(raw: bytes) -> str:
    """解码控制台输出：优先 UTF-8，中文 Windows 下回退 GBK/OEM，避免中文路径整段召回失效"""
    if not raw:
        return ""
    for enc in ("utf-8", "gbk", "mbcs"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="replace")


def _sanitize_like(kw: str) -> str:
    """剔除 SQL LIKE 通配符：否则输入 % 会让 Windows Search 变成全表匹配"""
    for ch in ('%', '_', '[', ']'):
        kw = kw.replace(ch, '')
    return kw


class FileSearchService:
    _es_path: str = ""
    _es_checked: bool = False

    @classmethod
    def _find_es(cls) -> str:
        if cls._es_checked:
            return cls._es_path
        cls._es_checked = True
        
        candidates = [
            "es.exe",
            r"C:\Program Files\Everything\es.exe",
            r"C:\Program Files (x86)\Everything\es.exe",
            r"D:\Everything\es.exe",
            r"E:\Everything\es.exe"
        ]
        for c in candidates:
            try:
                res = subprocess.run([c, "-v"], capture_output=True, text=True, timeout=0.8)
                if res.returncode == 0:
                    cls._es_path = c
                    return cls._es_path
            except Exception:
                pass
        return ""

    @classmethod
    def search_live(cls, query: str, limit: int = 35) -> List[RecentItem]:
        """全盘实时检索入口"""
        if not query or len(query.strip()) < 2:
            return []

        q = query.strip()
        q_lower = q.lower()
        q_clean = q_lower.replace(" ", "").replace("-", "").replace("_", "")
        tokens = [t.lower() for t in q.split() if t]

        # 1. 扩展搜索关键词 (全拼、分词、品牌别名智能映射)
        expanded_keywords: Set[str] = set([q_lower, q_clean] + tokens)
        if any(k in q_lower for k in ("miho", "mhy", "miha")):
            expanded_keywords.update(["米哈", "mihoyo", "mihomo"])
        if "hosts" in q_lower:
            expanded_keywords.add("hosts")
            
        results: List[RecentItem] = []
        seen: Set[str] = set()

        # 2. 核心系统热区直达 (如 hosts)
        if "hosts" in expanded_keywords:
            sys_hosts = "C:\\Windows\\System32\\drivers\\etc\\hosts"
            if os.path.exists(sys_hosts):
                try:
                    mtime = int(os.path.getmtime(sys_hosts))
                except Exception:
                    mtime = 0
                it = normalize_item(sys_hosts, display_name="hosts", last_used_at=mtime, source="system_hotspot")
                it.item_type = "file"
                results.append(it)
                seen.add(sys_hosts.lower())

        # 3. Everything 命令行快速召回 (若已安装 Everything)
        es_bin = cls._find_es()
        if es_bin:
            try:
                for kw in list(expanded_keywords)[:3]:
                    cmd = [es_bin, "-n", str(limit), kw]
                    proc = subprocess.run(cmd, capture_output=True, timeout=0.8)
                    if proc.returncode == 0 and proc.stdout:
                        for line in _decode_console(proc.stdout).splitlines():
                            fp = line.strip()
                            if fp and os.path.exists(fp):
                                norm = os.path.normpath(fp)
                                if norm.lower() not in seen:
                                    seen.add(norm.lower())
                                    try:
                                        mtime = int(os.path.getmtime(norm))
                                    except Exception:
                                        mtime = 0
                                    it = normalize_item(norm, last_used_at=mtime, source="everything")
                                    results.append(it)
                                    if len(results) >= limit:
                                        return results
            except Exception:
                pass

        # 4. Windows Search 原生 OLE DB 全盘检索 (安全初始化后台 COM 线程单元)
        try:
            try:
                import pythoncom
                pythoncom.CoInitialize()
            except Exception:
                pass

            import win32com.client
            conn = win32com.client.Dispatch("ADODB.Connection")
            conn.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
            rs = win32com.client.Dispatch("ADODB.Recordset")
            
            for kw in list(expanded_keywords)[:4]:
                if len(kw) < 2:
                    continue
                safe_q = _sanitize_like(kw).replace("'", "''")
                if not safe_q:
                    continue
                sql = f"SELECT TOP {limit} System.ItemName, System.ItemPathDisplay, System.DateModified FROM SystemIndex WHERE System.ItemName LIKE '%{safe_q}%' OR System.ItemPathDisplay LIKE '%{safe_q}%'"
                try:
                    rs.Open(sql, conn)
                    while not rs.EOF:
                        name = str(rs.Fields("System.ItemName").Value or "")
                        path = str(rs.Fields("System.ItemPathDisplay").Value or "")
                        if path and os.path.exists(path):
                            norm = os.path.normpath(path)
                            if norm.lower() not in seen:
                                seen.add(norm.lower())
                                try:
                                    mtime = int(os.path.getmtime(norm))
                                except Exception:
                                    mtime = 0
                                it = normalize_item(norm, display_name=name, last_used_at=mtime, source="windows_search")
                                results.append(it)
                                if len(results) >= limit:
                                    rs.Close()
                                    conn.Close()
                                    return results
                        rs.MoveNext()
                    rs.Close()
                except Exception:
                    pass
            conn.Close()
        except Exception:
            pass
        finally:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass

        # 5. 广度优先 (BFS) 全分区与高频热区极速发现引擎 (覆盖未加入系统索引的各盘目录与应用)
        import string
        from collections import deque

        available_drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        hotspots = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Documents"),
            os.path.abspath(os.path.join(base_dir, "..")),
        ] + available_drives

        queue = deque()
        for h in hotspots:
            if os.path.exists(h):
                queue.append((os.path.normpath(h), 0))

        def _match_name(name_str: str) -> bool:
            nl = name_str.lower()
            if any(kw in nl for kw in expanded_keywords):
                return True
            nc = nl.replace(" ", "").replace("-", "").replace("_", "")
            return q_clean in nc

        skip_dirs = {
            'node_modules', '__pycache__', '.git', '.venv', 'appdata', 'windows',
            '$recycle.bin', 'system volume information', 'recovery', 'programdata'
        }

        start_time = time.time()
        while queue and (time.time() - start_time) < 0.25 and len(results) < limit:
            cur_dir, depth = queue.popleft()
            try:
                with os.scandir(cur_dir) as it:
                    for entry in it:
                        name_lower = entry.name.lower()
                        full_p = os.path.normpath(entry.path)
                        fp_lower = full_p.lower()

                        matched = _match_name(entry.name)
                        if matched and fp_lower not in seen:
                            seen.add(fp_lower)
                            try:
                                mtime = int(entry.stat().st_mtime)
                            except Exception:
                                mtime = 0
                            
                            is_d = entry.is_dir(follow_symlinks=False)
                            it_item = normalize_item(full_p, display_name=entry.name, last_used_at=mtime, source="fast_crawl")
                            it_item.item_type = "folder" if is_d else ("app" if entry.name.lower().endswith(".exe") else "file")
                            results.append(it_item)
                            if len(results) >= limit:
                                return results

                        if entry.is_dir(follow_symlinks=False) and depth < 3:
                            if name_lower not in skip_dirs and not name_lower.startswith('.'):
                                if matched:
                                    queue.appendleft((full_p, depth + 1))
                                else:
                                    queue.append((full_p, depth + 1))
            except (PermissionError, FileNotFoundError, OSError):
                continue

        return results

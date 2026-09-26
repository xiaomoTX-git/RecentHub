"""
RecentHub 已安装应用收集器 (AppCollector)
扫描开始菜单、桌面与系统 App Paths，收录微信、QQ、浏览器、VS Code 等全量系统现有应用
支持快捷方式智能工作目录回退与 .lnk 原生调用兜底
"""

import os
import winreg
from typing import List, Set
from app.collectors.base import BaseCollector
from app.core.models import RecentItem
from app.parsers.lnk_parser import LnkParser
from app.aggregator.normalizer import normalize_item


class AppCollector(BaseCollector):
    def __init__(self):
        super().__init__("apps")

    def is_available(self) -> bool:
        return True

    def collect(self) -> List[RecentItem]:
        items: List[RecentItem] = []
        seen_targets: Set[str] = set()

        # 1. 扫描开始菜单与桌面快捷方式
        scan_dirs = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%USERPROFILE%\Desktop"),
            r"C:\Users\Public\Desktop"
        ]

        for d in scan_dirs:
            if not os.path.exists(d):
                continue
            for root, _, files in os.walk(d):
                for f in files:
                    if not f.lower().endswith(".lnk"):
                        continue
                    if "卸载" in f or "uninstall" in f.lower():
                        continue
                        
                    full_lnk = os.path.join(root, f)
                    try:
                        info = LnkParser.parse_file(full_lnk)
                        target = info.target_path
                        
                        # 智能回退机制
                        if not target or not os.path.exists(target):
                            if info.working_dir and os.path.exists(info.working_dir):
                                for cand in os.listdir(info.working_dir):
                                    if cand.lower().endswith(".exe") and "uninstall" not in cand.lower():
                                        target = os.path.join(info.working_dir, cand)
                                        break
                                        
                        if not target or not os.path.exists(target):
                            target = full_lnk  # 快捷方式本身即为可执行入口
                        
                        target_norm = os.path.normpath(target)
                        if target_norm.lower() in seen_targets:
                            continue

                        seen_targets.add(target_norm.lower())
                        display_name = f[:-4]  # 去掉 .lnk 后缀，例如 "微信"
                        mtime = info.access_time or int(os.path.getmtime(full_lnk))
                        
                        item = normalize_item(
                            target_path=target_norm,
                            display_name=display_name,
                            arguments=info.arguments,
                            last_used_at=mtime,
                            use_count=1,
                            source=self.name
                        )
                        item.item_type = "app"
                        items.append(item)

                        # 伴随主程序发现：收录同一应用安装目录下的主执行体 (如 leigod.exe 与 leigod_launcher.exe)
                        app_dir = os.path.dirname(target_norm)
                        if os.path.isdir(app_dir) and app_dir not in (r"C:WindowsSystem32", r"C:Windows"):
                            try:
                                for cand in os.listdir(app_dir):
                                    if cand.lower().endswith(".exe") and "uninstall" not in cand.lower():
                                        cand_path = os.path.normpath(os.path.join(app_dir, cand))
                                        if cand_path.lower() not in seen_targets and os.path.exists(cand_path):
                                            seen_targets.add(cand_path.lower())
                                            cand_mtime = int(os.path.getmtime(cand_path))
                                            c_item = normalize_item(
                                                target_path=cand_path,
                                                display_name=cand[:-4],
                                                last_used_at=cand_mtime,
                                                use_count=1,
                                                source=self.name
                                            )
                                            c_item.item_type = "app"
                                            items.append(c_item)
                            except Exception:
                                pass
                    except Exception:
                        continue

        # 2. 扫描注册表 App Paths
        reg_roots = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
        ]
        for hkey, reg_path in reg_roots:
            try:
                with winreg.OpenKey(hkey, reg_path) as key:
                    subkeys, _, _ = winreg.QueryInfoKey(key)
                    for i in range(subkeys):
                        app_name = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, app_name) as subkey:
                                target_val, _ = winreg.QueryValueEx(subkey, "")
                                if not target_val:
                                    continue
                                target_val = os.path.expandvars(target_val.strip('"'))
                                target_norm = os.path.normpath(target_val)
                                if target_norm.lower() in seen_targets:
                                    continue
                                if not os.path.exists(target_norm):
                                    continue

                                seen_targets.add(target_norm.lower())
                                display_name = app_name[:-4] if app_name.lower().endswith(".exe") else app_name
                                mtime = int(os.path.getmtime(target_norm))
                                
                                item = normalize_item(
                                    target_path=target_norm,
                                    display_name=display_name,
                                    last_used_at=mtime,
                                    use_count=1,
                                    source=self.name
                                )
                                item.item_type = "app"
                                items.append(item)
                        except Exception:
                            continue
            except Exception:
                pass

        # 3. 扫描系统已安装软件注册表 (Uninstall 表覆盖用户自定义在各盘根目录的软件，如 E:\LeiGod_Acc)
        reg_uninstalls = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hkey, reg_path in reg_uninstalls:
            try:
                with winreg.OpenKey(hkey, reg_path) as key:
                    subkeys, _, _ = winreg.QueryInfoKey(key)
                    for i in range(subkeys):
                        sub_name = winreg.EnumKey(key, i)
                        try:
                            with winreg.OpenKey(key, sub_name) as subkey:
                                loc = ""
                                icon_val = ""
                                dname = ""
                                try:
                                    dname, _ = winreg.QueryValueEx(subkey, "DisplayName")
                                except Exception:
                                    pass
                                try:
                                    loc, _ = winreg.QueryValueEx(subkey, "InstallLocation")
                                except Exception:
                                    pass
                                try:
                                    icon_val, _ = winreg.QueryValueEx(subkey, "DisplayIcon")
                                except Exception:
                                    pass

                                if icon_val:
                                    raw_icon = icon_val.split(",")[0].strip('"')
                                    if raw_icon.lower().endswith(".exe") and os.path.exists(raw_icon):
                                        icon_norm = os.path.normpath(raw_icon)
                                        if icon_norm.lower() not in seen_targets:
                                            seen_targets.add(icon_norm.lower())
                                            mtime = int(os.path.getmtime(icon_norm))
                                            item = normalize_item(
                                                target_path=icon_norm,
                                                display_name=dname or os.path.basename(icon_norm)[:-4],
                                                last_used_at=mtime,
                                                use_count=1,
                                                source=self.name
                                            )
                                            item.item_type = "app"
                                            items.append(item)

                                if loc and os.path.isdir(loc):
                                    for f in os.listdir(loc):
                                        if f.lower().endswith(".exe") and "uninstall" not in f.lower():
                                            full_f = os.path.normpath(os.path.join(loc, f))
                                            if full_f.lower() not in seen_targets and os.path.exists(full_f):
                                                seen_targets.add(full_f.lower())
                                                mtime = int(os.path.getmtime(full_f))
                                                item = normalize_item(
                                                    target_path=full_f,
                                                    display_name=f[:-4],
                                                    last_used_at=mtime,
                                                    use_count=1,
                                                    source=self.name
                                                )
                                                item.item_type = "app"
                                                items.append(item)
                        except Exception:
                            continue
            except Exception:
                pass

        return items

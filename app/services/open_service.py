"""
RecentHub 打开服务
封装 Win32 ShellExecute、打开所在文件夹、复制路径及管理员运行
"""

import os
import subprocess
from typing import Optional
from app.core.models import RecentItem


class OpenService:
    @staticmethod
    def open_item(item: RecentItem) -> bool:
        """执行默认打开"""
        path = item.target_path
        if not path:
            return False
        
        try:
            if item.item_type == 'url' or path.lower().startswith(('http://', 'https://')):
                os.startfile(path)
                return True
            
            if os.path.exists(path):
                if item.arguments:
                    import win32api
                    win32api.ShellExecute(0, "open", path, item.arguments, "", 1)
                else:
                    os.startfile(path)
                return True
            else:
                return False
        except Exception:
            return False

    @staticmethod
    def open_containing_folder(item: RecentItem) -> bool:
        """在文件资源管理器中打开并高亮选中该文件"""
        path = item.target_path
        if not path:
            return False
        try:
            if os.path.exists(path):
                subprocess.Popen(['explorer.exe', f'/select,{path}'])
                return True
            else:
                # 若文件不存在，尝试打开其上级目录
                parent = os.path.dirname(path)
                if os.path.exists(parent):
                    os.startfile(parent)
                    return True
        except Exception:
            pass
        return False

    @staticmethod
    def run_as_admin(item: RecentItem) -> bool:
        """以管理员身份启动程序"""
        path = item.target_path
        if not path or not os.path.exists(path):
            return False
        try:
            import win32api
            win32api.ShellExecute(0, "runas", path, item.arguments or "", "", 1)
            return True
        except Exception:
            return False

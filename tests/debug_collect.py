
import os
from app.collectors.app_collector import AppCollector

col = AppCollector()
# 手动逐步调试
scan_dirs = [
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%USERPROFILE%\Desktop"),
    r"C:\Users\Public\Desktop"
]
for d in scan_dirs:
    print("Checking dir:", d, "exists:", os.path.exists(d))

items = col.collect()
print("items:", len(items))


import os
import subprocess
import winreg

# 1. 检查是否有 everything.exe 或 es.exe
res = subprocess.run(["where.exe", "es.exe"], capture_output=True, text=True)
print("where es.exe:", res.stdout.strip(), res.stderr.strip())

res2 = subprocess.run(["where.exe", "Everything.exe"], capture_output=True, text=True)
print("where Everything.exe:", res2.stdout.strip(), res2.stderr.strip())

# 2. 检查常见安装路径
paths = [
    r"C:\Program Files\Everything\es.exe",
    r"C:\Program Files (x86)\Everything\es.exe",
    r"C:\Program Files\Everything\Everything.exe",
    r"C:\Tools\Everything\es.exe",
    r"D:\Everything\es.exe",
    r"E:\Everything\es.exe"
]
for p in paths:
    if os.path.exists(p):
        print("Found:", p)

# 3. 检查进程中是否有 Everything
import win32com.client
wmi = win32com.client.GetObject('winmgmts:')
for p in wmi.InstancesOf('win32_process'):
    if 'everything' in p.Name.lower():
        print(f"Running process: {p.Name} (pid: {p.ProcessId}) at {p.ExecutablePath}")

# 4. 检查开始菜单有哪些应用
start_menu_common = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs"
start_menu_user = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
print("start_menu_common exists:", os.path.exists(start_menu_common))
print("start_menu_user exists:", os.path.exists(start_menu_user))

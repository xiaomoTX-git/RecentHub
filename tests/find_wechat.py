
import os
import winreg

# 1. 检查注册表 WeChat 安装路径
keys = [
    (winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tencent\WeChat"),
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Tencent\WeChat")
]
for root, k in keys:
    try:
        with winreg.OpenKey(root, k) as key:
            val, _ = winreg.QueryValueEx(key, "InstallPath")
            print("Registry WeChat InstallPath:", val)
            exe = os.path.join(val, "WeChat.exe")
            print("  exe exists:", os.path.exists(exe), exe)
    except Exception as e:
        pass

# 2. 检查微信快捷方式为什么指向 E:WeChatWeChat.exe
path = r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs\微信\微信.lnk"
if os.path.exists(path):
    from app.parsers.lnk_parser import LnkParser
    info = LnkParser.parse_file(path)
    print("Start Menu Wechat target:", info.target_path)
    print("  exists:", os.path.exists(info.target_path))

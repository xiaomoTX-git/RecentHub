
import os
import glob

dirs = [
    r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
    os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
    os.path.expandvars(r"%USERPROFILE%\Desktop"),
    r"C:\Users\Public\Desktop"
]

found = []
for d in dirs:
    if os.path.exists(d):
        for root, _, files in os.walk(d):
            for f in files:
                if f.lower().endswith(".lnk"):
                    full = os.path.join(root, f)
                    if "微信" in f or "wechat" in f.lower() or "hosts" in f.lower():
                        print("MATCH:", full)
                    found.append((f, full))

print(f"Total lnks found in Start Menu & Desktop: {len(found)}")
for name, p in found[:20]:
    print(" -", name)

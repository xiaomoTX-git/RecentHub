
import winreg

def read_app_paths(root, path):
    apps = []
    try:
        with winreg.OpenKey(root, path) as key:
            subkeys, _, _ = winreg.QueryInfoKey(key)
            for i in range(subkeys):
                name = winreg.EnumKey(key, i)
                try:
                    with winreg.OpenKey(key, name) as subkey:
                        val, _ = winreg.QueryValueEx(subkey, "")
                        apps.append((name, val))
                except Exception:
                    pass
    except Exception:
        pass
    return apps

hklm = read_app_paths(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
hkcu = read_app_paths(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths")
print(f"HKLM App Paths: {len(hklm)}")
for n, p in hklm[:10]:
    print(" ", n, "->", p)
print(f"HKCU App Paths: {len(hkcu)}")
for n, p in hkcu[:10]:
    print(" ", n, "->", p)

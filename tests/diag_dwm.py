
import sys
import os
sys.path.insert(0, r"E:AI workBenchRecentHub")
import ctypes
from PySide6.QtWidgets import QApplication
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.ui.effects import apply_light_acrylic

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
scan_service = ScanService(db)
window = MainWindow(db, scan_service)
window.show()

hwnd = int(window.winId())
user32 = ctypes.windll.user32
dwmapi = ctypes.windll.dwmapi

GWL_STYLE = -16
GWL_EXSTYLE = -20
style = user32.GetWindowLongW(hwnd, GWL_STYLE)
exstyle = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
WS_EX_LAYERED = 0x00080000

print(f"HWND: {hwnd}")
print(f"Style: 0x{style:08X}")
print(f"ExStyle: 0x{exstyle:08X}")
print(f"Has WS_EX_LAYERED: {bool(exstyle & WS_EX_LAYERED)}")

# 测试 DwmSetWindowAttribute 返回码
backdrop_val = ctypes.c_int(3) # BACKDROP_ACRYLIC
res = dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(backdrop_val), 4)
print(f"DwmSetWindowAttribute(38, 3) HRESULT: 0x{res & 0xFFFFFFFF:08X}")

# 测试 DwmExtendFrameIntoClientArea
class MARGINS(ctypes.Structure):
    _fields_ = [("cxLeftWidth", ctypes.c_int), ("cxRightWidth", ctypes.c_int),
                ("cyTopHeight", ctypes.c_int), ("cyBottomHeight", ctypes.c_int)]
m = MARGINS(-1, -1, -1, -1)
res_m = dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(m))
print(f"DwmExtendFrameIntoClientArea HRESULT: 0x{res_m & 0xFFFFFFFF:08X}")

window.close()


import sys
import os
import time
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from PySide6.QtWidgets import QApplication
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)
app.setStyle("Fusion")

db = StorageDB(":memory:")
scan_service = ScanService(db)
scan_service.scan_all()

window = MainWindow(db, scan_service)
window.show()

# 1. 截取 Mode A 搜索微信 (50% 纯白毛玻璃质感)
window.search_edit.setText("微信")
window._on_search_debounced()
t_end = time.time() + 0.25
while time.time() < t_end:
    app.processEvents()
    time.sleep(0.005)

pix_a = window.grab()
pix_a.save("RecentHub/screenshot_glass_50_wechat.png")
print("Saved screenshot_glass_50_wechat.png")

# 2. 截取 Mode B 工作台 (50% 纯白毛玻璃质感)
window.toggle_mode()
t_end = time.time() + 0.25
while time.time() < t_end:
    app.processEvents()
    time.sleep(0.005)

pix_b = window.grab()
pix_b.save("RecentHub/screenshot_glass_50_workbench.png")
print("Saved screenshot_glass_50_workbench.png")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()
if window.active_search_worker and window.active_search_worker.isRunning():
    window.active_search_worker.wait()

window.close()

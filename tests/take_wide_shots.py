
import sys
import os
import time
sys.path.insert(0, r"E:AI workBenchRecentHub")
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

# 1. Mode A 搜索微信
window.search_edit.setText("微信")
window._on_search_debounced()
t_end = time.time() + 0.25
while time.time() < t_end:
    app.processEvents()
    time.sleep(0.005)

print(f"Mode A dimensions: {window.width()} x {window.height()}")
assert window.width() == 780, f"Width must be 780, got {window.width()}"
pix_a = window.grab()
pix_a.save("RecentHub/screenshot_wide_wechat.png")
print("Saved screenshot_wide_wechat.png")

# 2. Mode B 详细工作台
window.toggle_mode()
t_end = time.time() + 0.25
while time.time() < t_end:
    app.processEvents()
    time.sleep(0.005)

print(f"Mode B dimensions: {window.width()} x {window.height()}")
assert window.width() == 780, f"Width must be 780, got {window.width()}"
assert window.height() == 450, f"Height must be 450, got {window.height()}"
pix_b = window.grab()
pix_b.save("RecentHub/screenshot_wide_workbench.png")
print("Saved screenshot_wide_workbench.png")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()
if window.active_search_worker and window.active_search_worker.isRunning():
    window.active_search_worker.wait()

window.close()

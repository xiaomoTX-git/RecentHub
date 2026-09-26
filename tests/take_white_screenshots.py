
import sys
import os
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
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

# 1. 抓取 Mode A 初始极简状态 (只有白色单搜索框)
app.processEvents()
pix_empty = window.grab()
pix_empty.save("RecentHub/screenshot_white_mode_a_empty.png")
print("Saved screenshot_white_mode_a_empty.png")

# 2. 抓取 Mode A 键入搜索展开状态
window.search_edit.setText("Trae")
window._on_search_debounced()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_search = window.grab()
pix_search.save("RecentHub/screenshot_white_mode_a_search.png")
print("Saved screenshot_white_mode_a_search.png")

# 3. 抓取 Mode B 白色线条工作台状态
window.toggle_mode()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_workbench = window.grab()
pix_workbench.save("RecentHub/screenshot_white_mode_b.png")
print("Saved screenshot_white_mode_b.png")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()

window.close()

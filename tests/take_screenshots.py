
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

# 1. 抓取 Mode A 初始极简状态 (只有单搜索框)
app.processEvents()
pix_empty = window.grab()
pix_empty.save("RecentHub/screenshot_mode_a_empty.png")
print("Saved screenshot_mode_a_empty.png")

# 2. 抓取 Mode A 输入状态 (调用 debounced 并展开)
window.search_edit.setText("Trae")
window._on_search_debounced()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_search = window.grab()
pix_search.save("RecentHub/screenshot_mode_a_search.png")
print("Saved screenshot_mode_a_search.png")

# 3. 抓取 Mode B 详细工作台状态 (带 macOS 风格分段控制栏)
window.toggle_mode()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_workbench = window.grab()
pix_workbench.save("RecentHub/screenshot_mode_b.png")
print("Saved screenshot_mode_b.png")

window.close()

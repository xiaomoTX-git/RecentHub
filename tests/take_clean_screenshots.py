
import sys
import os
import time
from PySide6.QtWidgets import QApplication
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.ui.tray import TrayService

app = QApplication.instance() or QApplication(sys.argv)
app.setStyle("Fusion")

db = StorageDB(":memory:")
scan_service = ScanService(db)
scan_service.scan_all()

window = MainWindow(db, scan_service)
window.show()

# 1. 抓取无任何外围灰边的 720x48 极简单行搜索条
app.processEvents()
pix_empty = window.grab()
pix_empty.save("RecentHub/screenshot_clean_mode_a_empty.png")
print("Saved screenshot_clean_mode_a_empty.png")

# 2. 抓取键入搜索展开状态 (严格保持 720px 宽度)
window.search_edit.setText("Trae")
window._on_search_debounced()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_search = window.grab()
pix_search.save("RecentHub/screenshot_clean_mode_a_search.png")
print("Saved screenshot_clean_mode_a_search.png")

# 3. 抓取 Mode B 工作台 (严格保持 720px 宽度)
window.toggle_mode()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_workbench = window.grab()
pix_workbench.save("RecentHub/screenshot_clean_mode_b.png")
print("Saved screenshot_clean_mode_b.png")

# 4. 抓取极简纯净右键菜单
tray_service = TrayService(window, db, scan_service)
tray_menu = tray_service.tray_icon.contextMenu()
tray_menu.show()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_menu = tray_menu.grab()
pix_menu.save("RecentHub/screenshot_clean_tray_menu.png")
print("Saved screenshot_clean_tray_menu.png")
tray_menu.hide()

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()

window.close()

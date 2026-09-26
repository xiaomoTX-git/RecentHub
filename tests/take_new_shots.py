
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

# 1. 截取 Mode B 工作台 (无打开次数、无左下角统计、带Word/Excel/PDF)
window.toggle_mode()
app.processEvents()
time.sleep(0.05)
app.processEvents()

pix_b = window.grab()
pix_b.save("RecentHub/screenshot_mode_b_perfect.png")
print("Saved screenshot_mode_b_perfect.png")

# 2. 截取 Word 过滤模式
window.filter_buttons["word"].click()
app.processEvents()
time.sleep(0.05)
app.processEvents()

pix_word = window.grab()
pix_word.save("RecentHub/screenshot_mode_b_word.png")
print("Saved screenshot_mode_b_word.png")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()
if window.active_search_worker and window.active_search_worker.isRunning():
    window.active_search_worker.wait()

window.close()

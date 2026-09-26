
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

# 搜索微信
window.search_edit.setText("微信")
window._on_search_debounced()
t_end = time.time() + 0.25
while time.time() < t_end:
    app.processEvents()
    time.sleep(0.005)

pix = window.grab()
pix.save("RecentHub/screenshot_pure_no_arrows.png")
print("Saved screenshot_pure_no_arrows.png")

window.close()

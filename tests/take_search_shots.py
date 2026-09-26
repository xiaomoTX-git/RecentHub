
import sys
import time
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

# 1. 抓取搜索 "微信"
window.search_edit.setText("微信")
window._on_search_debounced()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_wechat = window.grab()
pix_wechat.save("RecentHub/screenshot_search_wechat.png")
print("Saved screenshot_search_wechat.png")

# 2. 抓取搜索 "hosts"
window.search_edit.setText("hosts")
window._on_search_debounced()
app.processEvents()
time.sleep(0.05)
app.processEvents()
pix_hosts = window.grab()
pix_hosts.save("RecentHub/screenshot_search_hosts.png")
print("Saved screenshot_search_hosts.png")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()

window.close()

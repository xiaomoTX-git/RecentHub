
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

# 切换到 Mode B 工作台
window.toggle_mode()
app.processEvents()
time.sleep(0.05)
app.processEvents()

pix = window.grab()
pix.save("RecentHub/screenshot_mode_b_no_scrollbar.png")
print("Saved screenshot_mode_b_no_scrollbar.png")

# 切换回 Mode A 查看右上角图标
window.toggle_mode()
app.processEvents()
time.sleep(0.05)
app.processEvents()

pix_a = window.grab()
pix_a.save("RecentHub/screenshot_mode_a_icon_btn.png")
print("Saved screenshot_mode_a_icon_btn.png")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()

window.close()


import sys
import time
from PySide6.QtWidgets import QApplication
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
scan_service = ScanService(db)
scan_service.scan_all()

window = MainWindow(db, scan_service)
window.show()

# 单独测量各阶段
t0 = time.perf_counter()
window.search_edit.setText("w")
t1 = time.perf_counter()
print(f"setText took: {(t1 - t0)*1000:.2f} ms")

t2 = time.perf_counter()
window.reload_data()
t3 = time.perf_counter()
print(f"reload_data took: {(t3 - t2)*1000:.2f} ms")

t4 = time.perf_counter()
window._apply_mode_ui(recenter=False)
t5 = time.perf_counter()
print(f"_apply_mode_ui took: {(t5 - t4)*1000:.2f} ms")

t6 = time.perf_counter()
app.processEvents()
t7 = time.perf_counter()
print(f"app.processEvents took: {(t7 - t6)*1000:.2f} ms")

if hasattr(window, 'worker') and window.worker.isRunning():
    window.worker.wait()
if window.active_search_worker and window.active_search_worker.isRunning():
    window.active_search_worker.wait()
window.close()

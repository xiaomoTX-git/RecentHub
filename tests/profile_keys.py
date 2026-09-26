
import sys, time
base = "E:/AI workBench/RecentHub"
sys.path.insert(0, base)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.core.models import RecentItem

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
scan = ScanService(db)

items = [
    RecentItem(target_path=f"C:/App/app_{i}.exe", display_name=f"Application {i}", item_type="app", last_used_at=1000 - i)
    for i in range(50)
]
db.upsert_items(items)

window = MainWindow(db, scan, auto_scan=False)
window.apply_theme("dark")
window.toggle_mode()
window.reload_data()
window.show()
app.processEvents()

times = []
for i in range(100):
    t0 = time.perf_counter()
    ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    app.sendEvent(window.search_edit, ev)
    app.processEvents()
    t1 = time.perf_counter()
    times.append((t1 - t0) * 1000.0)

print(f"Total 100 key presses: sum={sum(times):.2f}ms, avg={sum(times)/len(times):.2f}ms, max={max(times):.2f}ms, min={min(times):.2f}ms")
print("First 10 times (ms):", [round(t, 2) for t in times[:10]])
window.close()

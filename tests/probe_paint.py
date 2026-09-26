
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
from app.ui.delegates import ModernRowDelegate

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
items = [RecentItem(target_path=f"C:/app_{i}.exe", display_name=f"App {i}", item_type="app", last_used_at=1000 - i) for i in range(100)]
db.upsert_items(items)

w = MainWindow(db, ScanService(db), auto_scan=False)
w.apply_theme("dark")
w.toggle_mode()
w.reload_data()
w.show()
app.processEvents()

paint_pill_times = []
paint_super_times = []

orig_paint = w.row_delegate.paint
def detailed_paint(painter, option, index):
    t0 = time.perf_counter()
    # 我们看一下 pill 绘制和 super 绘制各占多少
    orig_paint(painter, option, index)
    t1 = time.perf_counter()
    paint_pill_times.append((t1 - t0) * 1000)

w.row_delegate.paint = detailed_paint

for i in range(20):
    w.select_next_row()
    app.processEvents()

print(f"Total paint calls: {len(paint_pill_times)}")
print(f"Avg time per cell paint: {sum(paint_pill_times)/len(paint_pill_times):.4f}ms")
print(f"Max time per cell paint: {max(paint_pill_times):.4f}ms")

w.close()

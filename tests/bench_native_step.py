
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
items = [RecentItem(target_path=f"C:/app_{i}.exe", display_name=f"App {i}", item_type="app", last_used_at=1000 - i) for i in range(100)]
db.upsert_items(items)

w = MainWindow(db, ScanService(db), auto_scan=False)
w.apply_theme("dark")
w.toggle_mode()
w.reload_data()
w.show()
app.processEvents()

# 测量纯粹原生的单步耗时
times = []
for i in range(50):
    t0 = time.perf_counter()
    w.select_next_row()
    app.processEvents() # 强制执行 Qt 绘制
    t1 = time.perf_counter()
    times.append((t1 - t0) * 1000)

avg_time = sum(times) / len(times)
max_time = max(times)
min_time = min(times)
print(f"Native Step Benchmark (50 steps): avg={avg_time:.3f}ms, min={min_time:.3f}ms, max={max_time:.3f}ms")
w.close()

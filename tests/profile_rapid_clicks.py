
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
items = [RecentItem(target_path=f"C:/app_{i}.exe", display_name=f"Application Name Long Item {i}", item_type="app", last_used_at=1000 - i) for i in range(150)]
db.upsert_items(items)

w = MainWindow(db, ScanService(db), auto_scan=False)
w.apply_theme("dark")
w.toggle_mode()
w.reload_data()
w.show()
app.processEvents()

# 详细记录快速点击时的每一段耗时
stats = {
    "key_press_total": [],
    "navigate_internal": [],
    "scroll_to": [],
    "paint_event": []
}

# 劫持 _navigate_to_row 进行微观耗时追踪
orig_navigate = w._navigate_to_row
def tracked_navigate(target_row, old_row):
    t0 = time.perf_counter()
    orig_navigate(target_row, old_row)
    t1 = time.perf_counter()
    stats["navigate_internal"].append((t1 - t0) * 1000)

w._navigate_to_row = tracked_navigate

print("Starting 50 rapid keypresses...")
for i in range(50):
    t_start = time.perf_counter()
    ev = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    app.sendEvent(w.search_edit, ev)
    t_key_done = time.perf_counter()
    app.processEvents() # 触发真正的 Qt 绘图和消息处理
    t_paint_done = time.perf_counter()
    
    stats["key_press_total"].append((t_key_done - t_start) * 1000)
    stats["paint_event"].append((t_paint_done - t_key_done) * 1000)

def print_stat(name, data):
    avg = sum(data) / len(data)
    mx = max(data)
    p95 = sorted(data)[int(len(data)*0.95)]
    print(f"{name:20s}: avg={avg:6.2f}ms, max={mx:6.2f}ms, p95={p95:6.2f}ms")

print_stat("Key Event Logic", stats["key_press_total"])
print_stat("Navigate Logic", stats["navigate_internal"])
print_stat("Qt Paint/Flush", stats["paint_event"])

w.close()

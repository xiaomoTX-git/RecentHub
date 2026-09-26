
import sys, time
base = "E:/AI workBench/RecentHub"
sys.path.insert(0, base)

from PySide6.QtWidgets import QApplication
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

# 拆解单步耗时
timings = {"delegate_set": 0, "sm": 0, "scroll": 0, "update": 0, "process_events": 0}

for _ in range(30):
    t0 = time.perf_counter()
    target_row = (window.get_selected_row() + 1) % 50
    old_row = window.get_selected_row()
    window._current_selected_row = target_row
    
    t1 = time.perf_counter()
    window.row_delegate.set_selected_row(target_row)
    t2 = time.perf_counter()
    
    idx = window.table_model.index(target_row, 0)
    sm = window.table_view.selectionModel()
    if sm:
        sm.setCurrentIndex(idx, sm.SelectionFlag.ClearAndSelect | sm.SelectionFlag.Rows)
    t3 = time.perf_counter()
    
    vp = window.table_view.viewport()
    v_rect = vp.rect()
    t_rect = window.table_view.visualRect(idx)
    if t_rect.top() < v_rect.top() or t_rect.bottom() > v_rect.bottom():
        window.table_view.scrollTo(idx, window.table_view.ScrollHint.EnsureVisible)
    t4 = time.perf_counter()
    
    if old_row >= 0 and old_row != target_row:
        old_idx = window.table_model.index(old_row, 0)
        r_old = window.table_view.visualRect(old_idx)
        r_new = window.table_view.visualRect(idx)
        vp.update(r_old)
        vp.update(r_new)
    t5 = time.perf_counter()
    
    app.processEvents()
    t6 = time.perf_counter()
    
    timings["delegate_set"] += (t2 - t1) * 1000
    timings["sm"] += (t3 - t2) * 1000
    timings["scroll"] += (t4 - t3) * 1000
    timings["update"] += (t5 - t4) * 1000
    timings["process_events"] += (t6 - t5) * 1000

for k, v in timings.items():
    print(f"{k}: total {v:.2f}ms, avg {v/30:.3f}ms")

window.close()

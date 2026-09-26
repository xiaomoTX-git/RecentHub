
import sys
import time
from PySide6.QtWidgets import QApplication
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.ui.effects import apply_light_acrylic

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
scan_service = ScanService(db)
scan_service.scan_all()

window = MainWindow(db, scan_service)
window.show()
app.processEvents()

# 1. 单独测量 apply_light_acrylic
t0 = time.perf_counter()
for _ in range(5):
    apply_light_acrylic(window)
t1 = time.perf_counter()
print(f"apply_light_acrylic avg: {((t1-t0)/5)*1000:.2f} ms")

# 2. 测量没有 apply_light_acrylic 时的 resize
t2 = time.perf_counter()
window.setFixedSize(720, 200)
app.processEvents()
t3 = time.perf_counter()
print(f"setFixedSize + processEvents: {(t3-t2)*1000:.2f} ms")

# 3. 测量表格数据重置并绘制的时间
items = db.query_items("w")
t4 = time.perf_counter()
window.table_model.set_items(items[:8])
app.processEvents()
t5 = time.perf_counter()
print(f"set_items(8) + paint render: {(t5-t4)*1000:.2f} ms")

window.close()

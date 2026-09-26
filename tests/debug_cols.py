import sys
base = "E:/AI workBench/RecentHub"
sys.path.insert(0, base)
from PySide6.QtWidgets import QApplication
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.core.models import RecentItem

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
items = [RecentItem(target_path="E:/test.exe", display_name="TestApp", item_type="app", last_used_at=1000)]
db.upsert_items(items)
window = MainWindow(db, ScanService(db), auto_scan=False)
window.toggle_mode()
window.reload_data()

print("Model columnCount:", window.table_model.columnCount())
for c in range(window.table_model.columnCount()):
    idx = window.table_model.index(0, c)
    print(f"Col {c} index.column():", idx.column())
window.close()

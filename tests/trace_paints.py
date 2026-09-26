
import sys, time
base = "E:/AI workBench/RecentHub"
sys.path.insert(0, base)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent
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

paints = []
class PaintSpy(window.table_view.viewport().__class__):
    pass

orig_table_paint = window.table_view.viewport().paintEvent
def spy_paint(event):
    paints.append(("viewport", event.rect()))
    orig_table_paint(event)

window.table_view.viewport().paintEvent = spy_paint

card_paints = []
orig_card_paint = window.central_card.paintEvent
def spy_card_paint(event):
    card_paints.append(("card", event.rect()))
    orig_card_paint(event)

window.central_card.paintEvent = spy_card_paint

for _ in range(5):
    window.select_next_row()
    app.processEvents()

print("Viewport paints:", paints)
print("Card paints:", card_paints)

window.close()

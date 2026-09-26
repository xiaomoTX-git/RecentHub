
import sys
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
items = [RecentItem(target_path=f"C:/app_{i}.exe", display_name=f"App {i}", item_type="app", last_used_at=1000 - i) for i in range(10)]
db.upsert_items(items)

w = MainWindow(db, ScanService(db), auto_scan=False)
w.show()
w.activateWindow()
app.processEvents()

print("Focus widget after show/activate:", QApplication.focusWidget())
print("Table rowCount:", w.table_model.rowCount())
print("Current mode:", w.current_mode)
print("Table isVisible:", w.table_view.isVisible())
print("Current selected_row:", w.get_selected_row())

# 发送物理按键 Down
print("--- Sending KeyDown without auto-repeat ---")
ev_down = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
target = QApplication.focusWidget() or w
handled = app.sendEvent(target, ev_down)
print("Event target:", target)
print("Handled by target:", handled)
print("Selected row after Down:", w.get_selected_row())

# 发送物理松手 KeyRelease
print("--- Sending KeyRelease ---")
ev_rel = QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
handled_rel = app.sendEvent(target, ev_rel)
print("Release handled:", handled_rel)
print("Selected row after Release:", w.get_selected_row())

w.close()

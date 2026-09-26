
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
w.apply_theme("dark")
w.toggle_mode()
w.reload_data()
w.show()
app.processEvents()

print("Initial selected_row in MainWindow:", w.get_selected_row())
print("Initial selected_row in Delegate:", w.row_delegate.selected_row)

# 模拟发送单次向下按键
ev_down = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
handled = app.sendEvent(w.search_edit, ev_down)
print("Was KeyDown handled by eventFilter?", handled)
print("selected_row in MainWindow after Down:", w.get_selected_row())
print("selected_row in Delegate after Down:", w.row_delegate.selected_row)

# 模拟松手
ev_up = QKeyEvent(QEvent.Type.KeyRelease, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
app.sendEvent(w.search_edit, ev_up)

# 再次按下 Down
handled2 = app.sendEvent(w.search_edit, ev_down)
print("Was 2nd KeyDown handled by eventFilter?", handled2)
print("selected_row in MainWindow after 2nd Down:", w.get_selected_row())
print("selected_row in Delegate after 2nd Down:", w.row_delegate.selected_row)

w.close()

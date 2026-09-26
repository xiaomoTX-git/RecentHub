
import sys, time
base = "E:/AI workBench/RecentHub"
sys.path.insert(0, base)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QMouseEvent, QKeyEvent
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.core.models import RecentItem

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
items = [RecentItem(target_path=f"C:/app_{i}.exe", display_name=f"App {i}", item_type="app", last_used_at=1000 - i) for i in range(20)]
db.upsert_items(items)

w = MainWindow(db, ScanService(db), auto_scan=False)
w.apply_theme("dark")
w.toggle_mode()
w.reload_data()
w.show()
app.processEvents()

print("Initial selected row:", w.get_selected_row())

# 1. 检查 viewport 是否在 draggable_surfaces
vp = w.table_view.viewport()
print("Is viewport in draggable_surfaces?", vp in w.draggable_surfaces)

# 2. 模拟鼠标点击第 4 行
r4 = w.table_view.visualRect(w.table_model.index(4, 0))
pt4 = r4.center()
print("Clicking row 4 at point:", pt4)

# 发送 MouseButtonPress 到 viewport
press4 = QMouseEvent(QEvent.Type.MouseButtonPress, pt4, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
app.sendEvent(vp, press4)
app.processEvents()
print("After press row 4, selected:", w.get_selected_row(), "delegate:", w.row_delegate.selected_row)

# 3. 模拟鼠标点击第 8 行
r8 = w.table_view.visualRect(w.table_model.index(8, 0))
pt8 = r8.center()
press8 = QMouseEvent(QEvent.Type.MouseButtonPress, pt8, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
app.sendEvent(vp, press8)
app.processEvents()
print("After press row 8, selected:", w.get_selected_row(), "delegate:", w.row_delegate.selected_row)

# 4. 模拟键盘上下键
k_down = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
app.sendEvent(w.search_edit, k_down)
app.processEvents()
print("After Key_Down, selected:", w.get_selected_row())

w.close()

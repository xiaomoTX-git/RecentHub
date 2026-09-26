
import sys
base = "E:/AI workBench/RecentHub"
sys.path.insert(0, base)
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPainter, QImage, QPainterPath
from PySide6.QtCore import Qt, QPointF, QLineF, QRectF
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow
from app.core.models import RecentItem

app = QApplication.instance() or QApplication(sys.argv)
db = StorageDB(":memory:")
items = [RecentItem(target_path="E:/test.exe", display_name="TestApp", item_type="app", last_used_at=1000)]
db.upsert_items(items)
window = MainWindow(db, ScanService(db), auto_scan=False)
window.apply_theme("dark")
window.toggle_mode()
window.reload_data()

# 检查当前 QTableView 的 viewport 绘制
# 我们自定义一个跟踪画笔行为的 Painter
class TracePainter(QPainter):
    def drawLine(self, *args):
        print("TRACE drawLine:", args)
        super().drawLine(*args)
    def drawPath(self, path):
        print("TRACE drawPath elementCount:", path.elementCount())
        for i in range(path.elementCount()):
            el = path.elementAt(i)
            print(f"  el {i}: type={el.type}, x={el.x}, y={el.y}")
        super().drawPath(path)
    def fillPath(self, path, brush):
        print("TRACE fillPath elementCount:", path.elementCount())
        super().fillPath(path, brush)

img = QImage(800, 100, QImage.Format.Format_ARGB32)
tp = TracePainter(img)

# 分别对每个 col 调用 delegate.paint
for c in range(4):
    idx = window.table_model.index(0, c)
    opt = window.table_view.viewOptions()
    opt.rect = window.table_view.visualRect(idx)
    print(f"\n=== PAINTING COL {c} (x={opt.rect.x()}, w={opt.rect.width()}) ===")
    window.row_delegate.paint(tp, opt, idx)

tp.end()
window.close()

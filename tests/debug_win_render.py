
import sys
import os
sys.path.insert(0, r"E:AI workBenchRecentHub")
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor
from app.storage.db import StorageDB
from app.services.scan_service import ScanService
from app.ui.main_window import MainWindow

app = QApplication(sys.argv)
db = StorageDB(":memory:")
scan_service = ScanService(db)
window = MainWindow(db, scan_service)
window.show()
app.processEvents()

pix = window.grab()
img = pix.toImage()
c = QColor(img.pixel(window.width() // 2, 20))
print(f"Window grab pixel at (center, 20): RGBA = ({c.red()}, {c.green()}, {c.blue()}, {c.alpha()})")
print("CentralCard objectName:", window.central_card.objectName())
print("StyleSheet length:", len(window.styleSheet()))

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap

class ImageViewData:
    def __init__(self, pixmap: QPixmap, rect: QRectF):
        self.pixmap = pixmap
        self.rect = rect

from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtGui import QTransform, QPixmap

class ImageItem(QGraphicsPixmapItem):
    def __init__(self, image_data, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.setPos(image_data.rect.topLeft())
        self.loaded = False

    def load_pixmap(self, pixmap: QPixmap):
        """
        실제 QPixmap을 받아 아이템에 설정하고 크기를 조절합니다.
        """
        if self.loaded:
            return
        self.setPixmap(pixmap)
        brect = self.boundingRect()
        if brect.width() > 0 and brect.height() > 0:
            sx = self.image_data.rect.width() / brect.width()
            sy = self.image_data.rect.height() / brect.height()
            transform = QTransform().scale(sx, sy)
            self.setTransform(transform)
        self.loaded = True

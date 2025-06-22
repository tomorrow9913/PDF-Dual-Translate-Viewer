from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtGui import QTransform

class ImageItem(QGraphicsPixmapItem):
    def __init__(self, image_data, parent=None):
        super().__init__(image_data.pixmap, parent)
        brect = self.boundingRect()
        if brect.width() > 0 and brect.height() > 0:
            sx = image_data.rect.width() / brect.width()
            sy = image_data.rect.height() / brect.height()
            transform = QTransform().scale(sx, sy)
            self.setTransform(transform)
        self.setPos(image_data.rect.topLeft())

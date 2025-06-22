from PySide6.QtWidgets import QGraphicsRectItem
from PySide6.QtGui import QBrush, QColor

class HighlightOverlay(QGraphicsRectItem):
    def __init__(self, rect, color="#ffffcc", parent=None):
        super().__init__(rect, parent)
        self.setBrush(QBrush(QColor(color)))
        self.setPen(QColor(color))
        self.setZValue(-1)  # 텍스트 아래에 표시
        self.setOpacity(0.5)

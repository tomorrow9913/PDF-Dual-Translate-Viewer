from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor
from typing import Optional

class SegmentViewData:
    def __init__(self, segment_id: str, text: str, rect: tuple, font_family: str, font_size: int, font_color: str,
                 is_bold: bool, is_italic: bool, is_highlighted: bool, link_uri: Optional[str] = None):
        self.segment_id = segment_id
        self.text = text
        self.rect = QRectF(rect[0], rect[1], rect[2], rect[3])
        self.font_family = font_family
        self.font_size = font_size
        self.font_color = QColor(font_color)
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_highlighted = is_highlighted
        self.link_uri = link_uri

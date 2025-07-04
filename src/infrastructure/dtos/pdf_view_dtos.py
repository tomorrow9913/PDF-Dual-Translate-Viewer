from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPixmap


class SegmentViewData:
    def __init__(
        self,
        segment_id: str,
        text: str,
        rect: Tuple[float, float, float, float],
        font_family: str,
        font_size: int,
        font_color: str,
        is_bold: bool,
        is_italic: bool,
        is_highlighted: bool,
        link_uri: Optional[str] = None,
        block_id: Optional[str] = None,
        line_id: Optional[str] = None,
    ):
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
        self.block_id = block_id
        self.line_id = line_id


class HighlightUpdateInfo:
    def __init__(self, segments_to_update: Dict[str, bool]):
        self.segments_to_update = segments_to_update


class ImageViewData:
    def __init__(self, xref: int, rect: QRectF):
        """
        지연 로딩을 위해 pixmap 대신 이미지의 xref를 저장합니다.
        """
        self.xref = xref
        self.rect = rect
        self.pixmap: Optional[QPixmap] = None  # 필요할 때 로드됩니다.


class PageDisplayViewModel:
    def __init__(
        self,
        page_number: int,
        page_width: float,
        page_height: float,
        original_segments_view: List[SegmentViewData],
        translated_segments_view: List[SegmentViewData],
        image_views: List[ImageViewData],
        error_message: Optional[str] = None,
    ):
        self.page_number = page_number
        self.page_width = page_width
        self.page_height = page_height
        self.original_segments_view = original_segments_view
        self.translated_segments_view = translated_segments_view
        self.image_views = image_views
        self.error_message = error_message

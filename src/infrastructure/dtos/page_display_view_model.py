from typing import List, Optional
from .segment_view_data import SegmentViewData
from .image_view_data import ImageViewData

class PageDisplayViewModel:
    def __init__(self, page_number: int, page_width: float, page_height: float,
                 original_segments_view: List[SegmentViewData],
                 translated_segments_view: List[SegmentViewData],
                 image_views: List[ImageViewData], error_message: Optional[str] = None):
        self.page_number = page_number
        self.page_width = page_width
        self.page_height = page_height
        self.original_segments_view = original_segments_view
        self.translated_segments_view = translated_segments_view
        self.image_views = image_views
        self.error_message = error_message

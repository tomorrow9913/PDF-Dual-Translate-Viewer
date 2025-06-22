from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem, QApplication, QMainWindow,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QGraphicsItem, QSizePolicy, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QFont, QColor, QBrush, QPainter, QPixmap, QTransform, QTextCursor, QTextCharFormat

from typing import List, Tuple, Optional, Dict

# --- DTOs (Data Transfer Objects) - 클래스 다이어그램에서 정의된 뷰 모델 활용 ---
class SegmentViewData:
    def __init__(self, segment_id: str, text: str, rect: Tuple[float, float, float, float],
                 font_family: str, font_size: int, font_color: str,
                 is_bold: bool, is_italic: bool, is_highlighted: bool):
        self.segment_id = segment_id
        self.text = text
        self.rect = QRectF(rect[0], rect[1], rect[2], rect[3])
        self.font_family = font_family
        self.font_size = font_size
        self.font_color = QColor(font_color)
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_highlighted = is_highlighted

class HighlightUpdateInfo:
    def __init__(self, segments_to_update: Dict[str, bool]):
        self.segments_to_update = segments_to_update

class ImageViewData:
    def __init__(self, pixmap: QPixmap, rect: QRectF):
        self.pixmap = pixmap
        self.rect = rect

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

class PdfViewWidget(QWidget):
    """
    단일 PDF 페이지를 렌더링하고 텍스트 세그먼트 상호작용을 처리하는 위젯.
    """
    segmentHovered = Signal(str, object)

    def __init__(self, view_context: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view_context = view_context
        self._current_segments_on_display: Dict[str, SegmentViewData] = {}
        self._text_items: Dict[str, QGraphicsTextItem] = {}
        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view = QGraphicsView(self.graphics_scene)
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.setMouseTracking(True)
        self.graphics_view.mouseMoveEvent = self._custom_mouse_move_event
        self.graphics_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.graphics_view)
        self.setLayout(self.layout)
        self.graphics_scene.setBackgroundBrush(QBrush(QColor("#ffffff")))

    def render_page(self, segments: List[SegmentViewData], images: List[ImageViewData], page_width: float, page_height: float):
        """
        주어진 세그먼트와 이미지 목록을 기반으로 페이지 내용을 렌더링합니다.
        페이지의 실제 크기를 기준으로 Scene의 좌표계를 설정합니다.
        """
        self.graphics_scene.clear()
        self._current_segments_on_display.clear()
        self._text_items.clear()

        # 페이지의 실제 크기로 씬의 영역을 설정합니다. 이것이 좌표계의 기준이 됩니다.
        if page_width > 0 and page_height > 0:
            self.graphics_scene.setSceneRect(0, 0, page_width, page_height)

        # 이미지 렌더링 (텍스트보다 먼저 그려서 텍스트 아래에 위치하도록 함)
        for image_data in images:
            if image_data.pixmap.isNull():
                continue
            pixmap_item = QGraphicsPixmapItem(image_data.pixmap)
            pixmap_item.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
            
            brect = pixmap_item.boundingRect()
            if brect.width() > 0 and brect.height() > 0:
                sx = image_data.rect.width() / brect.width()
                sy = image_data.rect.height() / brect.height()
                transform = QTransform().scale(sx, sy)
                pixmap_item.setTransform(transform)
            
            pixmap_item.setPos(image_data.rect.topLeft())
            self.graphics_scene.addItem(pixmap_item)

        if not segments:
            self.fit_to_view()
            return
        for segment_data in segments:
            text_item = QGraphicsTextItem(segment_data.text) # 텍스트 아이템 생성

            # 폰트 및 색상 설정
            font = QFont(segment_data.font_family, segment_data.font_size)
            font.setBold(segment_data.is_bold)
            font.setItalic(segment_data.is_italic)
            text_item.setFont(font)
            text_item.setDefaultTextColor(segment_data.font_color)

            # 텍스트 아이템의 자연스러운 크기를 얻음 (자동 줄바꿈 없이)
            natural_rect = text_item.boundingRect()
            target_rect = segment_data.rect

            if natural_rect.width() == 0 or natural_rect.height() == 0:
                continue

            # PDF의 바운딩 박스에 맞게 텍스트 아이템을 스케일링하고 위치시키는 변환(Transform) 생성
            scale_x = target_rect.width() / natural_rect.width()
            scale_y = target_rect.height() / natural_rect.height()

            transform = QTransform()
            transform.translate(target_rect.left(), target_rect.top())
            transform.scale(scale_x, scale_y)
            transform.translate(-natural_rect.left(), -natural_rect.top())
            text_item.setTransform(transform)

            text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
            self.graphics_scene.addItem(text_item)
            
            # 텍스트 아이템에 하이라이트 적용
            self._apply_highlight_format(text_item, segment_data.is_highlighted)

            self._text_items[segment_data.segment_id] = text_item
            self._current_segments_on_display[segment_data.segment_id] = segment_data
        # 씬의 크기가 페이지 크기로 고정되었으므로, 뷰를 여기에 맞춥니다.
        self.fit_to_view() # 모든 아이템이 추가된 후 뷰에 맞춤

    def _apply_highlight_format(self, text_item: QGraphicsTextItem, highlight: bool):
        """텍스트 아이템에 하이라이트 서식을 적용하거나 제거합니다."""
        cursor = QTextCursor(text_item.document())
        cursor.select(QTextCursor.SelectionType.Document)
        char_format = QTextCharFormat()
        if highlight:
            char_format.setBackground(QBrush(QColor("#ffffcc")))
        else:
            char_format.clearBackground()
        cursor.setCharFormat(char_format)

    def update_single_segment_highlight(self, segment_id: str, highlight: bool):
        if segment_id in self._text_items:
            text_item = self._text_items[segment_id]
            self._apply_highlight_format(text_item, highlight)
            if segment_id in self._current_segments_on_display:
                self._current_segments_on_display[segment_id].is_highlighted = highlight

    def get_segment_id_at_pos(self, x: float, y: float) -> Optional[str]:
        point = self.graphics_view.mapToScene(int(x), int(y))
        items = self.graphics_scene.items(point)
        for item in items:
            if isinstance(item, QGraphicsTextItem):
                for segment_id, text_item in self._text_items.items():
                    if text_item == item:
                        return segment_id
        return None

    def _custom_mouse_move_event(self, event):
        segment_id = self.get_segment_id_at_pos(event.pos().x(), event.pos().y())
        self.segmentHovered.emit(self.view_context, segment_id)
        super(QGraphicsView, self.graphics_view).mouseMoveEvent(event)

    def resizeEvent(self, event):
        """
        위젯 크기가 변경될 때 뷰를 업데이트하여 콘텐츠가 뷰에 맞도록 조정합니다.
        """
        super().resizeEvent(event)
        self.fit_to_view()

    def fit_to_view(self):
        """
        현재 scene의 콘텐츠를 view에 맞게 조정합니다.
        """
        if not self.graphics_scene.sceneRect().isEmpty():
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

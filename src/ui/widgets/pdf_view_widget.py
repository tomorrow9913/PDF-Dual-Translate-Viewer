from typing import Dict, List, Optional

import fitz
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QPainter,
    QPixmap,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.infrastructure.dtos.pdf_view_dtos import ImageViewData, SegmentViewData

from .highlight_overlay import HighlightOverlay
from .image_item import ImageItem
from .text_segment_item import TextSegmentItem

# --- DTOs (Data Transfer Objects) - 클래스 다이어그램에서 정의된 뷰 모델 활용 ---
# class SegmentViewData:
#     def __init__(self, segment_id: str, text: str, rect: Tuple[float, float, float, float],
#                  font_family: str, font_size: int, font_color: str,
#                  is_bold: bool, is_italic: bool, is_highlighted: bool,
#                  link_uri: Optional[str] = None):
#         self.segment_id = segment_id
#         self.text = text
#         self.rect = QRectF(rect[0], rect[1], rect[2], rect[3])
#         self.font_family = font_family
#         self.font_size = font_size
#         self.font_color = QColor(font_color)
#         self.is_bold = is_bold
#         self.is_italic = is_italic
#         self.is_highlighted = is_highlighted
#         self.link_uri = link_uri

# class HighlightUpdateInfo:
#     def __init__(self, segments_to_update: Dict[str, bool]):
#         self.segments_to_update = segments_to_update

# class ImageViewData:
#     def __init__(self, pixmap: QPixmap, rect: QRectF):
#         self.pixmap = pixmap
#         self.rect = rect

# class PageDisplayViewModel:
#     def __init__(self, page_number: int, page_width: float, page_height: float,
#                  original_segments_view: List[SegmentViewData],
#                  translated_segments_view: List[SegmentViewData],
#                  image_views: List[ImageViewData], error_message: Optional[str] = None):
#         self.page_number = page_number
#         self.page_width = page_width
#         self.page_height = page_height
#         self.original_segments_view = original_segments_view
#         self.translated_segments_view = translated_segments_view
#         self.image_views = image_views
#         self.error_message = error_message


class PdfViewWidget(QWidget):
    """
    단일 PDF 페이지를 렌더링하고 텍스트 세그먼트 상호작용을 처리하는 위젯.
    """

    segmentHovered = Signal(str, object)
    # 뷰 동기화를 위한 시그널
    zoom_in_requested = Signal()
    zoom_out_requested = Signal()
    linkClicked = Signal(str)  # linkClicked 시그널 추가
    fileDropped = Signal(str)  # PDF 파일 드롭 시그널 추가

    def __init__(self, view_context: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view_context = view_context
        self._current_segments_on_display: Dict[str, SegmentViewData] = {}
        self._text_items: Dict[str, QGraphicsTextItem] = {}
        self._image_items: List[ImageItem] = []
        self._pdf_doc: Optional[fitz.Document] = None
        self.setAcceptDrops(True)  # 드래그&드롭 허용

        # 지연 로딩을 위한 타이머 설정 (디바운싱)
        self._lazy_load_timer = QTimer(self)
        self._lazy_load_timer.setSingleShot(True)
        self._lazy_load_timer.setInterval(100)  # 100ms
        self._lazy_load_timer.timeout.connect(self._load_visible_images)

        self._current_highlight_color = QColor("#ffffcc")  # 기본 하이라이트 색상

        self._init_ui()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_view = QGraphicsView(self.graphics_scene)
        self.graphics_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.graphics_view.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )
        self.graphics_view.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorViewCenter
        )
        self.graphics_view.setDragMode(QGraphicsView.NoDrag)
        self.graphics_view.setMouseTracking(True)
        self.graphics_view.wheelEvent = self._custom_wheel_event
        self.graphics_view.mouseMoveEvent = self._custom_mouse_move_event
        self.graphics_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # 스크롤 이벤트 발생 시 지연 로딩 스케줄링
        self.graphics_view.verticalScrollBar().valueChanged.connect(
            self.schedule_lazy_load
        )
        self.graphics_view.horizontalScrollBar().valueChanged.connect(
            self.schedule_lazy_load
        )
        self.layout.addWidget(self.graphics_view)
        self.setLayout(self.layout)
        self.graphics_scene.setBackgroundBrush(QBrush(QColor("#ffffff")))

    def render_page(
        self,
        segments: List[SegmentViewData],
        images: List[ImageViewData],
        page_width: float,
        page_height: float,
        pdf_doc: Optional[fitz.Document],
    ):
        """
        주어진 세그먼트와 이미지 목록을 기반으로 페이지 내용을 렌더링합니다.
        페이지의 실제 크기를 기준으로 Scene의 좌표계를 설정합니다.
        지연 로딩을 위해 pdf_doc 객체를 받습니다.
        """
        self.graphics_scene.clear()
        self._current_segments_on_display.clear()
        self._text_items.clear()
        self._image_items.clear()
        self._pdf_doc = pdf_doc

        # 페이지의 실제 크기로 씬의 영역을 설정합니다. 이것이 좌표계의 기준이 됩니다.
        if page_width > 0 and page_height > 0:
            self.graphics_scene.setSceneRect(0, 0, page_width, page_height)

        # 이미지 렌더링 (텍스트보다 먼저 그려서 텍스트 아래에 위치하도록 함)
        for image_data in images:
            image_item = ImageItem(image_data)
            self.graphics_scene.addItem(image_item)
            self._image_items.append(image_item)

        if not segments:
            self.fit_to_view()
            self.schedule_lazy_load()  # 텍스트가 없어도 이미지는 로드
            return
        for segment_data in segments:
            # 하이라이트 오버레이 분리 적용
            if segment_data.is_highlighted:
                overlay = HighlightOverlay(segment_data.rect)
                self.graphics_scene.addItem(overlay)
            text_item = TextSegmentItem(segment_data)
            text_item.set_highlight_color(
                self._current_highlight_color
            )  # 하이라이트 색상 적용
            if segment_data.link_uri:
                text_item.linkActivated.connect(self._on_link_activated)
            self.graphics_scene.addItem(text_item)
            self._text_items[segment_data.segment_id] = text_item
            self._current_segments_on_display[segment_data.segment_id] = segment_data
        # 씬의 크기가 페이지 크기로 고정되었으므로, 뷰를 여기에 맞춥니다.
        self.fit_to_view()  # 모든 아이템이 추가된 후 뷰에 맞춤
        self.schedule_lazy_load()  # 초기 렌더링 후 보이는 이미지 로드

    def schedule_lazy_load(self):
        """보이는 이미지 로드를 위한 스케줄을 잡습니다 (디바운싱)."""
        self._lazy_load_timer.start()

    def _load_visible_images(self):
        """현재 뷰포트에 보이는 이미지들의 Pixmap을 로드합니다."""
        if not self._image_items or not self._pdf_doc:
            return

        # 씬 좌표계에서 현재 보이는 영역을 계산합니다.
        visible_rect = self.graphics_view.mapToScene(
            self.graphics_view.viewport().rect()
        ).boundingRect()

        for item in self._image_items:
            # 아이템이 보이고 아직 로드되지 않았다면 로드합니다.
            # item.sceneBoundingRect()는 pixmap이 로드되기 전에는 비어있으므로,
            # item.image_data.rect를 직접 사용하여 교차 검사를 수행합니다.
            if not item.loaded and item.image_data.rect.intersects(visible_rect):
                try:
                    base_image = self._pdf_doc.extract_image(item.image_data.xref)
                    if not base_image:
                        continue
                    image_bytes = base_image["image"]
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_bytes)
                    if not pixmap.isNull():
                        item.load_pixmap(pixmap)
                except Exception as e:
                    # 오류가 발생해도 전체가 멈추지 않도록 처리
                    print(f"Error lazy-loading image xref {item.image_data.xref}: {e}")

    def _apply_highlight_format(
        self, text_item: QGraphicsTextItem, highlight: bool, color: QColor = None
    ):
        """텍스트 아이템에 하이라이트 서식을 적용하거나 제거합니다."""
        if color is None:
            color = getattr(self, "_current_highlight_color", QColor("#ffffcc"))
        cursor = QTextCursor(text_item.document())
        cursor.select(QTextCursor.SelectionType.Document)
        char_format = QTextCharFormat()
        if highlight:
            char_format.setBackground(QBrush(color))
        else:
            char_format.clearBackground()
        cursor.setCharFormat(char_format)

    def update_single_segment_highlight(self, segment_id: str, highlight: bool):
        if segment_id in self._text_items:
            text_item = self._text_items[segment_id]
            self._apply_highlight_format(
                text_item, highlight, self._current_highlight_color
            )
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

    def _on_link_activated(self, link: str):
        self.linkClicked.emit(link)  # linkClicked 시그널 방출

    def _custom_wheel_event(self, event):
        """
        마우스 휠 이벤트를 처리합니다.
        - Ctrl + 휠: 뷰 확대/축소
        - Shift + 휠: 좌우 스크롤
        - 일반 휠: 상하 스크롤
        """
        modifiers = event.modifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            self.graphics_view.setTransformationAnchor(
                QGraphicsView.ViewportAnchor.AnchorUnderMouse
            )
            if event.angleDelta().y() > 0:
                self.graphics_view.scale(1.1, 1.1)
                self.zoom_in_requested.emit()
            else:
                self.graphics_view.scale(1 / 1.1, 1 / 1.1)
                self.zoom_out_requested.emit()
            self.graphics_view.setTransformationAnchor(
                QGraphicsView.ViewportAnchor.AnchorViewCenter
            )
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ShiftModifier:
            h_scroll = self.graphics_view.horizontalScrollBar()
            # 휠 한 번에 3 스텝씩 이동하도록 설정
            steps_to_scroll = h_scroll.singleStep() * 3
            if event.angleDelta().y() < 0:  # 아래로 스크롤 -> 오른쪽으로 이동
                h_scroll.setValue(h_scroll.value() + steps_to_scroll)
            else:  # 위로 스크롤 -> 왼쪽으로 이동
                h_scroll.setValue(h_scroll.value() - steps_to_scroll)
            event.accept()
        else:
            super(QGraphicsView, self.graphics_view).wheelEvent(event)

    def fit_to_view(self):
        """
        현재 scene의 콘텐츠를 view에 맞게 조정합니다.
        """
        if not self.graphics_scene.sceneRect().isEmpty():
            self.graphics_view.fitInView(
                self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio
            )

    def resizeEvent(self, event):
        """위젯 크기가 변경될 때 지연 로딩을 스케줄링합니다."""
        super().resizeEvent(event)
        self.schedule_lazy_load()

    def zoom_in(self):
        """뷰를 10% 확대합니다."""
        self.graphics_view.scale(1.1, 1.1)

    def zoom_out(self):
        """뷰를 10% 축소합니다."""
        self.graphics_view.scale(1 / 1.1, 1 / 1.1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".pdf"):
                self.fileDropped.emit(file_path)
                break
        event.acceptProposedAction()

    def set_font(self, font: QFont):
        """
        외부에서 전달된 QFont를 현재 표시 중인 모든 텍스트 세그먼트에 적용합니다.
        """
        for text_item in self._text_items.values():
            text_item.setFont(font)

    def set_highlight_color(self, color: QColor):
        self._current_highlight_color = color
        for text_item in self._text_items.values():
            text_item.set_highlight_color(color)

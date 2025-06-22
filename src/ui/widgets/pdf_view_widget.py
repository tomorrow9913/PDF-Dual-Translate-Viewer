from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene,
    QGraphicsRectItem, QGraphicsTextItem, QApplication, QMainWindow,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QGraphicsItem, QSizePolicy, QGraphicsPixmapItem
)
from PySide6.QtCore import Qt, QRectF, Signal, QPointF
from PySide6.QtGui import QFont, QColor, QBrush, QPainter, QPixmap, QTransform, QTextCursor, QTextCharFormat
import html # html 모듈 추가

from typing import List, Tuple, Optional, Dict
from src.infrastructure.dtos.pdf_view_dtos import SegmentViewData, HighlightUpdateInfo, ImageViewData, PageDisplayViewModel

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
    linkClicked = Signal(str) # linkClicked 시그널 추가
    fileDropped = Signal(str)  # PDF 파일 드롭 시그널 추가

    def __init__(self, view_context: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.view_context = view_context
        self._current_segments_on_display: Dict[str, SegmentViewData] = {}
        self._text_items: Dict[str, QGraphicsTextItem] = {}
        self.setAcceptDrops(True)  # 드래그&드롭 허용
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
        self.graphics_view.wheelEvent = self._custom_wheel_event
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
            text_item = QGraphicsTextItem() # QGraphicsTextItem 생성

            # 폰트 및 색상 설정
            font = QFont(segment_data.font_family, segment_data.font_size)
            font.setBold(segment_data.is_bold)
            font.setItalic(segment_data.is_italic)
            text_item.setFont(font)

            if segment_data.link_uri:
                # 링크가 있는 경우, HTML로 설정하고 상호작용 활성화
                escaped_text = html.escape(segment_data.text)
                html_content = f'<a href="{segment_data.link_uri}" style="color:blue; text-decoration:underline;">{escaped_text}</a>'
                text_item.setHtml(html_content)
                text_item.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
                text_item.setOpenExternalLinks(False)  # 우리가 직접 처리
                text_item.linkActivated.connect(self._on_link_activated) # 링크 활성화 시그널 연결
            else:
                # 일반 텍스트
                text_item.setPlainText(segment_data.text)
                text_item.setDefaultTextColor(segment_data.font_color)

            # 텍스트 아이템의 자연스러운 크기를 얻음 (자동 줄바꿈 없이)
            natural_rect = text_item.boundingRect()
            target_rect = segment_data.rect

            if natural_rect.width() == 0 or natural_rect.height() == 0:
                continue

            # 텍스트가 바운딩 박스를 벗어나는 경우에만 크기를 줄이도록 스케일 계산
            # 텍스트가 늘어나는 것을 방지하기 위해 1.0보다 크게 스케일링하지 않음
            scale = 1.0
            # 텍스트의 자연스러운 크기가 목표 사각형보다 클 때만 스케일 조정
            if natural_rect.width() > target_rect.width() or natural_rect.height() > target_rect.height():
                scale_x = target_rect.width() / natural_rect.width()
                scale_y = target_rect.height() / natural_rect.height()
                scale = min(scale_x, scale_y) # 가로/세로 비율을 유지하며 축소

            # 텍스트를 바운딩 박스의 좌상단에 위치시키고, 필요한 경우 균일하게 축소
            transform = QTransform()
            transform.translate(target_rect.left(), target_rect.top())
            transform.scale(scale, scale)
            transform.translate(-natural_rect.left(), -natural_rect.top())
            text_item.setTransform(transform)

            # 링크가 아닌 경우에만 선택 비활성화
            if not segment_data.link_uri:
                text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
            text_item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False) # 이동은 항상 비활성화
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

    def _on_link_activated(self, link: str):
        self.linkClicked.emit(link) # linkClicked 시그널 방출

    def _custom_wheel_event(self, event):
        """
        마우스 휠 이벤트를 처리합니다.
        - Ctrl + 휠: 뷰 확대/축소
        - Shift + 휠: 좌우 스크롤
        - 일반 휠: 상하 스크롤
        """
        modifiers = event.modifiers()
        if modifiers == Qt.KeyboardModifier.ControlModifier:
            self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
            if event.angleDelta().y() > 0:
                self.graphics_view.scale(1.1, 1.1)
                self.zoom_in_requested.emit()
            else:
                self.graphics_view.scale(1 / 1.1, 1 / 1.1)
                self.zoom_out_requested.emit()
            self.graphics_view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
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
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self):
        """뷰를 10% 확대합니다."""
        self.graphics_view.scale(1.1, 1.1)

    def zoom_out(self):
        """뷰를 10% 축소합니다."""
        self.graphics_view.scale(1 / 1.1, 1 / 1.1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                self.fileDropped.emit(file_path)
                break
        event.acceptProposedAction()

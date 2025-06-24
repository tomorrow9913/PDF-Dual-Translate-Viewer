import html

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QFont,
    QTextCharFormat,
    QTextCursor,
    QTransform,
)
from PySide6.QtWidgets import QGraphicsTextItem

from src.infrastructure.dtos.pdf_view_dtos import SegmentViewData


class TextSegmentItem(QGraphicsTextItem):
    linkActivated = Signal(str)

    def __init__(self, segment_data: SegmentViewData, parent=None):
        super().__init__(parent)
        self.segment_data = segment_data

        # Store original font properties from PDF
        self._original_font = QFont(segment_data.font_family, segment_data.font_size)
        self._original_font.setBold(segment_data.is_bold)
        self._original_font.setItalic(segment_data.is_italic)
        self._original_color = segment_data.font_color

        # Apply initial font and color (can be overridden by display_font)
        self.setFont(self._original_font)
        self.setDefaultTextColor(self._original_color)

        if segment_data.link_uri:
            escaped_text = html.escape(segment_data.text)
            html_content = f'<a href="{segment_data.link_uri}" style="color:blue; text-decoration:underline;">{escaped_text}</a>'
            self.setHtml(html_content)
            self.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.setOpenExternalLinks(False)
            self.setCursor(QCursor(Qt.PointingHandCursor))
            self.setToolTip(f"Link: {segment_data.link_uri}")
        else:
            self.setPlainText(segment_data.text)

        # Transform for position/scale
        natural_rect = self.boundingRect()
        target_rect = segment_data.rect
        scale = 1.0
        if (
            natural_rect.width() > 0 and natural_rect.height() > 0
        ):  # Check for non-zero dimensions
            if (
                natural_rect.width() > target_rect.width()
                or natural_rect.height() > target_rect.height()
            ):
                scale_x = target_rect.width() / natural_rect.width()
                scale_y = target_rect.height() / natural_rect.height()
                scale = min(scale_x, scale_y)
        transform = QTransform()
        transform.translate(target_rect.left(), target_rect.top())
        transform.scale(scale, scale)
        transform.translate(-natural_rect.left(), -natural_rect.top())
        self.setTransform(transform)
        self.setFlag(self.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(self.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        self._highlighted = segment_data.is_highlighted  # Store initial highlight state
        self._current_highlight_color = QColor("#ffffcc")  # Default highlight color
        self._apply_highlight_format(self._highlighted, self._current_highlight_color)

    def set_display_font(self, font: QFont):
        """
        텍스트 아이템의 표시 폰트를 설정합니다.
        원본 PDF의 폰트 속성(bold, italic)을 유지하면서 크기/패밀리만 변경합니다.
        """
        new_font = QFont(font.family(), font.pointSize())
        new_font.setBold(self._original_font.bold())
        new_font.setItalic(self._original_font.italic())
        self.setFont(new_font)

    def set_highlight_color(self, color: QColor):
        """하이라이트 색상을 변경하고 적용합니다."""
        self._current_highlight_color = color
        self._apply_highlight_format(self._highlighted, self._current_highlight_color)

    def _apply_highlight_format(self, highlight: bool, color: QColor):
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        char_format = QTextCharFormat()
        if highlight:
            char_format.setBackground(QBrush(color))
        else:
            char_format.clearBackground()
        cursor.setCharFormat(char_format)

    def set_highlighted(self, highlight):
        self._highlighted = highlight
        self._apply_highlight_format(highlight, self._current_highlight_color)

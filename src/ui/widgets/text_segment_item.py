from PySide6.QtWidgets import QGraphicsTextItem
from PySide6.QtGui import QFont, QColor, QBrush, QTransform
from PySide6.QtCore import Qt
import html

class TextSegmentItem(QGraphicsTextItem):
    def __init__(self, segment_data, parent=None):
        super().__init__(parent)
        self.segment_id = segment_data.segment_id
        self.setFont(QFont(segment_data.font_family, segment_data.font_size))
        self.setDefaultTextColor(segment_data.font_color)
        if segment_data.link_uri:
            escaped_text = html.escape(segment_data.text)
            html_content = f'<a href="{segment_data.link_uri}" style="color:blue; text-decoration:underline;">{escaped_text}</a>'
            self.setHtml(html_content)
            self.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.setOpenExternalLinks(False)
        else:
            self.setPlainText(segment_data.text)
        # Transform for position/scale
        natural_rect = self.boundingRect()
        target_rect = segment_data.rect
        scale = 1.0
        if natural_rect.width() > 0 and natural_rect.height() > 0:
            if natural_rect.width() > target_rect.width() or natural_rect.height() > target_rect.height():
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
        self._highlighted = segment_data.is_highlighted
        self._apply_highlight_format(self._highlighted)
        self.link_uri = segment_data.link_uri

    def _apply_highlight_format(self, highlight):
        from PySide6.QtGui import QTextCursor, QTextCharFormat
        cursor = QTextCursor(self.document())
        cursor.select(QTextCursor.SelectionType.Document)
        char_format = QTextCharFormat()
        if highlight:
            char_format.setBackground(QBrush(QColor("#ffffcc")))
        else:
            char_format.clearBackground()
        cursor.setCharFormat(char_format)

    def set_highlighted(self, highlight):
        self._highlighted = highlight
        self._apply_highlight_format(highlight)

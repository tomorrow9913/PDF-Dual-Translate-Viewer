from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from src.infrastructure.dtos.app_settings_dtos import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, current_settings: AppSettings, parent=None):  # type: ignore
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(400, 240)
        self.setModal(True)
        # Create a mutable copy of current settings to work with
        self._new_settings = AppSettings(
            font_family=current_settings.font_family,
            font_size=current_settings.font_size,
            highlight_color_hex=current_settings.highlight_color_hex,
        )
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # Font settings
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("폰트:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self._new_settings.font)
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        font_layout.addWidget(self.font_combo)

        font_layout.addWidget(QLabel("크기:"))
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(6, 72)
        self.font_size_spinbox.setValue(self._new_settings.font_size)
        self.font_size_spinbox.valueChanged.connect(self._on_font_size_changed)
        font_layout.addWidget(self.font_size_spinbox)
        main_layout.addLayout(font_layout)

        # Highlight color settings
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("하이라이트 색상:"))
        self.highlight_color_button = QPushButton("색상 선택")
        self.highlight_color_button.clicked.connect(
            self._on_highlight_color_button_clicked
        )
        self.highlight_color_preview = QLabel()
        self.highlight_color_preview.setFixedSize(20, 20)
        self._update_highlight_color_preview(self._new_settings.highlight_color)
        color_layout.addWidget(self.highlight_color_button)
        color_layout.addWidget(self.highlight_color_preview)
        color_layout.addStretch()
        main_layout.addLayout(color_layout)

        # Preview text
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("미리보기:"))
        self.preview_label = QLabel()
        self._update_preview_label()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)

        # OK/Cancel buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def _on_font_changed(self, font: QFont):
        self._new_settings.font_family = font.family()
        self._update_preview_label()

    def _on_font_size_changed(self, size: int):
        self._new_settings.font_size = size
        self._update_preview_label()

    def _on_highlight_color_button_clicked(self):
        color = QColorDialog.getColor(self._new_settings.highlight_color, self)
        if color.isValid():
            self._new_settings.highlight_color_hex = color.name()
            self._update_highlight_color_preview(color)
            self._update_preview_label()

    def _update_highlight_color_preview(self, color: QColor):
        self.highlight_color_preview.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid black;"
        )

    def _update_preview_label(self):
        # Example: 'Normal text [highlighted] normal text' where only [highlighted] is colored
        font = self._new_settings.font
        color_hex = self._new_settings.highlight_color_hex
        html_content = f'<span style="font-family:{font.family()}; font-size:{font.pointSize()}pt;">'
        html_content += "일반텍스트 "
        html_content += f'<span style="background-color:{color_hex};">하이라이트</span>'
        html_content += " 일반텍스트</span>"
        self.preview_label.setText(html_content)
        self.preview_label.setTextFormat(Qt.RichText)

    def get_settings(self):
        return self._new_settings

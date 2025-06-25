from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QSpinBox  # 추가
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QFontComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.infrastructure.dtos.app_settings_dtos import AppSettings


class SettingsDialog(QDialog):
    def __init__(self, current_settings: AppSettings, parent=None):  # type: ignore
        super().__init__(parent)
        self.setWindowTitle("설정")
        self.resize(400, 280)
        self.setModal(True)
        # Create a mutable copy of current settings to work with
        self._new_settings = AppSettings(
            font_family=current_settings.font_family,
            highlight_color_hex=current_settings.highlight_color_hex,
            prefetch_page_count=current_settings.prefetch_page_count,
            preview_page_count=current_settings.preview_page_count,
            enable_highlighting=current_settings.enable_highlighting,
        )
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 폰트 설정 (QFontComboBox만)
        font_layout = QHBoxLayout()
        font_layout.addWidget(QLabel("폰트:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self._new_settings.font)
        self.font_combo.currentFontChanged.connect(self._on_font_changed)
        font_layout.addWidget(self.font_combo)
        main_layout.addLayout(font_layout)

        # 하이라이트 색상 설정
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("하이라이트 색상:"))
        self.color_btn = QPushButton("색상 선택")
        self.color_btn.clicked.connect(self._on_color_btn_clicked)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(40, 20)
        self._update_highlight_color_preview(self._new_settings.highlight_color)
        color_layout.addWidget(self.color_btn)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        main_layout.addLayout(color_layout)

        # 미리 번역할 페이지 수 설정
        prefetch_layout = QHBoxLayout()
        prefetch_layout.addWidget(QLabel("미리 번역할 페이지 수:"))
        self.prefetch_spin = QSpinBox()
        self.prefetch_spin.setRange(0, 20)
        self.prefetch_spin.setValue(self._new_settings.prefetch_page_count)
        self.prefetch_spin.setSingleStep(1)
        self.prefetch_spin.valueChanged.connect(self._on_prefetch_count_changed)
        prefetch_layout.addWidget(self.prefetch_spin)
        prefetch_layout.addStretch()
        main_layout.addLayout(prefetch_layout)

        # 미리보기 페이지 수 설정
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("미리보기 페이지 수:"))
        self.preview_spin = QSpinBox()
        self.preview_spin.setRange(1, 50)  # 최소 1페이지, 최대 50페이지 등 적절히 설정
        self.preview_spin.setValue(self._new_settings.preview_page_count)
        self.preview_spin.setSingleStep(1)
        self.preview_spin.valueChanged.connect(self._on_preview_count_changed)
        preview_layout.addWidget(self.preview_spin)
        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)

        # 하이라이트 기능 활성화 여부 설정
        highlight_enable_layout = QHBoxLayout()
        self.highlight_enable_checkbox = QCheckBox("하이라이트 기능 사용")
        self.highlight_enable_checkbox.setChecked(
            self._new_settings.enable_highlighting
        )
        self.highlight_enable_checkbox.stateChanged.connect(
            self._on_highlight_enabled_changed
        )
        highlight_enable_layout.addWidget(self.highlight_enable_checkbox)
        main_layout.addLayout(highlight_enable_layout)

        # 예시 텍스트 미리보기 (일부만 하이라이트)
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("미리보기:"))
        self.preview_label = QLabel()
        self._update_preview_label()
        preview_layout.addWidget(self.preview_label)
        preview_layout.addStretch()
        main_layout.addLayout(preview_layout)

        # OK/Cancel 버튼
        button_layout = QHBoxLayout()
        ok_button = QPushButton("확인")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        main_layout.addLayout(button_layout)

    def _on_font_changed(self, font):
        self._new_settings.font_family = font.family()
        self._update_preview_label()

    def _on_color_btn_clicked(self):
        color = QColorDialog.getColor(self._new_settings.highlight_color, self)
        if color.isValid():
            self._new_settings.highlight_color_hex = color.name()
            self._update_highlight_color_preview(color)
            self._update_preview_label()

    def _on_prefetch_count_changed(self, value):
        self._new_settings.prefetch_page_count = value
        # 미리보기 등 필요시 반영 가능

    def _on_preview_count_changed(self, value):
        self._new_settings.preview_page_count = value

    def _on_highlight_enabled_changed(self, state):
        self._new_settings.enable_highlighting = bool(state)

    def _update_highlight_color_preview(self, color: QColor):
        self.color_preview.setStyleSheet(
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

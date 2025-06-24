from PySide6.QtGui import QColor

from src.infrastructure.dtos.app_settings_dtos import AppSettings
from src.infrastructure.gateways.settings_persistence_gateway import (
    SettingsPersistenceGateway,
)


class SettingsService:
    def __init__(self):
        self._persistence_gateway = SettingsPersistenceGateway()

    def load_settings(self) -> AppSettings:
        """
        Loads application settings.
        """
        settings_data = self._persistence_gateway.load_settings()
        if settings_data:
            return AppSettings.from_dict(settings_data)
        return AppSettings()  # Default settings if no file or error

    def save_settings(self, settings: AppSettings):
        """
        Saves application settings.
        """
        self._persistence_gateway.save_settings(settings.to_dict())
        print(f"Settings saved (not persisted yet): {settings}")

    def apply_settings(self, settings: AppSettings, main_window_instance):
        # Use the properties that return QFont/QColor objects
        display_font = settings.font
        main_window_instance.original_pdf_widget.set_display_font(display_font)
        main_window_instance.translated_pdf_widget.set_display_font(display_font)

        highlight_qcolor = QColor(settings.highlight_color)
        main_window_instance.original_pdf_widget.set_highlight_color(highlight_qcolor)
        main_window_instance.translated_pdf_widget.set_highlight_color(highlight_qcolor)

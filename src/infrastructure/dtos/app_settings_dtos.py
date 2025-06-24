from dataclasses import dataclass
from typing import Any, Dict

from PySide6.QtGui import QColor, QFont


@dataclass
class AppSettings:
    font_family: str = "Arial"
    highlight_color_hex: str = "#ffffcc"  # Store as hex string for serialization

    @property
    def font(self) -> QFont:
        return QFont(self.font_family)

    @property
    def highlight_color(self) -> QColor:
        return QColor(self.highlight_color_hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_family": self.font.family(),
            "highlight_color_hex": self.highlight_color.name(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppSettings":
        return AppSettings(
            font_family=data.get("font_family", "Arial"),
            highlight_color_hex=data.get("highlight_color_hex", "#ffffcc"),
        )

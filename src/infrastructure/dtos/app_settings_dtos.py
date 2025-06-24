from dataclasses import dataclass
from typing import Any, Dict

from PySide6.QtGui import QColor, QFont


@dataclass
class AppSettings:
    font_family: str = "Arial"
    font_size: int = 10
    highlight_color_hex: str = "#ffffcc"  # Store as hex string for serialization

    @property
    def font(self) -> QFont:
        qfont = QFont(self.font_family, self.font_size)
        return qfont

    @property
    def highlight_color(self) -> QColor:
        return QColor(self.highlight_color_hex)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "font_family": self.font.family(),
            "font_point_size": self.font.pointSize(),
            "highlight_color_hex": self.highlight_color.name(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppSettings":
        return AppSettings(
            font_family=data.get("font_family", "Arial"),
            font_size=data.get("font_point_size", 10),
            highlight_color_hex=data.get("highlight_color_hex", "#ffffcc"),
        )

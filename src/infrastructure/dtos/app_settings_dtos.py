from dataclasses import dataclass
from typing import Any, Dict

from PySide6.QtGui import QColor, QFont


@dataclass
class AppSettings:
    font_family: str = "Arial"
    highlight_color_hex: str = "#ffffcc"  # Store as hex string for serialization
    prefetch_page_count: int = 0  # 미리 번역할 페이지 수 (백그라운드)
    preview_page_count: int = 10  # 미리보기 다이얼로그에 표시할 페이지 수 (썸네일)
    enable_highlighting: bool = True  # 하이라이트 기능 활성화 여부

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
            "prefetch_page_count": self.prefetch_page_count,  # 백그라운드 프리페치
            "preview_page_count": self.preview_page_count,  # 미리보기 다이얼로그 (썸네일)
            "enable_highlighting": self.enable_highlighting,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AppSettings":
        return AppSettings(
            font_family=data.get("font_family", "Arial"),
            highlight_color_hex=data.get("highlight_color_hex", "#ffffcc"),
            prefetch_page_count=data.get(
                "prefetch_page_count", 0
            ),  # 백그라운드 프리페치
            preview_page_count=data.get(
                "preview_page_count", 10
            ),  # 미리보기 다이얼로그
            enable_highlighting=data.get("enable_highlighting", True),
        )

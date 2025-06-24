from src.infrastructure.dtos.pdf_view_dtos import PageDisplayViewModel  # type: ignore
from src.infrastructure.dtos.pdf_view_dtos import HighlightUpdateInfo


class PdfPresenter:
    @staticmethod
    def present_page(view_model: PageDisplayViewModel):
        """
        ViewModel을 받아 UI에 전달할 데이터(딕셔너리 등)로 변환
        (실제 UI에서는 이 데이터를 받아 렌더링)
        """
        return {
            "page_number": view_model.page_number,
            "page_width": view_model.page_width,
            "page_height": view_model.page_height,
            "original_segments": view_model.original_segments_view,
            "translated_segments": view_model.translated_segments_view,
            "image_views": view_model.image_views,
            "error_message": view_model.error_message,
        }

    @staticmethod
    def present_highlights(highlight_info: HighlightUpdateInfo):
        """
        HighlightUpdateInfo를 받아 UI에 전달할 데이터로 변환
        """
        return highlight_info.segments_to_update

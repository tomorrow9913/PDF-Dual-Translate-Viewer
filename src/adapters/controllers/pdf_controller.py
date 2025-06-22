from src.core.use_cases.pdf_parsing_service import PdfParsingService
from src.core.use_cases.translation_service import TranslationService
from src.core.use_cases.pdf_page_service import PdfPageService
from src.common.constants import LANGUAGES

class PdfController:
    def __init__(self, pdf_doc=None, translation_service=None, pdf_parser=None):
        self.pdf_doc = pdf_doc
        self.current_page = 0
        self.view_model = None
        # TranslationService 인스턴스 주입(없으면 기본 GoogleTranslationGateway 사용)
        if translation_service is not None:
            self.translation_service = translation_service
        else:
            from src.adapters.gateways.google_translation_gateway import GoogleTranslationGateway
            self.translation_service = TranslationService(GoogleTranslationGateway())
        # PDF 파서 주입(없으면 기본 FitzPdfParserGateway 사용)
        if pdf_parser is not None:
            self.pdf_parser = pdf_parser
        else:
            from src.adapters.gateways.fitz_pdf_parser_gateway import FitzPdfParserGateway
            self.pdf_parser = FitzPdfParserGateway()

    def open_pdf(self, file_path):
        import fitz
        self.pdf_doc = fitz.open(file_path)
        self.current_page = 0
        return self.pdf_doc

    def get_page_view_model(self, page_number):
        if not self.pdf_doc:
            return None
        page = self.pdf_doc[page_number]
        self.current_page = page_number
        self.view_model = self.pdf_parser.parse_page(page, page_number, self.pdf_doc)
        return self.view_model

    async def translate_current_page(self, source_lang, target_lang):
        if not self.view_model:
            return None
        original_segments = self.view_model.original_segments_view
        translated_texts = await self.translation_service.translate_segments(original_segments, source_lang, target_lang)
        translated_segments = self.translation_service.build_translated_segments(original_segments, translated_texts)
        self.view_model.translated_segments_view = translated_segments
        return translated_segments

    def get_highlight_update(self, all_segment_ids, hovered_segment_id, view_context):
        segments_to_update = PdfPageService.update_highlights(all_segment_ids, hovered_segment_id)
        # 동기화 로직(원본-번역 쌍 하이라이트)
        all_orig_ids = [s for s in all_segment_ids if s.startswith("orig_")]
        all_trans_ids = [s for s in all_segment_ids if s.startswith("trans_")]
        if hovered_segment_id:
            if view_context == "ORIGINAL" and hovered_segment_id.startswith("orig_"):
                translated_sibling_id = hovered_segment_id.replace("orig_", "trans_")
                if translated_sibling_id in all_trans_ids:
                    segments_to_update[translated_sibling_id] = True
            elif view_context == "TRANSLATED" and hovered_segment_id.startswith("trans_"):
                original_sibling_id = hovered_segment_id.replace("trans_", "orig_")
                if original_sibling_id in all_orig_ids:
                    segments_to_update[original_sibling_id] = True
        return segments_to_update

import asyncio
from src.infrastructure.gateways.translation_gateway import TranslationGateway
from src.ui.widgets.pdf_view_widget import SegmentViewData

class TranslationService:
    def __init__(self, gateway: TranslationGateway):
        self.gateway = gateway

    async def translate_segments(self, segments, source_lang, target_lang):
        """
        SegmentViewData 리스트를 받아 번역 결과를 반환
        """
        texts_to_translate = [seg.text for seg in segments]
        tasks = [self.gateway.translate(text, source_lang, target_lang) for text in texts_to_translate]
        translated_texts = await asyncio.gather(*tasks)
        return translated_texts

    @staticmethod
    def build_translated_segments(original_segments, translated_texts):
        """
        번역 결과를 SegmentViewData 리스트로 변환
        """
        return [
            SegmentViewData(
                segment_id=seg.segment_id.replace("orig_", "trans_"),
                text=translated_texts[i] if translated_texts[i] else seg.text,
                rect=seg.rect.getRect(),
                font_family=seg.font_family,
                font_size=seg.font_size,
                font_color=seg.font_color.name(),
                is_bold=seg.is_bold,
                is_italic=seg.is_italic,
                is_highlighted=seg.is_highlighted
            ) for i, seg in enumerate(original_segments)
        ]

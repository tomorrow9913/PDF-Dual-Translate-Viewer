import pytest

from src.core.use_cases.translation_service import TranslationService
from src.infrastructure.dtos.pdf_view_dtos import SegmentViewData


class DummyTranslationGateway:
    async def translate(self, text, source, target):
        return f"{text} (translated)"


@pytest.mark.asyncio
async def test_translate_segments_and_build():
    segs = [
        SegmentViewData(
            segment_id="orig_1",
            text="Hello world!",
            rect=(0, 0, 100, 20),
            font_family="Arial",
            font_size=10,
            font_color="#000000",
            is_bold=False,
            is_italic=False,
            is_highlighted=False,
        )
    ]
    service = TranslationService(DummyTranslationGateway())
    translated = await service.translate_segments(segs, "en", "ko")
    assert isinstance(translated, list)
    assert len(translated) == 1
    assert translated[0].endswith("(translated)")
    segs2 = service.build_translated_segments(segs, translated)
    assert segs2[0].text == translated[0]

import asyncio
from collections import OrderedDict

import fitz

from src.adapters.gateways.translation_gateway import TranslationGateway
from src.infrastructure.dtos.pdf_view_dtos import SegmentViewData


class TranslationService:
    def __init__(self, gateway: TranslationGateway):
        self.gateway = gateway

    async def translate_segments(self, segments, source_lang, target_lang) -> dict:
        """
        SegmentViewData 리스트를 받아 번역 결과를 반환합니다.
        번역 품질을 위해 세그먼트를 블록 단위로 묶어 번역 API에 요청합니다.
        :return: {block_id: translated_text} 형태의 딕셔너리
        """
        if not segments:
            return {}

        # 1. block_id를 기준으로 세그먼트를 순서대로 그룹화합니다.
        blocks = OrderedDict()
        for seg in segments:
            if seg.block_id not in blocks:
                blocks[seg.block_id] = []
            blocks[seg.block_id].append(seg)

        # 2. 블록별로 텍스트를 합치고 번역을 요청합니다.
        #    줄바꿈(\n)으로 텍스트를 연결하여 문단 구조를 유지합니다.
        block_texts_to_translate = [
            "\n".join(s.text for s in block_segments)
            for block_segments in blocks.values()
        ]

        tasks = [
            self.gateway.translate(text, source_lang, target_lang)
            for text in block_texts_to_translate
        ]
        translated_block_texts = await asyncio.gather(*tasks)

        # 3. 번역된 블록 텍스트를 block_id에 매핑하여 반환합니다.
        translated_blocks = {}
        for i, block_id in enumerate(blocks.keys()):
            translated_blocks[block_id] = translated_block_texts[i]

        return translated_blocks

    @staticmethod
    def build_translated_segments(original_segments, translated_blocks: dict):
        """
        번역된 블록 딕셔너리를 기반으로 번역된 SegmentViewData 리스트를 생성합니다.
        각 번역된 블록은 하나의 SegmentViewData로 만들어집니다.
        """
        if not original_segments:
            return []

        blocks = OrderedDict()
        for seg in original_segments:
            if seg.block_id not in blocks:
                blocks[seg.block_id] = []
            blocks[seg.block_id].append(seg)

        translated_segments = []
        for block_id, segments_in_block in blocks.items():
            if block_id not in translated_blocks or not translated_blocks[block_id]:
                continue

            block_bbox = fitz.Rect()
            for seg in segments_in_block:
                qrect = seg.rect
                block_bbox.include_rect(
                    fitz.Rect(
                        qrect.x(),
                        qrect.y(),
                        qrect.x() + qrect.width(),
                        qrect.y() + qrect.height(),
                    )
                )

            first_seg = segments_in_block[0]
            translated_text = translated_blocks[block_id]

            translated_segments.append(
                SegmentViewData(
                    segment_id=f"trans_{block_id}",
                    text=translated_text,
                    rect=(
                        block_bbox.x0,
                        block_bbox.y0,
                        block_bbox.width,
                        block_bbox.height,
                    ),
                    font_family=first_seg.font_family,
                    font_size=first_seg.font_size,
                    font_color=first_seg.font_color.name(),
                    is_bold=first_seg.is_bold,
                    is_italic=first_seg.is_italic,
                    is_highlighted=False,
                    block_id=block_id,
                    line_id=None,
                )
            )
        return translated_segments

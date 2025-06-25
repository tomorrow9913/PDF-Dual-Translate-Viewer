import fitz
from PySide6.QtCore import QRectF

from src.infrastructure.dtos.pdf_view_dtos import (
    ImageViewData,
    PageDisplayViewModel,
    SegmentViewData,
)


class PdfParsingService:
    @staticmethod
    def parse_page(page, page_number, pdf_doc):
        """
        PDF 페이지에서 텍스트 세그먼트, 이미지, 링크 등 정보를 추출하여 PageDisplayViewModel로 반환.
        - 텍스트 블록을 하나의 세그먼트로 병합하여 번역 품질 향상.
        - 성능 향상을 위해 링크 정보를 미리 처리.
        """
        # 1. 링크 정보 미리 처리 (성능 최적화 및 가독성 향상)
        # 각 스팬을 순회할 때마다 전체 링크 목록을 다시 탐색하는 것을 방지합니다.
        # R-tree 같은 공간 인덱스를 사용하면 대규모 문서에서 더 큰 성능 향상을 기대할 수 있습니다.
        processed_links = []
        for link in page.get_links():
            link_rect = fitz.Rect(link["from"])
            uri = None
            kind = link.get("kind")

            if kind == fitz.LINK_GOTO:
                # 내부 페이지 이동 링크
                uri = f"page:{link.get('page', -1)}"
            elif kind == fitz.LINK_URI:
                # 외부 URL 링크
                uri = link.get("uri")
            elif kind == fitz.LINK_LAUNCH:
                # 파일 실행 링크 (보안상 주의 필요)
                uri = f"file:{link.get('file')}"
            elif kind == fitz.LINK_NAMED:
                # 명명된 목적지 링크
                uri = f"name:{link.get('name')}"
            # fitz.LINK_REMOTE 등 다른 종류의 링크도 필요에 따라 추가할 수 있습니다.

            if uri:
                processed_links.append({"rect": link_rect, "uri": uri})

        page_rect = page.rect
        # 이미지 추출
        image_views = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            img_rect = page.get_image_bbox(img_info)
            if img_rect.is_valid:
                # 지연 로딩: 실제 이미지 데이터 대신 xref와 좌표만 저장
                image_views.append(
                    ImageViewData(
                        xref=xref,
                        rect=QRectF(
                            img_rect.x0, img_rect.y0, img_rect.width, img_rect.height
                        ),
                    )
                )

        # 텍스트 세그먼트 추출 (UI 상호작용을 위해 줄(line) 단위로 분리)
        segments = []
        # `get_text("dict")`는 텍스트 블록에 대한 상세 정보를 제공합니다.
        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:  # 0은 텍스트 블록을 의미
                continue

            for line_idx, line in enumerate(block["lines"]):
                line_spans = line.get("spans", [])
                if not line_spans:
                    continue

                # 줄(line) 내의 모든 스팬(span)을 병합하여 하나의 텍스트로 만듭니다.
                line_text = " ".join(span["text"] for span in line_spans)
                if not line_text.strip():
                    continue

                # 줄의 경계 상자(bounding box)를 계산합니다.
                line_bbox = fitz.Rect()
                for span in line_spans:
                    line_bbox.include_rect(fitz.Rect(span["bbox"]))

                # 줄에 대한 링크를 찾습니다.
                line_link_uri = None
                for link_info in processed_links:
                    if link_info["rect"].intersects(line_bbox):
                        line_link_uri = link_info["uri"]
                        break

                # 폰트 정보는 첫 번째 스팬의 것을 대표로 사용합니다.
                first_span = line_spans[0]
                block_id = f"block_{page_number}_{block['number']}"
                line_id = f"line_{page_number}_{block['number']}_{line_idx}"

                rect = (line_bbox.x0, line_bbox.y0, line_bbox.width, line_bbox.height)
                seg = SegmentViewData(
                    segment_id=f"orig_{line_id}",
                    text=line_text,
                    rect=rect,
                    font_family=first_span.get("font", "Arial"),
                    font_size=first_span["size"],
                    font_color="#000000",
                    is_bold="bold" in first_span.get("font", "").lower(),
                    is_italic="italic" in first_span.get("font", "").lower(),
                    is_highlighted=False,
                    link_uri=line_link_uri,
                    block_id=block_id,
                    line_id=line_id,
                )
                segments.append(seg)
        view_model = PageDisplayViewModel(
            page_number=page_number + 1,
            page_width=page_rect.width,
            page_height=page_rect.height,
            original_segments_view=segments,
            translated_segments_view=[
                SegmentViewData(
                    segment_id=seg.segment_id.replace("orig_", "trans_"),
                    text=seg.text,  # 초기에는 원본 텍스트로 채움
                    rect=seg.rect.getRect(),
                    font_family=seg.font_family,
                    font_size=seg.font_size,
                    font_color=seg.font_color.name(),
                    is_bold=seg.is_bold,
                    is_italic=seg.is_italic,
                    is_highlighted=seg.is_highlighted,
                    link_uri=None,
                    block_id=seg.block_id,
                    line_id=seg.line_id,
                )
                for seg in segments
            ],
            image_views=image_views,
        )
        return view_model

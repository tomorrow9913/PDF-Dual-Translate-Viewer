import fitz
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap
from src.infrastructure.dtos.pdf_view_dtos import SegmentViewData, ImageViewData, PageDisplayViewModel

class PdfParsingService:
    @staticmethod
    def parse_page(page, page_number, pdf_doc):
        """
        PDF 페이지에서 텍스트 세그먼트, 이미지, 링크 등 정보를 추출하여 PageDisplayViewModel로 반환
        - 링크 감지 로직을 스팬 단위로 정교화하고, 다양한 링크 종류를 처리하도록 개선.
        - 성능 향상을 위해 링크 정보를 미리 처리.
        """
        # 1. 링크 정보 미리 처리 (성능 최적화 및 가독성 향상)
        # 각 스팬을 순회할 때마다 전체 링크 목록을 다시 탐색하는 것을 방지합니다.
        # R-tree 같은 공간 인덱스를 사용하면 대규모 문서에서 더 큰 성능 향상을 기대할 수 있습니다.
        processed_links = []
        for link in page.get_links():
            link_rect = fitz.Rect(link['from'])
            uri = None
            kind = link.get('kind')

            if kind == fitz.LINK_GOTO:
                # 내부 페이지 이동 링크
                uri = f"page:{link.get('page', -1)}"
            elif kind == fitz.LINK_URI:
                # 외부 URL 링크
                uri = link.get('uri')
            elif kind == fitz.LINK_LAUNCH:
                # 파일 실행 링크 (보안상 주의 필요)
                uri = f"file:{link.get('file')}"
            elif kind == fitz.LINK_NAMED:
                # 명명된 목적지 링크
                uri = f"name:{link.get('name')}"
            # fitz.LINK_REMOTE 등 다른 종류의 링크도 필요에 따라 추가할 수 있습니다.

            if uri:
                processed_links.append({'rect': link_rect, 'uri': uri})

        page_rect = page.rect
        # 이미지 추출
        image_views = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            img_rect = page.get_image_bbox(img_info)
            if img_rect.is_valid:
                # 지연 로딩: 실제 이미지 데이터 대신 xref와 좌표만 저장
                image_views.append(ImageViewData(xref=xref, rect=QRectF(img_rect.x0, img_rect.y0, img_rect.width, img_rect.height)))
        
        # 텍스트 세그먼트 추출
        segments = []
        for block in page.get_text("dict")['blocks']:
            if block['type'] != 0:  # 0은 텍스트 블록을 의미
                continue
            for line in block['lines']:
                for span in line['spans']:
                    # 2. 스팬(span) 단위로 링크를 정확하게 매핑
                    span_rect = fitz.Rect(span['bbox'])
                    span_link_uri = None
                    # 미리 처리된 링크 목록에서 현재 스팬과 겹치는 링크를 찾습니다.
                    for link_info in processed_links:
                        if link_info['rect'].intersects(span_rect):
                            span_link_uri = link_info['uri']
                            break  # 이 스팬에 대한 링크를 찾았으므로 중단

                    rect = (span['bbox'][0], span['bbox'][1], span['bbox'][2] - span['bbox'][0], span['bbox'][3] - span['bbox'][1])
                    seg = SegmentViewData(
                        segment_id=f"orig_{page_number}_{span['bbox']}",
                        text=span['text'],
                        rect=rect,
                        font_family=span.get('font', 'Arial'),
                        font_size=span['size'],
                        font_color="#000000",  # 링크의 시각적 표시는 UI(TextSegmentItem)에서 처리
                        is_bold='bold' in span.get('font', '').lower(),
                        is_italic='italic' in span.get('font', '').lower(),
                        is_highlighted=False,
                        link_uri=span_link_uri  # 스팬에 해당하는 특정 링크 할당
                    )
                    segments.append(seg)
        view_model = PageDisplayViewModel(
            page_number=page_number+1,
            page_width=page_rect.width,
            page_height=page_rect.height,
            original_segments_view=segments,
            translated_segments_view=[
                SegmentViewData(
                    segment_id=seg.segment_id.replace("orig_", "trans_"),
                    text=seg.text,
                    rect=seg.rect.getRect(),
                    font_family=seg.font_family,
                    font_size=seg.font_size,
                    font_color=seg.font_color.name(),
                    is_bold=seg.is_bold,
                    is_italic=seg.is_italic,
                    is_highlighted=seg.is_highlighted,
                    link_uri=None  # 번역된 텍스트에는 링크를 복사하지 않음 (정책에 따라 변경 가능)
                ) for seg in segments
            ],
            image_views=image_views
        )
        return view_model

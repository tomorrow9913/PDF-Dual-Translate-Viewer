import fitz
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPixmap
from src.ui.widgets.pdf_view_widget import SegmentViewData, ImageViewData, PageDisplayViewModel

class PdfParsingService:
    @staticmethod
    def parse_page(page, page_number, pdf_doc):
        """
        PDF 페이지에서 텍스트 세그먼트, 이미지, 링크 등 정보를 추출하여 PageDisplayViewModel로 반환
        """
        links = page.get_links()
        page_rect = page.rect
        # 이미지 추출
        image_views = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_image = pdf_doc.extract_image(xref)
            if not base_image:
                continue
            image_bytes = base_image["image"]
            pixmap = QPixmap()
            pixmap.loadFromData(image_bytes)
            img_rect = page.get_image_bbox(img_info)
            if not pixmap.isNull() and img_rect.is_valid:
                image_views.append(ImageViewData(pixmap=pixmap, rect=QRectF(img_rect.x0, img_rect.y0, img_rect.width, img_rect.height)))
        segments = []
        for block in page.get_text("dict")['blocks']:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                line_rect = fitz.Rect(line['bbox'])
                line_link_uri = None
                for link in links:
                    if fitz.Rect(link['from']).intersects(line_rect):
                        if link['kind'] == fitz.LINK_GOTO:
                            line_link_uri = f"page:{link['page']}"
                        elif link['kind'] == fitz.LINK_URI:
                            line_link_uri = link['uri']
                        break
                for span in line['spans']:
                    rect = (span['bbox'][0], span['bbox'][1], span['bbox'][2]-span['bbox'][0], span['bbox'][3]-span['bbox'][1])
                    seg = SegmentViewData(
                        segment_id=f"orig_{page_number}_{span['bbox']}",
                        text=span['text'],
                        rect=rect,
                        font_family=span.get('font', 'Arial'),
                        font_size=span['size'],
                        font_color="#000000",
                        is_bold='bold' in span.get('font', '').lower(),
                        is_italic='italic' in span.get('font', '').lower(),
                        is_highlighted=False,
                        link_uri=line_link_uri
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
                    is_highlighted=seg.is_highlighted
                ) for seg in segments
            ],
            image_views=image_views
        )
        return view_model

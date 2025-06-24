import fitz

from src.core.use_cases.pdf_parsing_service import PdfParsingService


def test_parse_page_returns_view_model():
    # 샘플 PDF 생성 (in-memory)
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF!")
    view_model = PdfParsingService.parse_page(page, 0, doc)
    assert view_model.page_number == 1
    assert view_model.page_width > 0
    assert view_model.page_height > 0
    assert len(view_model.original_segments_view) > 0
    assert view_model.original_segments_view[0].text == "Hello PDF!"
    doc.close()

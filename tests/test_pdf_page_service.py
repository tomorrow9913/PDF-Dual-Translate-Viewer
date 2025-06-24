from src.core.use_cases.pdf_page_service import PdfPageService


def test_update_highlights_basic():
    all_ids = ["orig_1", "orig_2", "trans_1", "trans_2"]
    hovered = "orig_1"
    result = PdfPageService.update_highlights(all_ids, hovered)
    assert result["orig_1"] is True
    assert all(v is False for k, v in result.items() if k != "orig_1")

from .pdf_parser_gateway import PdfParserGateway
from src.core.use_cases.pdf_parsing_service import PdfParsingService

class FitzPdfParserGateway(PdfParserGateway):
    def parse_page(self, page, page_number, pdf_doc):
        return PdfParsingService.parse_page(page, page_number, pdf_doc)

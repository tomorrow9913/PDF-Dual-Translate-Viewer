from typing import Protocol


class PdfParserGateway(Protocol):
    def parse_page(self, page, page_number, pdf_doc):
        pass  # Interface method for parsing a PDF page

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox, QProgressBar, QComboBox, QDockWidget, QTreeWidget, QTreeWidgetItem, QApplication
from PySide6.QtCore import Qt, QRectF, Signal, QTimer, QUrl, QEvent
from PySide6.QtGui import QPixmap
from src.ui.widgets.pdf_view_widget import PdfViewWidget, PageDisplayViewModel, SegmentViewData, HighlightUpdateInfo, ImageViewData
import fitz  # PyMuPDF
from PySide6.QtWidgets import QFileDialog, QMessageBox
import asyncio
from src.infrastructure.translation.google_translate_async import google_translate

LANGUAGES = {
    "auto": "Auto Detect",
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "zh-CN": "Chinese (Simplified)",
    "zh-TW": "Chinese (Traditional)",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "ru": "Russian",
    "it": "Italian",
    "pt": "Portuguese",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "th": "Thai",
    "ar": "Arabic",
    "hi": "Hindi",
    "tr": "Turkish",
    "pl": "Polish",
    "nl": "Dutch",
    "sv": "Swedish",
    "fi": "Finnish",
    "no": "Norwegian",
    "da": "Danish",
    "cs": "Czech",
    "hu": "Hungarian",
    "he": "Hebrew",
    "el": "Greek",
    "ro": "Romanian",
    "sk": "Slovak",
    "uk": "Ukrainian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sr": "Serbian",
    "fa": "Persian",
    "ms": "Malay",
    "tl": "Tagalog",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "sl": "Slovenian",
    "mt": "Maltese",
    "ga": "Irish",
    "sq": "Albanian",
    "mk": "Macedonian",
    "af": "Afrikaans",
    "sw": "Swahili",
    "zu": "Zulu",
    "xh": "Xhosa",
    "st": "Southern Sotho",
    "tn": "Tswana",
    "ts": "Tsonga",
    "ss": "Swati",
    "ve": "Venda",
    "nr": "South Ndebele",
    "nso": "Northern Sotho",
    "kg": "Kongo",
    "rw": "Kinyarwanda",
    "so": "Somali",
    "yo": "Yoruba",
    "ig": "Igbo",
    "ha": "Hausa",
    "am": "Amharic",
    "om": "Oromo",
    "ti": "Tigrinya",
    "sn": "Shona",
    "ny": "Chichewa",
    "mg": "Malagasy",
    "rn": "Kirundi",
    "ln": "Lingala",
    "lu": "Luba-Katanga",
    "to": "Tonga",
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 번역기 - 듀얼 뷰어")
        self.setGeometry(100, 100, 800, 600)
        self.auto_translate = False
        self._current_view_model = None
        self.sidebar_visible = False
        self.outline_tree = None
        self.sidebar = None
        self.setAcceptDrops(True)  # 드래그&드롭 허용

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self._syncing_scroll = False # 스크롤 동기화 재귀 방지 플래그

        self._create_toolbar()
        self._create_main_views()
        self._setup_scroll_sync()
        self._create_navigation_bar()
        self._create_status_bar()
        self._load_dummy_data()

        QApplication.instance().installEventFilter(self)

    def _create_status_bar(self):
        """창 하단에 상태바(푸터)를 생성합니다."""
        self.status_bar = self.statusBar()
        self.status_label = QLabel("")
        self.status_bar.addPermanentWidget(self.status_label) # 위젯을 우측에 영구적으로 추가

    def _create_toolbar(self):
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(10, 5, 10, 5)
        # 햄버거 버튼
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedWidth(32)
        self.menu_btn.clicked.connect(self.toggle_sidebar)
        toolbar_layout.addWidget(self.menu_btn)
        # 파일 열기 버튼
        file_open_btn = QPushButton("파일 열기")
        file_open_btn.clicked.connect(self.open_pdf_file)
        toolbar_layout.addWidget(file_open_btn)
        toolbar_layout.addSpacing(10)
        toolbar_layout.addWidget(QLabel("원본 언어:"))
        self.original_lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.original_lang_combo.addItem(f"{name} ({code})", code)
        self.original_lang_combo.setCurrentIndex(0)
        self.original_lang_combo.setEditable(True)
        self.original_lang_combo.setInsertPolicy(QComboBox.NoInsert)
        self.original_lang_combo.setFixedWidth(180)
        self.original_lang_combo.lineEdit().textEdited.connect(lambda text: self._filter_combo(self.original_lang_combo, text))
        toolbar_layout.addWidget(self.original_lang_combo)
        toolbar_layout.addSpacing(20)
        toolbar_layout.addWidget(QLabel("번역 언어:"))
        self.target_lang_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self.target_lang_combo.addItem(f"{name} ({code})", code)
        self.target_lang_combo.setCurrentIndex(list(LANGUAGES.keys()).index("ko"))
        self.target_lang_combo.setEditable(True)
        self.target_lang_combo.setInsertPolicy(QComboBox.NoInsert)
        self.target_lang_combo.setFixedWidth(180)
        self.target_lang_combo.lineEdit().textEdited.connect(lambda text: self._filter_combo(self.target_lang_combo, text))
        toolbar_layout.addWidget(self.target_lang_combo)
        self.translate_btn = QPushButton("번역 실행")
        self.translate_btn.setStyleSheet("background-color: #c0e0c0;")
        self.translate_btn.clicked.connect(self.run_translation)
        toolbar_layout.addWidget(self.translate_btn)
        # 계속 번역 체크박스
        self.auto_translate_checkbox = QCheckBox("계속 번역")
        self.auto_translate_checkbox.stateChanged.connect(self._on_auto_translate_changed)
        toolbar_layout.addWidget(self.auto_translate_checkbox)
        # 글자 크기 +, - 버튼
        self.font_increase_btn = QPushButton("+")
        self.font_increase_btn.setFixedWidth(28)
        self.font_increase_btn.clicked.connect(self.increase_font_size)
        toolbar_layout.addWidget(self.font_increase_btn)
        self.font_decrease_btn = QPushButton("-")
        self.font_decrease_btn.setFixedWidth(28)
        self.font_decrease_btn.clicked.connect(self.decrease_font_size)
        toolbar_layout.addWidget(self.font_decrease_btn)
        
        toolbar_layout.addStretch(1)
        self.main_layout.addLayout(toolbar_layout)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 0) # Indeterminate mode
        self.progress_bar.setVisible(False) # Initially hidden
        self.main_layout.addWidget(self.progress_bar)

    def _on_auto_translate_changed(self, state):
        self.auto_translate = self.auto_translate_checkbox.isChecked()

    def increase_font_size(self):
        self.original_pdf_widget.zoom_in()
        self.translated_pdf_widget.zoom_in()

    def decrease_font_size(self):
        self.original_pdf_widget.zoom_out()
        self.translated_pdf_widget.zoom_out()

    def _create_main_views(self):
        view_area_layout = QHBoxLayout()
        view_area_layout.setContentsMargins(10, 10, 10, 10)
        # 원본/번역 라벨 추가
        original_container = QVBoxLayout()
        original_label = QLabel("<b>원본 PDF 뷰 (Original PDF View)</b>")
        original_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        original_container.addWidget(original_label)
        self.original_pdf_widget = PdfViewWidget(view_context="ORIGINAL")
        original_container.addWidget(self.original_pdf_widget)
        view_area_layout.addLayout(original_container)

        translated_container = QVBoxLayout()
        translated_label = QLabel("<b>번역본 뷰 (Translated View)</b>")
        translated_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        translated_container.addWidget(translated_label)
        self.translated_pdf_widget = PdfViewWidget(view_context="TRANSLATED")
        translated_container.addWidget(self.translated_pdf_widget)
        view_area_layout.addLayout(translated_container)

        self.main_layout.addLayout(view_area_layout, 1)  # stretch factor를 1로 설정하여 이 레이아웃이 수직 공간을 채우도록 함
        self.original_pdf_widget.segmentHovered.connect(self._handle_segment_hover)
        self.translated_pdf_widget.segmentHovered.connect(self._handle_segment_hover)

        # 드래그&드롭 파일 열기 시그널 연결
        self.original_pdf_widget.fileDropped.connect(self._open_pdf_file_path)
        self.translated_pdf_widget.fileDropped.connect(self._open_pdf_file_path)

        # 줌 동기화 시그널 연결
        self.original_pdf_widget.zoom_in_requested.connect(self.translated_pdf_widget.zoom_in)
        self.original_pdf_widget.zoom_out_requested.connect(self.translated_pdf_widget.zoom_out)
        self.translated_pdf_widget.zoom_in_requested.connect(self.original_pdf_widget.zoom_in)
        self.translated_pdf_widget.zoom_out_requested.connect(self.original_pdf_widget.zoom_out)

        # 링크 클릭 시그널 연결 (원본 뷰에만 적용)
        self.original_pdf_widget.linkClicked.connect(self._handle_link_click)

    def show_status_message(self, message: str, timeout: int = 4000):
        """상태바에 메시지를 표시하고 일정 시간 후 지웁니다."""
        self.status_label.setText(message)
        QTimer.singleShot(timeout, lambda: self.status_label.clear())

    def _setup_scroll_sync(self):
        """두 PDF 뷰의 스크롤바를 동기화합니다."""
        # 스크롤바 가져오기
        self.orig_v_scroll = self.original_pdf_widget.graphics_view.verticalScrollBar()
        self.trans_v_scroll = self.translated_pdf_widget.graphics_view.verticalScrollBar()
        self.orig_h_scroll = self.original_pdf_widget.graphics_view.horizontalScrollBar()
        self.trans_h_scroll = self.translated_pdf_widget.graphics_view.horizontalScrollBar()

        # 시그널 연결
        self.orig_v_scroll.valueChanged.connect(self._sync_v_scroll_from_original)
        self.trans_v_scroll.valueChanged.connect(self._sync_v_scroll_from_translated)
        self.orig_h_scroll.valueChanged.connect(self._sync_h_scroll_from_original)
        self.trans_h_scroll.valueChanged.connect(self._sync_h_scroll_from_translated)

    def _sync_scroll(self, source_scroll, target_scroll, value):
        """한 스크롤바의 움직임을 다른 스크롤바에 비례하여 적용합니다."""
        if self._syncing_scroll:
            return
        self._syncing_scroll = True

        source_range = source_scroll.maximum() - source_scroll.minimum()
        if source_range == 0:
            self._syncing_scroll = False
            return

        proportion = (value - source_scroll.minimum()) / source_range
        target_value = int(target_scroll.minimum() + proportion * (target_scroll.maximum() - target_scroll.minimum()))
        target_scroll.setValue(target_value)

        self._syncing_scroll = False

    def _sync_v_scroll_from_original(self, value):
        self._sync_scroll(self.orig_v_scroll, self.trans_v_scroll, value)

    def _sync_v_scroll_from_translated(self, value):
        self._sync_scroll(self.trans_v_scroll, self.orig_v_scroll, value)

    def _sync_h_scroll_from_original(self, value):
        self._sync_scroll(self.orig_h_scroll, self.trans_h_scroll, value)

    def _sync_h_scroll_from_translated(self, value):
        self._sync_scroll(self.trans_h_scroll, self.orig_h_scroll, value)

    def _create_navigation_bar(self):
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.addStretch(1)
        prev_page_btn = QPushButton("<")
        prev_page_btn.setFixedSize(30, 30)
        prev_page_btn.clicked.connect(self.go_to_prev_page)
        nav_layout.addWidget(prev_page_btn)
        self.page_input = QLineEdit("1")
        self.page_input.setFixedSize(50, 24)
        self.page_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_input.returnPressed.connect(self.go_to_input_page)
        nav_layout.addWidget(self.page_input)
        self.page_count_label = QLabel("/ 1")
        nav_layout.addWidget(self.page_count_label)
        next_page_btn = QPushButton(">")
        next_page_btn.setFixedSize(30, 30)
        next_page_btn.clicked.connect(self.go_to_next_page)
        nav_layout.addWidget(next_page_btn)
        nav_layout.addStretch(1)
        self.main_layout.addLayout(nav_layout)
        self.original_pdf_widget.page_input = self.page_input
        self.translated_pdf_widget.page_input = self.page_input

    def go_to_prev_page(self):
        if hasattr(self, '_current_pdf') and self._current_pdf is not None:
            if self._current_page > 0:
                self._current_page -= 1
                self._show_pdf_page(self._current_page)

    def go_to_next_page(self):
        if hasattr(self, '_current_pdf') and self._current_pdf is not None:
            if self._current_page < self._current_pdf.page_count - 1:
                self._current_page += 1
                self._show_pdf_page(self._current_page)

    def go_to_input_page(self):
        if hasattr(self, '_current_pdf') and self._current_pdf is not None:
            try:
                page_num = int(self.page_input.text()) - 1
                if 0 <= page_num < self._current_pdf.page_count:
                    self._current_page = page_num
                    self._show_pdf_page(self._current_page)
            except Exception:
                pass

    def _load_dummy_data(self):
        original_segments = [
            SegmentViewData(
                segment_id="orig_1",
                text="Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
                rect=(30, 100, 340, 30),
                font_family="Arial", font_size=10, font_color="#555555",
                is_bold=False, is_italic=False, is_highlighted=False
            ),
            SegmentViewData(
                segment_id="orig_2",
                text="Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                rect=(30, 135, 340, 30),
                font_family="Arial", font_size=10, font_color="#555555",
                is_bold=False, is_italic=False, is_highlighted=False
            ),
            SegmentViewData(
                segment_id="orig_3",
                text="Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                rect=(30, 170, 340, 45),
                font_family="Arial", font_size=10, font_color="#555555",
                is_bold=False, is_italic=False, is_highlighted=False
            )
        ]
        translated_segments = [
            SegmentViewData(
                segment_id="trans_1",
                text="이것은 번역된 내용입니다. 스타일과 위치가 유지됩니다.",
                rect=(30, 100, 340, 30),
                font_family="Arial", font_size=10, font_color="#555555",
                is_bold=False, is_italic=False, is_highlighted=False
            ),
            SegmentViewData(
                segment_id="trans_2",
                text="두 번째 문장입니다. 번역은 원본과 1:1이 아닐 수도 있습니다.",
                rect=(30, 135, 340, 30),
                font_family="Arial", font_size=10, font_color="#555555",
                is_bold=False, is_italic=False, is_highlighted=False
            ),
             SegmentViewData(
                segment_id="trans_3",
                text="세 번째 문장입니다. 새로운 번역 세그먼트입니다.",
                rect=(30, 170, 340, 45),
                font_family="Arial", font_size=10, font_color="#555555",
                is_bold=False, is_italic=False, is_highlighted=False
            )
        ]
        dummy_page_view_model = PageDisplayViewModel(
            page_number=1,
            page_width=595,  # 더미 데이터용 페이지 너비 (A4 포인트 기준)
            page_height=842, # 더미 데이터용 페이지 높이
            original_segments_view=original_segments,
            translated_segments_view=translated_segments,
            image_views=[]
        )
        self.display_page(dummy_page_view_model)

    def display_page(self, view_model: PageDisplayViewModel):
        page_width = view_model.page_width
        page_height = view_model.page_height
        # 원본 뷰는 원본 세그먼트와 이미지를 렌더링
        self.original_pdf_widget.render_page(view_model.original_segments_view, view_model.image_views, page_width, page_height)
        # 번역본 뷰는 번역된 세그먼트와 원본 이미지를 렌더링 (이미지는 번역 대상이 아니므로)
        self.translated_pdf_widget.render_page(view_model.translated_segments_view, view_model.image_views, page_width, page_height)
        self.page_input.setText(str(view_model.page_number))
        self._current_view_model = view_model

    def update_highlights(self, highlight_info: HighlightUpdateInfo):
        for segment_id, should_highlight in highlight_info.segments_to_update.items():
            if segment_id.startswith("orig_"):
                self.original_pdf_widget.update_single_segment_highlight(segment_id, should_highlight)
            elif segment_id.startswith("trans_"):
                self.translated_pdf_widget.update_single_segment_highlight(segment_id, should_highlight)

    def _handle_segment_hover(self, view_context: str, segment_id):
        all_orig_ids = self.original_pdf_widget._current_segments_on_display.keys()
        all_trans_ids = self.translated_pdf_widget._current_segments_on_display.keys()
        all_segment_ids = list(all_orig_ids) + list(all_trans_ids)

        segments_to_update = {s_id: False for s_id in all_segment_ids}

        if segment_id:
            segments_to_update[segment_id] = True

            # Dummy mapping logic (e.g., 'orig_1' <-> 'trans_1')
            if view_context == "ORIGINAL" and segment_id.startswith("orig_"):
                # Find corresponding translated segment
                translated_sibling_id = segment_id.replace("orig_", "trans_")
                if translated_sibling_id in all_trans_ids:
                    segments_to_update[translated_sibling_id] = True
            elif view_context == "TRANSLATED" and segment_id.startswith("trans_"):
                # Find corresponding original segment
                original_sibling_id = segment_id.replace("trans_", "orig_")
                if original_sibling_id in all_orig_ids:
                    segments_to_update[original_sibling_id] = True

        self.update_highlights(HighlightUpdateInfo(segments_to_update))

    def _handle_link_click(self, link: str):
        """PDF 뷰의 하이퍼링크 클릭을 처리합니다."""
        if link.startswith("page:"):
            try:
                # 내부 페이지 링크 처리
                page_num = int(link.split(":")[1])
                if hasattr(self, '_current_pdf') and 0 <= page_num < self._current_pdf.page_count:
                    self._show_pdf_page(page_num)
                else:
                    QMessageBox.warning(self, "잘못된 링크", f"문서에 없는 페이지({page_num + 1})로의 링크입니다.")
            except (ValueError, IndexError):
                QMessageBox.warning(self, "잘못된 링크", f"잘못된 내부 링크 형식입니다: {link}")
        else:
            # 외부 URL 링크 처리
            reply = QMessageBox.question(self, "외부 링크 열기",
                                         f"다음 주소를 브라우저에서 여시겠습니까?\n\n{link}",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                         QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(link))

    def toggle_sidebar(self):
        if not self.sidebar:
            self.sidebar = QDockWidget("PDF 목차", self)
            self.sidebar.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
            self.outline_tree = QTreeWidget()
            self.outline_tree.setHeaderLabels(["Title"])
            self.outline_tree.itemClicked.connect(self._on_outline_item_clicked)
            self.sidebar.setWidget(self.outline_tree)
            self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar)
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _load_pdf_outline(self):
        if not hasattr(self, '_current_pdf') or self._current_pdf is None or not self.outline_tree:
            return
        self.outline_tree.clear()
        try:
            flat_toc = self._current_pdf.get_toc()
            if not flat_toc:
                root = QTreeWidgetItem(["(No outline)"])
                self.outline_tree.addTopLevelItem(root)
                return

            def build_tree(flat_toc_list):
                # A dummy root item to hold all top-level items
                root_item = QTreeWidgetItem()
                # A dictionary to keep track of the last item at each level
                parents = {0: root_item}

                for entry in flat_toc_list:
                    # 목차 항목이 리스트 형태이고 최소 3개 이상의 요소를 가지는지 확인
                    if not isinstance(entry, list) or len(entry) < 3:
                        self.show_status_message(f"경고: 목차 항목 형식이 잘못되었습니다: {entry}. 건너뜁니다.", timeout=5000)
                        continue
                    level, title, page = entry[:3]
                    item = QTreeWidgetItem([title])
                    item.setData(0, Qt.UserRole, page)

                    # The parent is at level-1.
                    parent_item = parents.get(level - 1)
                    if parent_item:
                        parent_item.addChild(item)
                    else:
                        # Fallback for malformed TOC where levels are skipped. Add to the root.
                        root_item.addChild(item)
                    # Register the current item as the parent for the next level.
                    parents[level] = item
                return root_item

            root_node = build_tree(flat_toc)
            if root_node:
                # Move children from the dummy root to the actual tree widget
                while root_node.childCount() > 0:
                    child = root_node.takeChild(0)
                    self.outline_tree.addTopLevelItem(child)
        except Exception as e:
            root = QTreeWidgetItem([f"(Outline error: {e})"])
            self.outline_tree.addTopLevelItem(root)

    def _on_outline_item_clicked(self, item, column):
        page = item.data(0, Qt.UserRole)
        if page is not None:
            self._show_pdf_page(page - 1)

    def _open_pdf_file_path(self, file_path):
        try:
            doc = fitz.open(file_path)
            self._current_pdf = doc
            self._current_pdf_path = file_path
            self._current_page = 0
            if self.sidebar:
                self._load_pdf_outline()
            if self.auto_translate:
                asyncio.create_task(self._run_translation_async())
            else:
                self._show_pdf_page(0)
        except Exception as e:
            QMessageBox.critical(self, "PDF 열기 오류", f"PDF 파일을 열 수 없습니다.\n{e}")

    def open_pdf_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "PDF 파일 열기", "", "PDF Files (*.pdf)")
        if not file_path:
            return
        self._open_pdf_file_path(file_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith('.pdf'):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                self._open_pdf_file_path(file_path)
                break
        event.acceptProposedAction()

    def _show_pdf_page(self, page_number):
        if not hasattr(self, '_current_pdf') or self._current_pdf is None:
            return
        if page_number < 0 or page_number >= self._current_pdf.page_count:
            return
        self._current_page = page_number

        # 먼저 원본 뷰를 즉시 렌더링합니다. 번역본 뷰는 원본 텍스트를 임시로 보여줍니다.
        page = self._current_pdf[page_number]
        links = page.get_links()
        page_rect = page.rect
        # 이미지 추출
        image_views = []
        for img_info in page.get_images(full=True):
            xref = img_info[0]
            base_image = self._current_pdf.extract_image(xref)
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
                # 이 텍스트 라인이 링크 영역과 겹치는지 확인
                for link in links:
                    if fitz.Rect(link['from']).intersects(line_rect):
                        if link['kind'] == fitz.LINK_GOTO:
                            line_link_uri = f"page:{link['page']}"
                        elif link['kind'] == fitz.LINK_URI:
                            line_link_uri = link['uri']
                        break  # 이 라인에 대한 링크를 찾았으므로 중단

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
        self.display_page(view_model)
        self.page_input.setText(str(page_number+1))
        self.page_count_label.setText(f"/ {self._current_pdf.page_count}")

        # 자동 번역이 활성화된 경우, 백그라운드에서 번역을 시작합니다.
        if self.auto_translate:
            asyncio.create_task(self._run_translation_async())

    def run_translation(self):
        """
        '번역 실행' 버튼에 연결된 슬롯. 비동기 번역 작업을 시작합니다.
        qasync에 의해 관리되는 이벤트 루프에서 실행됩니다.
        """
        asyncio.create_task(self._run_translation_async())


    async def _run_translation_async(self):
        # 현재 표시된 원본 세그먼트를 가져옵니다.
        original_segments = list(self.original_pdf_widget._current_segments_on_display.values())
        if not original_segments:
            self.show_status_message("번역할 내용이 없습니다.")
            return

        self.progress_bar.setVisible(True)
        try:
            # 1. 번역 실행
            texts_to_translate = [seg.text for seg in original_segments]
            source_lang = self.original_lang_combo.currentData()
            target_lang = self.target_lang_combo.currentData()
            tasks = [google_translate(text, source=source_lang, target=target_lang) for text in texts_to_translate]
            translated_texts = await asyncio.gather(*tasks)
            self._last_translated_texts = {i: t for i, t in enumerate(translated_texts)}

            # 2. 번역된 세그먼트 데이터 생성
            translated_segments = [
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

            # 3. 현재 뷰 모델에서 이미지와 페이지 크기 정보 가져오기
            if not self._current_view_model:
                return
            image_views = self._current_view_model.image_views
            page_width = self._current_view_model.page_width
            page_height = self._current_view_model.page_height

            # 4. 번역본 뷰만 업데이트
            self.translated_pdf_widget.render_page(
                translated_segments,
                image_views,
                page_width,
                page_height
            )
            # 5. 현재 뷰 모델의 번역본 데이터도 업데이트 (일관성 유지)
            self._current_view_model.translated_segments_view = translated_segments

        except Exception as e:
            QMessageBox.critical(self, "번역 오류", f"번역 중 오류가 발생했습니다.\n{e}")
        finally:
            self.progress_bar.setVisible(False)

    def _filter_combo(self, combo, text):
        # 입력값이 코드/이름에 포함된 첫 항목을 선택
        text = text.strip().lower()
        for i in range(combo.count()):
            code = combo.itemData(i)
            name = combo.itemText(i).lower()
            if text == code or text in name:
                combo.setCurrentIndex(i)
                return

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            # 페이지 입력창에 포커스가 있으면 통과
            if self.page_input and self.page_input.hasFocus():
                return super().eventFilter(obj, event)
            if event.key() == Qt.Key_Left:
                self.go_to_prev_page()
                return True
            elif event.key() == Qt.Key_Right:
                self.go_to_next_page()
                return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self.go_to_prev_page()
        elif event.key() == Qt.Key_Right:
            self.go_to_next_page()
        else:
            super().keyPressEvent(event)

import asyncio

import fitz  # PyMuPDF
from PySide6.QtCore import QEvent, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QImage, QPixmap
from PySide6.QtWidgets import QTreeWidget  # QAction removed from here
from PySide6.QtWidgets import QTreeWidgetItem  # QAction removed from here
from PySide6.QtWidgets import (  # QAction removed from here
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.adapters.controllers.pdf_controller import PdfController
from src.adapters.presenters.pdf_presenter import PdfPresenter
from src.common.constants import LANGUAGES
from src.core.use_cases.pdf_page_service import PdfPageService
from src.infrastructure.dtos.app_settings_dtos import AppSettings
from src.infrastructure.dtos.pdf_view_dtos import (
    HighlightUpdateInfo,
    PageDisplayViewModel,
    SegmentViewData,
)
from src.ui.view.settings_dialog import SettingsDialog
from src.ui.widgets.pdf_view_widget import PdfViewWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF 번역기 - 듀얼 뷰어")
        self.setWindowIcon(QIcon("src/ui/resources/asset/icon.ico"))  # 아이콘 경로 설정
        self.setGeometry(100, 100, 800, 600)
        self.auto_translate = False
        self.pdf_preview_dialog = None  # 미리보기 다이얼로그 참조
        self._current_view_model = None
        self.sidebar_visible = False
        self.controller = PdfController()  # 컨트롤러 인스턴스 생성
        # self.outline_tree와 self.sidebar를 항상 생성
        self.outline_tree = QTreeWidget()
        self.outline_tree.setHeaderLabels(["목차"])
        self.outline_tree.itemClicked.connect(self._on_outline_item_clicked)
        self.sidebar = QDockWidget("PDF 목차", self)
        self.sidebar.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.sidebar.setWidget(self.outline_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.sidebar)
        self.sidebar.setVisible(False)  # 기본적으로 숨김
        self.setAcceptDrops(True)  # 드래그&드롭 허용

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QVBoxLayout(self.main_widget)
        self._syncing_scroll = False  # 스크롤 동기화 재귀 방지 플래그

        self._create_toolbar()
        self._create_main_views()
        self._setup_scroll_sync()
        self._create_navigation_bar()
        self._create_status_bar()
        self._load_dummy_data()
        self._create_pdf_thumbnail_widget()
        self._create_menu_bar()

        QApplication.instance().installEventFilter(self)

        self.current_settings = AppSettings()  # 폰트/하이라이트 등 통합 관리

    def _create_status_bar(self):
        """창 하단에 상태바(푸터)를 생성합니다."""
        self.status_bar = self.statusBar()
        self.status_label = QLabel("")
        self.status_bar.addPermanentWidget(
            self.status_label
        )  # 위젯을 우측에 영구적으로 추가

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
        self.original_lang_combo.lineEdit().textEdited.connect(
            lambda text: self._filter_combo(self.original_lang_combo, text)
        )
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
        self.target_lang_combo.lineEdit().textEdited.connect(
            lambda text: self._filter_combo(self.target_lang_combo, text)
        )
        toolbar_layout.addWidget(self.target_lang_combo)
        self.translate_btn = QPushButton("번역 실행")
        self.translate_btn.setStyleSheet("background-color: #c0e0c0;")
        self.translate_btn.clicked.connect(self.run_translation)
        toolbar_layout.addWidget(self.translate_btn)
        # 계속 번역 체크박스
        self.auto_translate_checkbox = QCheckBox("계속 번역")
        self.auto_translate_checkbox.stateChanged.connect(
            self._on_auto_translate_changed
        )
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
        self.progress_bar.setRange(0, 0)  # Indeterminate mode
        self.progress_bar.setVisible(False)  # Initially hidden
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

        self.main_layout.addLayout(
            view_area_layout, 1
        )  # stretch factor를 1로 설정하여 이 레이아웃이 수직 공간을 채우도록 함
        self.original_pdf_widget.segmentHovered.connect(self._handle_segment_hover)
        self.translated_pdf_widget.segmentHovered.connect(self._handle_segment_hover)

        # 드래그&드롭 파일 열기 시그널 연결
        self.original_pdf_widget.fileDropped.connect(self._open_pdf_file_path)
        self.translated_pdf_widget.fileDropped.connect(self._open_pdf_file_path)

        # 줌 동기화 시그널 연결
        self.original_pdf_widget.zoom_in_requested.connect(
            self.translated_pdf_widget.zoom_in
        )
        self.original_pdf_widget.zoom_out_requested.connect(
            self.translated_pdf_widget.zoom_out
        )
        self.translated_pdf_widget.zoom_in_requested.connect(
            self.original_pdf_widget.zoom_in
        )
        self.translated_pdf_widget.zoom_out_requested.connect(
            self.original_pdf_widget.zoom_out
        )

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
        self.trans_v_scroll = (
            self.translated_pdf_widget.graphics_view.verticalScrollBar()
        )
        self.orig_h_scroll = (
            self.original_pdf_widget.graphics_view.horizontalScrollBar()
        )
        self.trans_h_scroll = (
            self.translated_pdf_widget.graphics_view.horizontalScrollBar()
        )

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
        target_value = int(
            target_scroll.minimum()
            + proportion * (target_scroll.maximum() - target_scroll.minimum())
        )
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
        if hasattr(self, "_current_pdf") and self._current_pdf is not None:
            if self._current_page > 0:
                self._current_page -= 1
                self._show_pdf_page(self._current_page)

    def go_to_next_page(self):
        if hasattr(self, "_current_pdf") and self._current_pdf is not None:
            if self._current_page < self._current_pdf.page_count - 1:
                self._current_page += 1
                self._show_pdf_page(self._current_page)

    def go_to_input_page(self):
        if hasattr(self, "_current_pdf") and self._current_pdf is not None:
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
                font_family="Arial",
                font_size=10,
                font_color="#555555",
                is_bold=False,
                is_italic=False,
                is_highlighted=False,
            ),
            SegmentViewData(
                segment_id="orig_2",
                text="Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                rect=(30, 135, 340, 30),
                font_family="Arial",
                font_size=10,
                font_color="#555555",
                is_bold=False,
                is_italic=False,
                is_highlighted=False,
            ),
            SegmentViewData(
                segment_id="orig_3",
                text="Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
                rect=(30, 170, 340, 45),
                font_family="Arial",
                font_size=10,
                font_color="#555555",
                is_bold=False,
                is_italic=False,
                is_highlighted=False,
            ),
        ]
        translated_segments = [
            SegmentViewData(
                segment_id="trans_1",
                text="이것은 번역된 내용입니다. 스타일과 위치가 유지됩니다.",
                rect=(30, 100, 340, 30),
                font_family="Arial",
                font_size=10,
                font_color="#555555",
                is_bold=False,
                is_italic=False,
                is_highlighted=False,
            ),
            SegmentViewData(
                segment_id="trans_2",
                text="두 번째 문장입니다. 번역은 원본과 1:1이 아닐 수도 있습니다.",
                rect=(30, 135, 340, 30),
                font_family="Arial",
                font_size=10,
                font_color="#555555",
                is_bold=False,
                is_italic=False,
                is_highlighted=False,
            ),
            SegmentViewData(
                segment_id="trans_3",
                text="세 번째 문장입니다. 새로운 번역 세그먼트입니다.",
                rect=(30, 170, 340, 45),
                font_family="Arial",
                font_size=10,
                font_color="#555555",
                is_bold=False,
                is_italic=False,
                is_highlighted=False,
            ),
        ]
        dummy_page_view_model = PageDisplayViewModel(
            page_number=1,
            page_width=595,  # 더미 데이터용 페이지 너비 (A4 포인트 기준)
            page_height=842,  # 더미 데이터용 페이지 높이
            original_segments_view=original_segments,
            translated_segments_view=translated_segments,
            image_views=[],
        )
        self.display_page(dummy_page_view_model)

    def display_page(self, view_model):
        # 프레젠터를 통해 UI 데이터 추출
        page_data = PdfPresenter.present_page(view_model)

        page_width = page_data["page_width"]
        page_height = page_data["page_height"]

        # 지연 로딩을 위해 pdf_doc 객체를 전달
        pdf_doc = (
            self._current_pdf
            if hasattr(self, "_current_pdf") and self._current_pdf
            else None
        )

        self.original_pdf_widget.render_page(
            page_data["original_segments"],
            page_data["image_views"],
            page_width,
            page_height,
            pdf_doc,
        )
        self.translated_pdf_widget.render_page(
            page_data["translated_segments"],
            page_data["image_views"],
            page_width,
            page_height,
            pdf_doc,
        )
        self.page_input.setText(str(page_data["page_number"]))
        self._current_view_model = view_model

    def update_highlights(self, highlight_info):
        # 프레젠터를 통해 하이라이트 데이터 추출
        segments_to_update = PdfPresenter.present_highlights(highlight_info)
        for segment_id, should_highlight in segments_to_update.items():
            if segment_id.startswith("orig_"):
                self.original_pdf_widget.update_single_segment_highlight(
                    segment_id, should_highlight
                )
            elif segment_id.startswith("trans_"):
                self.translated_pdf_widget.update_single_segment_highlight(
                    segment_id, should_highlight
                )

    def _handle_segment_hover(self, view_context: str, segment_id):
        all_orig_ids = self.original_pdf_widget._current_segments_on_display.keys()
        all_trans_ids = self.translated_pdf_widget._current_segments_on_display.keys()
        all_segment_ids = list(all_orig_ids) + list(all_trans_ids)

        # 비즈니스 로직 분리: PdfPageService 사용
        segments_to_update = PdfPageService.update_highlights(
            all_segment_ids, segment_id
        )

        # 번역/원본 동기화 로직은 기존대로 유지
        if segment_id:
            if view_context == "ORIGINAL" and segment_id.startswith("orig_"):
                translated_sibling_id = segment_id.replace("orig_", "trans_")
                if translated_sibling_id in all_trans_ids:
                    segments_to_update[translated_sibling_id] = True
            elif view_context == "TRANSLATED" and segment_id.startswith("trans_"):
                original_sibling_id = segment_id.replace("trans_", "orig_")
                if original_sibling_id in all_orig_ids:
                    segments_to_update[original_sibling_id] = True

        self.update_highlights(HighlightUpdateInfo(segments_to_update))

    def _handle_link_click(self, link: str):
        """PDF 뷰의 하이퍼링크 클릭을 처리합니다."""
        if not link:
            return

        if link.startswith("page:"):
            try:
                # 내부 페이지 링크 처리
                page_num = int(link.split(":")[1])
                if (
                    hasattr(self, "_current_pdf")
                    and 0 <= page_num < self._current_pdf.page_count
                ):
                    self._show_pdf_page(page_num)
                else:
                    self.show_status_message(
                        f"잘못된 링크: 문서에 없는 페이지({page_num + 1})입니다."
                    )
            except (ValueError, IndexError):
                self.show_status_message(f"잘못된 링크 형식: {link}")
        elif link.startswith("file:"):
            file_path = link[5:]
            reply = QMessageBox.question(
                self,
                "파일 실행",
                f"다음 파일을 여시겠습니까?\n\n{file_path}\n\n(주의: 알 수 없는 파일을 열면 위험할 수 있습니다.)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(file_path)):
                    QMessageBox.warning(
                        self, "파일 열기 실패", f"파일을 열 수 없습니다: {file_path}"
                    )
        elif link.startswith("name:"):
            dest_name = link[5:]
            if hasattr(self, "_current_pdf") and self._current_pdf:
                try:
                    page_num = self._current_pdf.get_page_number_from_name(dest_name)
                    if page_num != -1:
                        self._show_pdf_page(page_num)
                    else:
                        QMessageBox.warning(
                            self,
                            "잘못된 링크",
                            f"문서에서 '{dest_name}' 목적지를 찾을 수 없습니다.",
                        )
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "링크 오류",
                        f"명명된 목적지 링크 처리 중 오류가 발생했습니다: {e}",
                    )
        else:
            # 외부 URL 링크 처리
            reply = QMessageBox.question(
                self,
                "외부 링크 열기",
                f"다음 주소를 브라우저에서 여시겠습니까?\n\n{link}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                QDesktopServices.openUrl(QUrl(link))

    def toggle_sidebar(self):
        # 단순히 show/hide만 담당
        self.sidebar.setVisible(not self.sidebar.isVisible())
        self._update_thumbnail_position()

    def _create_pdf_thumbnail_widget(self):
        # 썸네일을 절대 좌표로 배치, 사이드바 열릴 때 위치 보정
        self.thumbnail_label = QLabel(self)
        self.thumbnail_label.setFixedSize(120, 160)
        self.thumbnail_label.setStyleSheet("border: 1px solid #aaa; background: #eee;")
        self.thumbnail_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom
        )
        self.thumbnail_label.setVisible(False)
        self.thumbnail_label.mousePressEvent = self._show_pdf_modal
        self._update_thumbnail_position()

    def _update_thumbnail_position(self):
        x_offset = 10
        if self.sidebar and self.sidebar.isVisible():
            x_offset += self.sidebar.width()
        y_offset = self.height() - self.thumbnail_label.height() - 10
        self.thumbnail_label.move(x_offset, y_offset)

    def _on_mainwindow_resize(self, event):
        self._update_thumbnail_position()
        return super().resizeEvent(event)

    def _load_pdf_outline(self):
        if (
            not hasattr(self, "_current_pdf")
            or self._current_pdf is None
            or not self.outline_tree
        ):
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
                        self.show_status_message(
                            f"경고: 목차 항목 형식이 잘못되었습니다: {entry}. 건너뜁니다.",
                            timeout=5000,
                        )
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
            self.controller.open_pdf(file_path)
            self._current_pdf = self.controller.pdf_doc
            self._current_pdf_path = file_path
            self._current_page = 0
            if self.sidebar:
                self._load_pdf_outline()
            if self.auto_translate:
                import asyncio

                asyncio.create_task(self._run_translation_async())
            else:
                self._show_pdf_page(0)
        except Exception as e:
            QMessageBox.critical(
                self, "PDF 열기 오류", f"PDF 파일을 열 수 없습니다.\n{e}"
            )

    def open_pdf_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "PDF 파일 열기", "", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        self._open_pdf_file_path(file_path)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".pdf"):
                self._open_pdf_file_path(file_path)
                break
        event.acceptProposedAction()

    def _show_pdf_page(self, page_number):
        if not hasattr(self, "_current_pdf") or self._current_pdf is None:
            return
        if page_number < 0 or page_number >= self._current_pdf.page_count:
            return
        self._current_page = page_number
        view_model = self.controller.get_page_view_model(page_number)
        self.display_page(view_model)
        self.page_input.setText(str(page_number + 1))
        self.page_count_label.setText(f"/ {self._current_pdf.page_count}")
        self._update_pdf_thumbnail()
        self._update_thumbnail_position()
        if self.sidebar:
            self._load_pdf_outline()
        if self.auto_translate:
            import asyncio

            asyncio.create_task(self._run_translation_async())

        self._update_pdf_preview_content()  # 미리보기 창 내용 업데이트

    def run_translation(self):
        """
        '번역 실행' 버튼에 연결된 슬롯. 비동기 번역 작업을 시작합니다.
        qasync에 의해 관리되는 이벤트 루프에서 실행됩니다.
        """
        asyncio.create_task(self._run_translation_async())

    async def _run_translation_async(self):
        if not self.controller.view_model:
            self.show_status_message("번역할 내용이 없습니다.")
            return
        self.progress_bar.setVisible(True)
        try:
            source_lang = self.original_lang_combo.currentData()
            target_lang = self.target_lang_combo.currentData()
            translated_segments = await self.controller.translate_current_page(
                source_lang, target_lang
            )
            if not translated_segments:
                return
            image_views = self.controller.view_model.image_views
            page_width = self.controller.view_model.page_width
            page_height = self.controller.view_model.page_height
            pdf_doc = self._current_pdf if hasattr(self, "_current_pdf") else None

            # 원본 PDF 뷰의 현재 변환(확대/축소 및 이동) 상태를 가져옵니다.
            # 이를 통해 번역된 뷰가 원본 뷰와 동일한 시각적 상태를 유지하도록 합니다.
            original_view_transform = self.original_pdf_widget.graphics_view.transform()

            self.translated_pdf_widget.render_page(
                translated_segments, image_views, page_width, page_height, pdf_doc
            )
            # 번역된 뷰에 원본 뷰의 변환 상태를 적용합니다.
            self.translated_pdf_widget.graphics_view.setTransform(
                original_view_transform
            )

            self.controller.view_model.translated_segments_view = translated_segments
        except Exception as e:
            QMessageBox.critical(
                self, "번역 오류", f"번역 중 오류가 발생했습니다.\n{e}"
            )
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

    def _update_pdf_thumbnail(self):
        if not hasattr(self, "_current_pdf") or self._current_pdf is None:
            self.thumbnail_label.setVisible(False)
            return
        try:
            # 현재 페이지의 썸네일을 표시하도록 수정
            page = self._current_pdf[self._current_page]
            pix = page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
            img = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888,
            )
            pixmap = QPixmap.fromImage(img)
            self.thumbnail_label.setPixmap(
                pixmap.scaled(
                    self.thumbnail_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            self.thumbnail_label.setVisible(True)
            self._update_thumbnail_position()
        except Exception:
            self.thumbnail_label.setVisible(False)

    def _on_preview_closed(self):
        """미리보기 다이얼로그가 닫힐 때 참조를 정리하는 슬롯."""
        self.pdf_preview_dialog = None

    def _update_pdf_preview_content(self):
        """미리보기 다이얼로그가 열려있으면 내용을 업데이트합니다."""
        # isVisible() 체크를 제거하여, 다이얼로그가 아직 화면에 표시되기 전(처음 생성 시)에도 콘텐츠가 채워지도록 합니다.
        if (
            not self.pdf_preview_dialog
            or not hasattr(self, "_current_pdf")
            or self._current_pdf is None
        ):
            return

        scroll_area = self.pdf_preview_dialog.findChild(QScrollArea)
        if not scroll_area:
            return
        container = scroll_area.widget()
        if not container:
            return
        layout = container.layout()

        # 기존 위젯들 제거
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # 새로운 페이지 이미지들로 채우기
        start = self._current_page
        end = min(self._current_page + 10, self._current_pdf.page_count)
        for i in range(start, end):
            page = self._current_pdf[i]
            pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
            img = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format_RGBA8888 if pix.alpha else QImage.Format_RGB888,
            )
            label = QLabel()
            label.setPixmap(QPixmap.fromImage(img))
            layout.addWidget(label)

    def _show_pdf_modal(self, event):
        if not hasattr(self, "_current_pdf") or self._current_pdf is None:
            return

        # 다이얼로그가 없으면 새로 생성
        if self.pdf_preview_dialog is None:
            self.pdf_preview_dialog = QDialog(self)
            self.pdf_preview_dialog.setWindowTitle("원본 PDF 전체 보기")
            self.pdf_preview_dialog.resize(800, 1000)

            dialog_layout = QVBoxLayout(self.pdf_preview_dialog)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            dialog_layout.addWidget(scroll)

            container = QWidget()
            QVBoxLayout(container)
            scroll.setWidget(container)

            self.pdf_preview_dialog.finished.connect(self._on_preview_closed)

        self._update_pdf_preview_content()
        self.pdf_preview_dialog.show()
        self.pdf_preview_dialog.raise_()
        self.pdf_preview_dialog.activateWindow()

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        settings_menu = menu_bar.addMenu("설정(&S)")
        settings_action = QAction("설정 열기", self)
        settings_action.triggered.connect(self._open_settings_dialog)
        settings_menu.addAction(settings_action)

    def _open_settings_dialog(self):
        dialog = SettingsDialog(self.current_settings, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self.current_settings = dialog.get_settings()
            self.apply_font_to_views(self.current_settings.font)
            self.apply_highlight_color_to_views(self.current_settings.highlight_color)

    def apply_highlight_color_to_views(self, color):
        if hasattr(self, "original_pdf_widget"):
            self.original_pdf_widget.set_highlight_color(color)
        if hasattr(self, "translated_pdf_widget"):
            self.translated_pdf_widget.set_highlight_color(color)

    def apply_font_to_views(self, font):
        if hasattr(self, "original_pdf_widget"):
            self.original_pdf_widget.set_font(font)
        if hasattr(self, "translated_pdf_widget"):
            self.translated_pdf_widget.set_font(font)

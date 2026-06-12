from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QSplitter, QAbstractItemView, QLabel, QTabWidget)
from PyQt5.QtCore import pyqtSignal

class DataPanel(QWidget):
    urlSubmitted = pyqtSignal(str)
    ruleSelected = pyqtSignal(str)
    pageDoubleClicked = pyqtSignal(str)
    detailDoubleClicked = pyqtSignal(str)
    clearPagesRequested = pyqtSignal()
    clearDetailsRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        url_bar = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("输入网址...")
        self.btn_analyze = QPushButton("分析")
        url_bar.addWidget(self.url_input)
        url_bar.addWidget(self.btn_analyze)
        layout.addLayout(url_bar)
        rule_bar = QHBoxLayout()
        self.rule_selector = QComboBox()
        self.rule_selector.addItem("选择规则...")
        self.btn_new_rule = QPushButton("新建规则")
        rule_bar.addWidget(self.rule_selector)
        rule_bar.addWidget(self.btn_new_rule)
        layout.addLayout(rule_bar)
        splitter = QSplitter()

        # Page list (top)
        page_container = QWidget()
        page_layout = QVBoxLayout(page_container)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_toolbar = QHBoxLayout()
        page_toolbar.addWidget(QLabel("分页列表"))
        self.btn_clear_pages = QPushButton("清空")
        self.btn_delete_pages = QPushButton("删除选中")
        page_toolbar.addStretch()
        page_toolbar.addWidget(self.btn_clear_pages)
        page_toolbar.addWidget(self.btn_delete_pages)
        page_layout.addLayout(page_toolbar)
        self.page_list = QListWidget()
        self.page_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        page_layout.addWidget(self.page_list)
        self.btn_delete_pages.clicked.connect(self._delete_selected_pages)
        self.btn_clear_pages.clicked.connect(lambda: self.clearPagesRequested.emit())

        # Bottom: tab widget with 详情, 图片, 视频
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        self.tabs.addTab(self._make_detail_tab(), "详情")
        self.tabs.addTab(self._make_media_tab("image"), "图片")
        self.tabs.addTab(self._make_media_tab("video"), "视频")
        self.tabs.addTab(self._make_m3u8_tab(), "M3U8")
        detail_layout.addWidget(self.tabs)

        splitter.addWidget(page_container)
        splitter.addWidget(detail_container)
        layout.addWidget(splitter)
        self.url_input.returnPressed.connect(lambda: self.urlSubmitted.emit(self.url_input.text()))
        self.page_list.itemDoubleClicked.connect(lambda item: self.pageDoubleClicked.emit(item.data(256)))
        self.detail_list.itemDoubleClicked.connect(lambda item: self.detailDoubleClicked.emit(item.data(256)))

    def _make_detail_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        tb = QHBoxLayout()
        self.btn_clear_details = QPushButton("清空")
        self.btn_delete_details = QPushButton("删除选中")
        tb.addStretch()
        tb.addWidget(self.btn_clear_details)
        tb.addWidget(self.btn_delete_details)
        l.addLayout(tb)
        self.detail_list = QListWidget()
        self.detail_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        l.addWidget(self.detail_list)
        self.btn_delete_details.clicked.connect(self._delete_selected_details)
        self.btn_clear_details.clicked.connect(lambda: self.clearDetailsRequested.emit())
        return w

    def _make_media_tab(self, media_type):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        tb = QHBoxLayout()
        count_label = QLabel("0 个文件")
        btn_clear = QPushButton("清空")
        btn_dl = QPushButton("下载全部")
        tb.addWidget(count_label)
        tb.addStretch()
        tb.addWidget(btn_clear)
        tb.addWidget(btn_dl)
        l.addLayout(tb)
        ml = QListWidget()
        ml.setSelectionMode(QAbstractItemView.ExtendedSelection)
        l.addWidget(ml)
        setattr(self, f'_media_list_{media_type}', ml)
        setattr(self, f'_media_label_{media_type}', count_label)
        btn_clear.clicked.connect(lambda: (ml.clear(), count_label.setText("0 个文件")))
        btn_dl.clicked.connect(lambda: self._download_media_tab(media_type))
        return w

    def _make_m3u8_tab(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        self.m3u8_list = QListWidget()
        l.addWidget(self.m3u8_list)
        return w

    def add_m3u8_task(self, task_id: str, title: str):
        item = QListWidgetItem(f"[等待] {title[:50]}")
        item.setData(256, task_id)
        self.m3u8_list.insertItem(0, item)
        return item

    def update_m3u8_task(self, task_id: str, status: str, detail: str = ""):
        for i in range(self.m3u8_list.count()):
            item = self.m3u8_list.item(i)
            if item.data(256) == task_id:
                item.setText(f"[{status}] {detail[:80]}")
                break

    def _download_media_tab(self, media_type):
        ml = getattr(self, f'_media_list_{media_type}')
        urls = []
        for i in range(ml.count()):
            url = ml.item(i).data(256)
            if url:
                urls.append({"url": url, "type": media_type})
        if urls:
            from PyQt5.QtCore import QObject
            getattr(self, f'_download_{media_type}_requested', lambda: None)()
        # We'll connect this from main_window

    def add_media_item(self, media_type, url, text=""):
        ml = getattr(self, f'_media_list_{media_type}')
        item = QListWidgetItem(text or url)
        item.setData(256, url)
        ml.addItem(item)
        label = getattr(self, f'_media_label_{media_type}')
        label.setText(f"{ml.count()} 个文件")

    def _delete_selected_pages(self):
        for item in self.page_list.selectedItems():
            self.page_list.takeItem(self.page_list.row(item))

    def _delete_selected_details(self):
        for item in self.detail_list.selectedItems():
            self.detail_list.takeItem(self.detail_list.row(item))

    def add_page_item(self, text: str, url: str):
        item = QListWidgetItem(text)
        item.setData(256, url)
        self.page_list.addItem(item)

    def add_detail_item(self, text: str, url: str):
        item = QListWidgetItem(text)
        item.setData(256, url)
        self.detail_list.addItem(item)

    def clear_pages(self):
        self.page_list.clear()

    def clear_details(self):
        self.detail_list.clear()
        for t in ('image', 'video'):
            getattr(self, f'_media_list_{t}').clear()
            getattr(self, f'_media_label_{t}').setText("0 个文件")

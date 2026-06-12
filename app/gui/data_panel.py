from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QSplitter, QAbstractItemView, QLabel)
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

        # Page list (top) with toolbar
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

        # Detail list (bottom)
        detail_container = QWidget()
        detail_layout = QVBoxLayout(detail_container)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_toolbar = QHBoxLayout()
        detail_toolbar.addWidget(QLabel("详情列表"))
        self.btn_clear_details = QPushButton("清空")
        self.btn_delete_details = QPushButton("删除选中")
        detail_toolbar.addStretch()
        detail_toolbar.addWidget(self.btn_clear_details)
        detail_toolbar.addWidget(self.btn_delete_details)
        detail_layout.addLayout(detail_toolbar)
        self.detail_list = QListWidget()
        self.detail_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        detail_layout.addWidget(self.detail_list)
        self.btn_delete_details.clicked.connect(self._delete_selected_details)
        self.btn_clear_details.clicked.connect(lambda: self.clearDetailsRequested.emit())

        splitter.addWidget(page_container)
        splitter.addWidget(detail_container)
        layout.addWidget(splitter)
        self.url_input.returnPressed.connect(lambda: self.urlSubmitted.emit(self.url_input.text()))
        self.page_list.itemDoubleClicked.connect(lambda item: self.pageDoubleClicked.emit(item.data(256)))
        self.detail_list.itemDoubleClicked.connect(lambda item: self.detailDoubleClicked.emit(item.data(256)))

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

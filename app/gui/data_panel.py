from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QListWidgetItem,
    QComboBox, QSplitter)
from PyQt5.QtCore import pyqtSignal

class DataPanel(QWidget):
    urlSubmitted = pyqtSignal(str)
    ruleSelected = pyqtSignal(str)
    pageDoubleClicked = pyqtSignal(str)
    detailDoubleClicked = pyqtSignal(str)

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
        self.page_list = QListWidget()
        self.detail_list = QListWidget()
        splitter.addWidget(self.page_list)
        splitter.addWidget(self.detail_list)
        layout.addWidget(splitter)
        self.url_input.returnPressed.connect(lambda: self.urlSubmitted.emit(self.url_input.text()))
        self.btn_analyze.clicked.connect(lambda: self.urlSubmitted.emit(self.url_input.text()))
        self.page_list.itemDoubleClicked.connect(lambda item: self.pageDoubleClicked.emit(item.data(256)))
        self.detail_list.itemDoubleClicked.connect(lambda item: self.detailDoubleClicked.emit(item.data(256)))

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

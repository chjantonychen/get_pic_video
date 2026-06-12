from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl

class BrowserPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        nav = QHBoxLayout()
        self.btn_back = QPushButton("◀")
        self.btn_forward = QPushButton("▶")
        self.btn_refresh = QPushButton("🔄")
        self.btn_pick = QPushButton("点选模式")
        self.btn_pick.setCheckable(True)
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_forward)
        nav.addWidget(self.btn_refresh)
        nav.addStretch()
        nav.addWidget(self.btn_pick)
        layout.addLayout(nav)
        self.webview = QWebEngineView()
        self.webview.setUrl(QUrl("about:blank"))
        layout.addWidget(self.webview)
        self.btn_back.clicked.connect(self.webview.back)
        self.btn_forward.clicked.connect(self.webview.forward)
        self.btn_refresh.clicked.connect(self.webview.reload)

    def navigate(self, url):
        self.webview.setUrl(QUrl(url))

    def page(self):
        return self.webview.page()

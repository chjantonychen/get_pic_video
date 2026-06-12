from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QHBoxLayout
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEngineProfile
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
        self.btn_pick = QPushButton("开启点选")
        self.btn_pick.setCheckable(True)
        nav.addWidget(self.btn_back)
        nav.addWidget(self.btn_forward)
        nav.addWidget(self.btn_refresh)
        nav.addStretch()
        nav.addWidget(self.btn_pick)
        layout.addLayout(nav)
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        # Allow loading mixed content (HTTP images on HTTPS pages)
        profile.setHttpAcceptLanguage("zh-CN,zh;q=0.9,en;q=0.8")
        self.webview = QWebEngineView()
        s = self.webview.settings()
        s.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        s.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        s.setAttribute(QWebEngineSettings.AutoLoadImages, True)
        s.setAttribute(QWebEngineSettings.ErrorPageEnabled, False)
        s.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.WebGLEnabled, True)
        s.setAttribute(QWebEngineSettings.Accelerated2dCanvasEnabled, True)
        s.setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        s.setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        self.webview.setUrl(QUrl("about:blank"))
        layout.addWidget(self.webview)
        self.btn_back.clicked.connect(self.webview.back)
        self.btn_forward.clicked.connect(self.webview.forward)
        self.btn_refresh.clicked.connect(self.webview.reload)

    def navigate(self, url):
        self.webview.setUrl(QUrl(url))

    def page(self):
        return self.webview.page()

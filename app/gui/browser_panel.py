from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class BrowserPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("浏览器面板 (WebEngine)"))

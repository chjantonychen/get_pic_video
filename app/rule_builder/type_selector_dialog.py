from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

ELEMENT_TYPES = ["分页链接", "详情链接", "图片容器", "视频容器", "下一页按钮"]


class TypeSelectorDialog(QDialog):
    def __init__(self, selector: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择元素类型")
        self.selected_type = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"选择器: {selector}"))
        layout.addWidget(QLabel("这个元素属于什么类型？"))
        for t in ELEMENT_TYPES:
            btn = QPushButton(t)
            btn.clicked.connect(lambda checked, t=t: self._pick(t))
            layout.addWidget(btn)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _pick(self, t: str):
        self.selected_type = t
        self.accept()

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QPushButton, QLabel

class BottomBar(QWidget):
    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        self.progress = QProgressBar()
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        self.log_label = QLabel("就绪")
        layout.addWidget(self.progress, 1)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.log_label)

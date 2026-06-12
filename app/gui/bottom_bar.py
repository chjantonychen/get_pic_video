from PyQt5.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QPushButton, QTextEdit
from PyQt5.QtCore import pyqtSignal
import time

class BottomBar(QWidget):
    pauseRequested = pyqtSignal()
    cancelRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(300)
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(60)
        self.log.setMaximumWidth(400)
        layout.addWidget(self.progress)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.log, 1)
        self.btn_pause.clicked.connect(lambda: self.pauseRequested.emit())
        self.btn_cancel.clicked.connect(lambda: self.cancelRequested.emit())

    def log_message(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")

    def update_progress(self, current: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

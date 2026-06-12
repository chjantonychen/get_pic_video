from PyQt5.QtWidgets import QWidget, QHBoxLayout, QProgressBar, QPushButton, QTextEdit, QLabel
from PyQt5.QtCore import pyqtSignal
import time

class BottomBar(QWidget):
    pauseRequested = pyqtSignal()
    cancelRequested = pyqtSignal()
    downloadRequested = pyqtSignal()
    autoDownloadRequested = pyqtSignal()
    autoPauseRequested = pyqtSignal()
    autoStopRequested = pyqtSignal()

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(150)
        self.pending_label = QLabel("待下载: 0")
        self.pending_label.setMinimumWidth(70)
        self.btn_auto = QPushButton("自动下载")
        self.btn_auto_pause = QPushButton("暂停自动")
        self.btn_auto_stop = QPushButton("停止自动")
        self.btn_download = QPushButton("开始下载")
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(60)
        self.log.setMaximumWidth(300)
        layout.addWidget(self.progress)
        layout.addWidget(self.pending_label)
        layout.addWidget(self.btn_auto)
        layout.addWidget(self.btn_auto_pause)
        layout.addWidget(self.btn_auto_stop)
        layout.addWidget(self.btn_download)
        layout.addWidget(self.btn_pause)
        layout.addWidget(self.btn_cancel)
        layout.addWidget(self.log, 1)
        self.btn_auto.clicked.connect(lambda: self.autoDownloadRequested.emit())
        self.btn_auto_pause.clicked.connect(lambda: self.autoPauseRequested.emit())
        self.btn_auto_stop.clicked.connect(lambda: self.autoStopRequested.emit())
        self.btn_download.clicked.connect(lambda: self.downloadRequested.emit())
        self.btn_pause.clicked.connect(lambda: self.pauseRequested.emit())
        self.btn_cancel.clicked.connect(lambda: self.cancelRequested.emit())

    def log_message(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")

    def update_progress(self, current: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def set_pending_count(self, count: int):
        self.pending_label.setText(f"待下载: {count}")

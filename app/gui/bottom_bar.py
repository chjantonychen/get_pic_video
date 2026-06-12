from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QPushButton, QTextEdit, QLabel, QGroupBox
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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 2, 5, 2)
        main_layout.setSpacing(2)

        # Row 1: progress + pending + auto group + manual group
        row1 = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(150)
        self.pending_label = QLabel("待下载: 0")
        self.pending_label.setMinimumWidth(70)

        # Auto-download group box
        auto_group = QGroupBox("自动下载图片")
        auto_layout = QHBoxLayout(auto_group)
        auto_layout.setContentsMargins(3, 0, 3, 0)
        self.btn_auto = QPushButton("自动下载")
        self.btn_auto_pause = QPushButton("暂停自动")
        self.btn_auto_stop = QPushButton("停止自动")
        auto_layout.addWidget(self.btn_auto)
        auto_layout.addWidget(self.btn_auto_pause)
        auto_layout.addWidget(self.btn_auto_stop)

        # Manual download group box
        manual_group = QGroupBox("手动下载图片")
        manual_layout = QHBoxLayout(manual_group)
        manual_layout.setContentsMargins(3, 0, 3, 0)
        self.btn_download = QPushButton("开始下载")
        self.btn_pause = QPushButton("暂停")
        self.btn_cancel = QPushButton("取消")
        manual_layout.addWidget(self.btn_download)
        manual_layout.addWidget(self.btn_pause)
        manual_layout.addWidget(self.btn_cancel)

        row1.addWidget(self.progress)
        row1.addWidget(self.pending_label)
        row1.addWidget(auto_group)
        row1.addStretch()
        row1.addWidget(manual_group)

        # Row 2: log (full width)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFixedHeight(120)

        main_layout.addLayout(row1)
        main_layout.addWidget(self.log)

        self.btn_auto.clicked.connect(lambda: self.autoDownloadRequested.emit())
        self.btn_auto_pause.clicked.connect(lambda: self.autoPauseRequested.emit())
        self.btn_auto_stop.clicked.connect(lambda: self.autoStopRequested.emit())
        self.btn_download.clicked.connect(lambda: self.downloadRequested.emit())
        self.btn_pause.clicked.connect(lambda: self.pauseRequested.emit())
        self.btn_cancel.clicked.connect(lambda: self.cancelRequested.emit())

    def log_message(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log.append(f"[{ts}] {msg}")
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def update_progress(self, current: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def set_pending_count(self, count: int):
        self.pending_label.setText(f"待下载: {count}")

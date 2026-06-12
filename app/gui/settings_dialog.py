from PyQt5.QtWidgets import (QDialog, QFormLayout, QSpinBox,
    QLineEdit, QCheckBox, QDoubleSpinBox, QTextEdit, QDialogButtonBox,
    QTabWidget, QWidget, QVBoxLayout)

class SettingsDialog(QDialog):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self._config = config
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_download_tab(), "下载")
        tabs.addTab(self._build_anti_crawl_tab(), "反爬")
        tabs.addTab(self._build_browser_tab(), "浏览器")
        layout.addWidget(tabs)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_download_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self.spin_threads = QSpinBox(); self.spin_threads.setRange(1, 50)
        self.spin_threads.setValue(self._config.get("download_threads", 10))
        self.edit_path = QLineEdit(self._config.get("save_path", ""))
        self.spin_speed = QDoubleSpinBox(); self.spin_speed.setRange(0, 100)
        self.spin_speed.setValue(self._config.get("speed_limit", 0))
        self.chk_resume = QCheckBox(); self.chk_resume.setChecked(self._config.get("resume_enabled", True))
        self.edit_ffmpeg = QLineEdit(self._config.get("ffmpeg_path", "ffmpeg"))
        f.addRow("线程数:", self.spin_threads)
        f.addRow("保存路径:", self.edit_path)
        f.addRow("限速 (MB/s, 0=不限):", self.spin_speed)
        f.addRow("断点续传:", self.chk_resume)
        f.addRow("ffmpeg 路径:", self.edit_ffmpeg)
        return w

    def _build_anti_crawl_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self.spin_delay_min = QDoubleSpinBox(); self.spin_delay_min.setRange(0, 60)
        self.spin_delay_min.setValue(self._config.get("delay_min", 1))
        self.spin_delay_max = QDoubleSpinBox(); self.spin_delay_max.setRange(0, 60)
        self.spin_delay_max.setValue(self._config.get("delay_max", 3))
        self.chk_ua = QCheckBox(); self.chk_ua.setChecked(self._config.get("random_ua", True))
        self.edit_proxies = QTextEdit()
        self.edit_proxies.setPlainText("\n".join(self._config.get("proxy_list", [])))
        f.addRow("最小延迟 (秒):", self.spin_delay_min)
        f.addRow("最大延迟 (秒):", self.spin_delay_max)
        f.addRow("随机 UA:", self.chk_ua)
        f.addRow("代理列表:", self.edit_proxies)
        return w

    def _build_browser_tab(self):
        w = QWidget()
        f = QFormLayout(w)
        self.spin_timeout = QSpinBox(); self.spin_timeout.setRange(5, 120)
        self.spin_timeout.setValue(self._config.get("page_timeout", 30))
        self.spin_retries = QSpinBox(); self.spin_retries.setRange(0, 10)
        self.spin_retries.setValue(self._config.get("js_retries", 3))
        f.addRow("加载超时 (秒):", self.spin_timeout)
        f.addRow("JS 重试次数:", self.spin_retries)
        return w

    def get_config(self) -> dict:
        return {
            "download_threads": self.spin_threads.value(),
            "save_path": self.edit_path.text(),
            "speed_limit": self.spin_speed.value(),
            "resume_enabled": self.chk_resume.isChecked(),
            "ffmpeg_path": self.edit_ffmpeg.text(),
            "delay_min": self.spin_delay_min.value(),
            "delay_max": self.spin_delay_max.value(),
            "random_ua": self.chk_ua.isChecked(),
            "proxy_list": self.edit_proxies.toPlainText().strip().splitlines(),
            "page_timeout": self.spin_timeout.value(),
            "js_retries": self.spin_retries.value(),
        }

import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLabel,
    QComboBox, QHBoxLayout, QDialogButtonBox, QButtonGroup, QRadioButton,
    QLineEdit, QCheckBox)

ELEMENT_TYPES = ["分页链接", "详情链接", "图片容器", "视频容器", "下一页按钮"]

FALLBACK_ATTRS = [
    {"name": "src", "value": ""},
    {"name": "href", "value": ""},
    {"name": "data-src", "value": ""},
    {"name": "data-original", "value": ""},
    {"name": "data-lazy", "value": ""},
]

class TypeSelectorDialog(QDialog):
    def __init__(self, selector: str, detected_attrs: list = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择元素类型")
        self.selected_type = None
        self.selected_attribute = "href"
        self.use_url_pattern = False
        self.url_pattern = ""

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"CSS: {selector[:80]}"))
        layout.addWidget(QLabel("类型:"))
        self._type_group = QButtonGroup()
        for i, t in enumerate(ELEMENT_TYPES):
            rb = QRadioButton(t)
            self._type_group.addButton(rb, i)
            layout.addWidget(rb)
            if t == "详情链接":
                rb.setChecked(True)

        # URL pattern mode
        self.chk_url_mode = QCheckBox("使用 URL 正则匹配（更稳定）")
        self.chk_url_mode.toggled.connect(self._on_mode_toggle)
        layout.addWidget(self.chk_url_mode)
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("正则表达式，如 /d/\\d+")
        self.url_input.hide()
        layout.addWidget(self.url_input)

        # Attribute selector
        layout.addWidget(QLabel("取属性:"))
        self.attr_combo = QComboBox()
        items = detected_attrs if detected_attrs else FALLBACK_ATTRS
        for item in items:
            name = item["name"] if isinstance(item, dict) else item
            value = item.get("value", "") if isinstance(item, dict) else ""
            display = f"{name} = {value[:80]}" if value else name
            self.attr_combo.addItem(display, name)
        layout.addWidget(self.attr_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Auto-generate URL pattern from the URL value if available
        for item in (detected_attrs or []):
            name = item.get("name", "") if isinstance(item, dict) else ""
            value = item.get("value", "") if isinstance(item, dict) else ""
            if name in ("href", "src") and value:
                pattern = self._auto_pattern(value)
                if pattern:
                    self.url_input.setText(pattern)
                    self.url_input.setCursorPosition(0)
                break

    def _auto_pattern(self, url: str) -> str:
        """从链接地址自动生成正则，如 /d/12345 → /d/\\d+"""
        import re
        p = re.sub(r"\d+", r"\\d+", url)
        if p != url:
            return p
        return ""

    def _on_mode_toggle(self, checked):
        self.url_input.setVisible(checked)

    def _on_ok(self):
        btn = self._type_group.checkedButton()
        if btn:
            self.selected_type = btn.text()
            self.selected_attribute = self.attr_combo.currentData()
            self.use_url_pattern = self.chk_url_mode.isChecked()
            if self.use_url_pattern:
                self.url_pattern = self.url_input.text().strip()
            self.accept()

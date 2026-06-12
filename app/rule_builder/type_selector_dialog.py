from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QPushButton, QLabel,
    QComboBox, QHBoxLayout, QDialogButtonBox, QButtonGroup, QRadioButton)

ELEMENT_TYPES = ["分页链接", "详情链接", "图片容器", "视频容器", "下一页按钮"]

ATTR_OPTIONS = ["src", "href", "data-src", "data-original", "data-lazy"]

class TypeSelectorDialog(QDialog):
    def __init__(self, selector: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择元素类型")
        self.selected_type = None
        self.selected_attribute = "src"
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"选择器: {selector}"))
        layout.addWidget(QLabel("类型:"))
        self._type_group = QButtonGroup()
        for i, t in enumerate(ELEMENT_TYPES):
            rb = QRadioButton(t)
            self._type_group.addButton(rb, i)
            layout.addWidget(rb)
            if t == "详情链接":
                rb.setChecked(True)
        layout.addWidget(QLabel("取属性:"))
        self.attr_combo = QComboBox()
        self.attr_combo.addItems(ATTR_OPTIONS)
        layout.addWidget(self.attr_combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self):
        btn = self._type_group.checkedButton()
        if btn:
            self.selected_type = btn.text()
            self.selected_attribute = self.attr_combo.currentText()
            self.accept()

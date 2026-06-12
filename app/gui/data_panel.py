from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

class DataPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("数据面板 (URL输入 + 列表)"))

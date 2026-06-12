from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal


class PickerBridge(QObject):
    elementPicked = pyqtSignal(str)

    @pyqtSlot(str)
    def onElementPicked(self, selector: str):
        self.elementPicked.emit(selector)

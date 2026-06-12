import sys
from PyQt5.QtWidgets import QApplication
from app.gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GetIv")
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

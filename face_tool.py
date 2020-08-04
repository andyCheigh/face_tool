import sys
import os

from PyQt5 import QtWidgets

from src.main_window import MainWindow


def main():
    os.environ['QT_IM_MODULE'] = 'fcitx'
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

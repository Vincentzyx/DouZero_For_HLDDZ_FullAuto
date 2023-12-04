from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5 import QtCore
from PyQt5.QtGui import *
from PyQt5.QtCore import QDate
from window import Ui_MainWindow
import sys
from GameHelper import GameHelper
from PIL import Image
import cv2

GameHelper = GameHelper()
GameHelper.ScreenZoomRate = 1.0


class Main(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(Main, self).__init__()
        self.setupUi(self)
        self.setWindowTitle('存图')
        self.setFixedSize(self.width(), self.height())  # 禁止窗口拉伸
        self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint |  # 使能最小化按钮
                            QtCore.Qt.WindowCloseButtonHint |  # 使能关闭按钮
                            QtCore.Qt.WindowStaysOnTopHint)  # 窗体总在最前端
        self.i = 0
        self.label.setText("0")
        self.pushButton.clicked.connect(self.save_pic)

    def save_pic(self, date):
        img, _ = GameHelper.Screenshot()
        img.save(str(8 + self.i) + ".png")
        self.label.setText(str(self.i))
        self.i += 1


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main = Main()
    main.show()
    sys.exit(app.exec_())

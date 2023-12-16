# coding:utf-8
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

from ui.home import Home

VERSION = "1.0"
AUTHOR = "Moxiner"
from include.tools import Logger


class Demo(Home):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.resize(560, 430)
        self.setMinimumSize(560, 430)
        self.setMaximumSize(560, 430)
        self.setWindowTitle(f"HLDDZ_FullAuto 配置向导   v{VERSION}  By:{AUTHOR}")
        self.setWindowIcon(QIcon("./favicon.ico"))


if __name__ == "__main__":
    # enable dpi scale
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    w = Demo()
    w.show()
    Logger.Info(f"HLDDZ_FullAuto_GUIDE {VERSION}")
    Logger.Info(f"By {AUTHOR}")
    sys.exit(app.exec_())

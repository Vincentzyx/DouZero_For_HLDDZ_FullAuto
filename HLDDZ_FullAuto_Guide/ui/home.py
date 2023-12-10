# coding:utf-8
from PyQt5.QtWidgets import (
    QWidget,
)
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from ui.home_ui import Ui_Home
import webbrowser
from qfluentwidgets import (
    InfoBarPosition,
    InfoBar,
    MessageBox,
)
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from include.tools import Logger, FileOperation
import traceback
import pyperclip

""" Home UI类
"""


class Home(Ui_Home, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setupUi(self)
        self.show()
        self.stateTooltip = None
        self.DeBug_Print = True
        # 初始化选区数据
        self.selectposlistdefault = [
            ["我出牌的区域", "None"],
            ["左边出牌的区域", "None"],
            ["右边出牌的区域", "None"],
            ["地主底牌的区域", "None"],
            ["左边不出的区域", "None"],
            ["右边不出的区域", "None"],
            ["我不出的区域", "None"],
            ["左边牌角的区域", "None"],
            ["右边牌角的区域", "None"],
            ["操作按钮的区域", "None"],
            ["左边地主标识的区域", "None"],
            ["右边地主标识的区域", "None"],
            ["我的地主标识的区域", "None"],
        ]
        self.selectposlist = []
        self.MainWidget.setCurrentIndex(0)
        self.StartButton.clicked.connect(self.OneNextGuide)
        self.OneNextButton.clicked.connect(self.TwoNextGuide)
        self.InstallPythonButton.clicked.connect(self.installPython)
        self.Install3PacketButton.clicked.connect(self.install3Packet)
        self.ShowDisplaySetButton.clicked.connect(self.open_display_settings)
        self.DoneButton.clicked.connect(self.close)
        self.PrintScreenButton.clicked.connect(self.print_screen)
        self.SelectPosButton.clicked.connect(self.select_pos)
        self.TwoNextButton.clicked.connect(self.endGuide)
        self.ClearButton.clicked.connect(self.default_selectpos)
        self.OpenSelectPosButton.clicked.connect(self.open_selectposlist)
        self.CopySelectPosButton.clicked.connect(self.copyConfig)
        self.OpenMainButton.clicked.connect(self.openMain)
        self.OpenProgramButton.clicked.connect(self.openMainProgram)
        self.initmenu()
        self.renew_selectlist()
        self.MenuWidget.setCurrentItem("Onepage")
        pixmap = QtGui.QPixmap("./pics/OneImage.jpg")
        pixmap = pixmap.scaledToWidth(540)

        self.OneImage.setImage(pixmap)
        self.FourImage.setImage(pixmap)
        Logger.Info("HLDDZ 初始化完成")

    def initmenu(self):
        """初始化顶部步数菜单栏"""
        self.MenuWidget.insertItem(
            0,
            "Onepage",
            "开始",
            onClick=lambda: self.MainWidget.setCurrentIndex(0),
        )
        self.MenuWidget.insertItem(1, "Twopage", "第一步", onClick=self.OneNextGuide)
        self.MenuWidget.insertItem(2, "Threepage", "第二步", onClick=self.TwoNextGuide)
        self.MenuWidget.insertItem(3, "Fourpage", "结束", onClick=self.endGuide)

    def OneNextGuide(self):
        """切换至第一步导航页"""
        self.MainWidget.setCurrentIndex(1)
        self.MenuWidget.setCurrentItem("Twopage")
        Logger.Debug("切换至 TwoPage", self.DeBug_Print)

    def TwoNextGuide(self):
        """切换至第二步导航页"""
        self.MainWidget.setCurrentIndex(2)
        self.MenuWidget.setCurrentItem("Threepage")

        Logger.Debug("切换至 FourPage", self.DeBug_Print)

    def installPython(self):
        """安装 Python"""
        self.createInfoBar("正在唤醒浏览器下载Python", "下载完成后请手动安装")

        webbrowser.open(
            "https://www.python.org/ftp/python/3.8.10/python-3.8.10-amd64.exe"
        )
        Logger.Info("唤醒浏览器下载Python")

    def install3Packet(self):
        """安装 Python 第三方库"""
        self.createInfoBar("唤醒安装程序成功", "请查看终端内的安装信息")
        with ThreadPoolExecutor() as executor:
            executor.map(self.run_bat, ["Install.bat"])
        Logger.Info("唤醒 Install.bat 安装第三方库")

    def run_bat(self, file_path):
        """运行 bat 脚本

        Args:
            file_path (string): 脚本的文件路径
        """
        subprocess.run(["start", file_path], shell=True)

    def open_display_settings(self):
        """唤醒显示设置"""
        if os.name == "nt":  # Windows系统
            os.system("control.exe /name Microsoft.Display")
            self.createInfoBar("唤醒屏幕设置成功", "请进行屏幕设置")
        elif os.name == "posix":  # macOS或Linux系统
            subprocess.call("xdg-open display settings", shell=True)
        else:
            Logger.Info("不支持的操作系统")
        Logger.Info("拉起屏幕设置")

    def createInfoBar(self, title, content):
        """创建 通知弹窗

        Args:
            title (string): 标题
            content (string): 内容
        """
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            # position='Custom',   # NOTE: use custom info bar manager
            duration=2000,
            parent=self,
        )

    def createErrorBar(self, title, content):
        """创建 错误弹窗

        Args:
            title (string): 标题
            content (string): 内容
        """
        InfoBar.error(
            title=title,
            content=content,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            # position='Custom',   # NOTE: use custom info bar manager
            duration=2000,
            parent=self,
        )

    def print_screen(self):
        """截图"""
        try:
            from include.GameHelper import GameHelper

            GameHelper = GameHelper()
            GameHelper.ScreenZoomRate = 1.0
            img, _ = GameHelper.Screenshot()
            img.save("PrintScreen.png")
            Logger.Info("图片保存成功")
            self.createInfoBar("截图成功", "请进行选区操作")

        except AttributeError as e:
            self.createErrorBar("未检测到游戏窗口", "请确保游戏在前端运行")
            Logger.Error(traceback.print_exc(), self.DeBug_Print)

    def select_pos(self):
        """触发选区窗口"""
        from include.selectpos import main

        pos = main()
        Logger.Info(pos)
        lst = []
        data = self.read_selectpos()
        for items in data:
            if items[1] == "None":
                lst.append(f"{items[0]}    [无数据，请选区]")
            else:
                lst.append(f"{items[0]}    {items[1]}]")
        for i in range(len(lst)):
            if lst[i] == self.SelectPosComboBox.currentText():
                data[i][1] = pos
                break
        self.write_selectpos(data)
        self.renew_selectlist()

    def renew_selectlist(self):
        """刷新选区数据库和选区下拉选项"""
        data = self.read_selectpos()
        lst = []
        self.SelectPosComboBox.clear()
        for items in data:
            if items[1] == "None":
                lst.append(f"{items[0]}    [无数据，请选区]")
            else:
                lst.append(f"{items[0]}    {items[1]}")
        self.SelectPosComboBox.addItems(lst)
        self.write_selectpos(data)

    def read_selectpos(self):
        """读取选区数据

        Returns:
            list: 选区数据列表
        """
        data = FileOperation.ReadJSon("./data/posdata.json")
        # Logger.Debug(data, self.DeBug_Print)
        return data

    def write_selectpos(self, data):
        """写入选区数据

        Args:
            data (list): 选区数据列表
        """
        FileOperation.WriteJson("./data/posdata.json", data)

    def default_selectpos(self):
        """将选取数据恢复为空"""
        w = MessageBox("确定要清除所有选区数据嘛？", "这将会删除所有的选区数据，此操作不可撤回", self)
        if w.exec():
            FileOperation.WriteJson("./data/posdata.json", self.selectposlistdefault)
            self.createInfoBar("所有选区数据清除成功", "请重新选区吧！")
        else:
            self.createErrorBar("取消删除所有选区数据", "你还是舍不得的，对吧？")

        self.renew_selectlist()

    def open_selectposlist(self):
        """用记事本打开选区数据"""
        FileOperation.WriteText("./data/posdata.txt", self.generateConfig())
        self.createInfoBar("正在唤醒记事本", "正在打开 posdata 相关文件")
        with ThreadPoolExecutor() as executor:
            executor.map(
                subprocess.run(["start", "notepad", "./data/posdata.txt"], shell=True)
            )

        Logger.Info("记事本正在被唤醒，正在打开 posdata.txt")

    def generateConfig(self):
        """转换选区数据"""
        data = self.read_selectpos()
        mainData = f"""
# 坐标
self.MyHandCardsPos = {tuple(data[0][1])}  # 我的截图区域
self.LPlayedCardsPos = {tuple(data[1][1])}  # 左边出牌截图区域
self.RPlayedCardsPos = {tuple(data[2][1])}  # 右边出牌截图区域
self.LandlordCardsPos = {tuple(data[3][1])}  # 地主底牌截图区域，resize成349x168
self.LPassPos = {tuple(data[4][1])}  # 左边不出截图区域
self.RPassPos = {tuple(data[5][1])}  # 右边不出截图区域
self.PassBtnPos = {tuple(data[6][1])}  # 我不出截图区域

self.LCardsCorner = {tuple(data[7][1])}  # 左边牌角截图区域
self.RCardsCorner = {tuple(data[8][1])}  # 右边牌角截图区域
self.GeneralBtnPos = {tuple(data[9][1])} # 我方按钮的位置

self.LandlordFlagPos = [{tuple(data[11][1])}, {tuple(data[12][1])}, {tuple(data[10][1])}]  # 地主标志截图区域(右-我-左)
"""
        return mainData

    def copyConfig(self):
        """将选区数据复制到粘贴板"""
        pyperclip.copy(self.generateConfig())
        self.createInfoBar("已将配置复制至粘贴板", "请打开 main.py 进行参数修改")
        Logger.Info("生成配置文件完成")

    def endGuide(self):
        """切换至结束页"""
        self.MainWidget.setCurrentIndex(3)
        self.MenuWidget.setCurrentItem("Fourpage")

    def openMain(self):
        """用记事本打开 Main.py"""
        try:
            with ThreadPoolExecutor() as executor:
                executor.map(
                    subprocess.run(["start", "notepad", "main.py"], shell=True)
                )
                self.createInfoBar("DouZero 已启动", "开启赌神生活！")

        except Exception as e:
            self.createErrorBar("main.py 打不开", "具体看终端报错")
            Logger.Error(traceback.print_exc(), self.DeBug_Print)

    def openMainProgram(self):
        """打开主程序"""
        try:
            with ThreadPoolExecutor() as executor:
                executor.map(subprocess.run(["start", "python", "main.py"], shell=True))
                self.createInfoBar("DouZero 已启动", "开启赌神生活！")
                self.showMinimized()
        except Exception as e:
            self.createErrorBar("main.py 打不开", "具体看终端报错")
            Logger.Error(traceback.print_exc(), self.DeBug_Print)

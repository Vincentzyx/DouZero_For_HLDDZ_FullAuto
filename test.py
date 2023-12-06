'''from GameHelper import GameHelper
import numpy as np
import cv2
from main import MyPyQT_Form as form
from collections import defaultdict
import GameHelper as gh
GeneralBtnPos = (268, 481, 1240, 255)
helper = GameHelper()
helper.ScreenZoomRate = 1.0

img = cv2.imread("chaojijiabei.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
result = helper.LocateOnScreen("chaojijiabei_btn", img=img, region=GeneralBtnPos)
print(result)'''

# -*- coding: utf-8 -*-
# Created by: Raf
# Modify by: Vincentzyx

import GameHelper as gh
from GameHelper import GameHelper
import os
import sys
import time
import threading
import pyautogui
import win32gui
from PIL import Image
import multiprocessing as mp
import DetermineColor as DC
from skimage.metrics import structural_similarity as ssim
from collections import defaultdict
from douzero.env.move_detector import get_move_type
import cv2
import numpy as np

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QInputDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QTime, QEventLoop
from MainWindow import Ui_Form

from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent
import traceback

import BidModel
import LandlordModel
import FarmerModel

helper = GameHelper()
helper.ScreenZoomRate = 1.0  # 请修改屏幕缩放比

AllCards = ['D', 'X', '2', 'A', 'K', 'Q', 'J', 'T',
            '9', '8', '7', '6', '5', '4', '3']


class MyPyQT_Form:
    def __init__(self):
        super(MyPyQT_Form, self).__init__()
        self.other_hands_cards_str = None
        self.stop_sign = None
        self.loop_sign = None
        self.env = None
        self.three_landlord_cards_env = None
        self.three_landlord_cards_real = None
        self.user_hand_cards_env = None
        self.user_hand_cards_real = None
        self.play_order = None
        self.card_play_data_list = None
        self.other_hand_cards = None
        self.other_played_cards_env = None
        self.other_played_cards_real = None
        self.user_position = None

        # self.Players = [self.RPlayer, self.Player, self.LPlayer]

        self.counter = QTime()

        # 参数
        self.MyConfidence = 0.8  # 我的牌的置信度
        self.OtherConfidence = 0.8  # 别人的牌的置信度
        self.WhiteConfidence = 0.85  # 检测白块的置信度
        self.LandlordFlagConfidence = 0.8  # 检测地主标志的置信度
        self.ThreeLandlordCardsConfidence = 0.8  # 检测地主底牌的置信度
        self.PassConfidence = 0.7

        self.PassConfidence = 0.8
        self.WaitTime = 1  # 等待状态稳定延时
        self.MyFilter = 40  # 我的牌检测结果过滤参数
        self.OtherFilter = 25  # 别人的牌检测结果过滤参数
        self.SleepTime = 0.1  # 循环中睡眠时间
        self.RunGame = False
        self.AutoPlay = False
        self.BidThreshold1 = 65  # 叫地主阈值
        self.BidThreshold2 = 72  # 抢地主阈值
        self.JiabeiThreshold = (
            (85, 72),  # 叫地主 超级加倍 加倍 阈值
            (85, 75)  # 叫地主 超级加倍 加倍 阈值  (在地主是抢来的情况下)
        )
        self.MingpaiThreshold = 92
        # 坐标
        self.MyHandCardsPos = (192, 692, 1448, 120)  # 我的截图区域
        self.LPlayedCardsPos = (400, 300, 500, 270)  # 左边出牌截图区域
        self.RPlayedCardsPos = (880, 300, 500, 270)  # 右边出牌截图区域
        self.LandlordCardsPos = (704, 36, 368, 142)  # 地主底牌截图区域，resize成349x168
        self.LPassPos = (462, 475, 138, 78)  # 左边不出截图区域
        self.RPassPos = (1320, 524, 65, 63)  # 右边不出截图区域

        self.LCardsCorner = (307, 490, 152, 102)  # 左边牌角截图区域
        self.RCardsCorner = (1293, 488, 173, 106)  # 右边牌角截图区域

        self.PassBtnPos = (322, 508, 1124, 213)
        self.LPassPos = (462, 475, 138, 78)  # 左边不出截图区域
        self.RPassPos = (1173, 469, 142, 87)  # 右边不出截图区域
        self.GeneralBtnPos = (268, 481, 1240, 255)
        self.LandlordFlagPos = [(1561, 317, 56, 44), (18, 817, 58, 65), (152, 312, 65, 62)]  # 地主标志截图区域(右-我-左)
        # 信号量
        self.shouldExit = 0  # 通知上一轮记牌结束
        self.canRecord = threading.Lock()  # 开始记牌
        self.card_play_model_path_dict = {
            'landlord': "baselines/resnet/resnet_landlord.ckpt",
            'landlord_up': "baselines/resnet/resnet_landlord_up.ckpt",
            'landlord_down': "baselines/resnet/resnet_landlord_down.ckpt"
        }

    def sleep(self, ms):
        self.counter.restart()
        while self.counter.elapsed() < ms:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)

    def cards_filter(self, location, distance):  # 牌检测结果滤波
        if len(location) == 0:
            return 0
        locList = [location[0][0]]
        poslist = [location[0]]
        count = 1
        for e in location:
            flag = 1  # “是新的”标志
            for have in locList:
                # print(abs(e[0] - have))
                if abs(e[0] - have) <= distance:
                    flag = 0
                    break
            if flag:
                count += 1
                locList.append(e[0])
                poslist.append(e)
        # print(poslist)
        return count, poslist

    def find_cards(self, img, pos, mark="", confidence=0.8):
        cards_real = ""
        D_king = 0
        X_king = 0
        for card in AllCards:
            result = gh.LocateAllOnImage(img, helper.PicsCV[mark + card], region=pos, confidence=confidence)

            if len(result) > 0:
                count, s = self.cards_filter(list(result), 20)
                if card == "X" or card == "D":
                    for a in s:
                        classifier = DC.ColorClassify(debug=True)
                        img1 = img[pos[1]:pos[1] + pos[3], pos[0]:pos[0] + pos[2]]
                        img2 = img1[a[1]:a[1] + a[3] - 50, a[0]:a[0] + 20]  # 注意连着裁切时img不能重名
                        # gh.ShowImg(img2)
                        result = classifier.classify(img2)
                        # print(result)
                        for b in result:
                            if b[0] == "Red":
                                if b[1] > 0.54:
                                    D_king = 1
                                else:
                                    X_king = 1
                else:
                    cards_real += card[0] * count

        if X_king:
            cards_real += "X"
            cards_real = cards_real[-1] + cards_real[:-1]

        if D_king:
            cards_real += "D"
            cards_real = cards_real[-1] + cards_real[:-1]
        return cards_real

    def find_my_cards(self):
        # img = cv2.imread("11.png")
        img, _ = helper.Screenshot()
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        my_cards_real = self.find_cards(img, self.MyHandCardsPos, mark="m")
        return my_cards_real

    def my_cards_area(self):
        cards = self.find_my_cards()
        res1 = helper.LocateOnScreen("top_left_corner", region=self.MyHandCardsPos, confidence=0.65)
        while res1 is None:
            if not self.RunGame:
                break
            print("未找到手牌区域")
            img, _ = helper.Screenshot()
            img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
            cv2.imwrite("hand_cards_debug.png", img)
            self.sleep(500)
            res1 = helper.LocateOnScreen("top_left_corner", region=self.MyHandCardsPos, confidence=0.65)
        pos = res1[0] + 15, res1[1] + 10, 57 * len(cards), 200

        res2 = helper.LocateOnScreen("top_left_corner", region=(192, 720, 1448, 100), confidence=0.65)
        if res2 is not None:
            pos = res2[0] + 15, res2[1] + 10, 57 * len(cards), 200
        return pos

    def test(self):
        img = cv2.imread("debug2.png")
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        cards = "2TT976654433"
        num = len(cards)
        space = 57

        res1 = helper.LocateOnScreen("top_left_corner", img=img, region=(192, 700, 1448, 120), confidence=0.7)
        area = res1[0] + 15, res1[1] + 10, 57 * len(cards), 200
        print(res1)
        if res1 is not None:
            res3 = helper.LocateOnScreen("top_left_corner", img=img, region=(192, 720, 1448, 100), confidence=0.7)
            print(res3)
            area = res3[0] + 15, res3[1] + 10, 57 * len(cards), 200

        # img = img[pos[1]:pos[1]+pos[3], pos[0]:pos[0]+pos[2]]

        pos_list = [(area[0] + i * space, area[1]) for i in range(num)]
        # 将两个列表合并转为字典
        cards_dict = defaultdict(list)
        for key, value in zip(cards, pos_list):
            cards_dict[key].append(value)
        # 转换为普通的字典
        cards_dict = dict(cards_dict)
        print(cards_dict)
        i = "T"
        cars_pos = cards_dict[i][-1][0:2]
        print(cars_pos)

        point = cars_pos[0] + 20, cars_pos[1] + 50
        check_one = self.find_cards(img=img, pos=(cars_pos[0] + 5, 700, 60, 85), mark="m", confidence=0.8)
        img = gh.DrawRectWithText(img, (cars_pos[0] + 5, 700, 60, 85), "test")
        img = gh.DrawRectWithText(img, area, "test")
        gh.ShowImg(img)

        print("检查牌的上面有没有牌：", check_one)
    def haha(self):
        img = cv2.imread("debug2.png")
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        check_cards = self.find_cards(img, (192, 740, 1448, 200), mark="m")
        return check_cards


if __name__ == '__main__':
    main = MyPyQT_Form()
    # main.test()
    print(main.haha())




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
from cnocr import CnOcr

ocr = CnOcr(det_model_name='en_PP-OCRv3_det', rec_model_name='en_PP-OCRv3',
            cand_alphabet="12345678910JQKA")  # 所有参数都使用默认值

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
        self.MyHandCardsPos = (180, 560, 1050, 90)  # 我的截图区域
        self.LPlayedCardsPos = (320, 280, 500, 120)  # 左边出牌截图区域
        self.RPlayedCardsPos = (600, 280, 500, 120)  # 右边出牌截图区域
        self.LandlordCardsPos = (600, 33, 220, 103)  # 地主底牌截图区域
        self.LPassPos = (360, 360, 120, 80)  # 左边不出截图区域
        self.RPassPos = (940, 360, 120, 80)  # 右边不出截图区域

        self.PassBtnPos = (200, 450, 1000, 120)  # 要不起截图区域
        self.GeneralBtnPos = (200, 450, 1000, 120)  # 叫地主、抢地主、加倍按钮截图区域
        self.LandlordFlagPos = [(1247, 245, 48, 52), (12, 661, 51, 53), (123, 243, 52, 54)]  # 地主标志截图区域(右-我-左)
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
                count, s = self.cards_filter(list(result), 30)
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
        img = cv2.imread("10.png")
        # img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        my_cards_real = self.find_cards(img, self.MyHandCardsPos, mark="m")
        return my_cards_real

    def click_cards(self, out_cards):
        cards = self.find_my_cards()
        num = len(cards)
        space = 45.6
        img = cv2.imread("10.png")
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        res1 = helper.LocateOnScreen("up_left", img=img, region=self.MyHandCardsPos, confidence=0.65)
        pos = res1[0] + 6, res1[1] + 7

        res2 = helper.LocateOnScreen("up_left", img=img, region=(180, 580, 1050, 90), confidence=0.65)
        if res2 is not None:
            pos = res1[0] + 6, res1[1] + 7

        pos_list = [(int(pos[0] + i * space), pos[1]) for i in range(num)]

        # 将两个列表合并转为字典
        cards_dict = defaultdict(list)
        for key, value in zip(cards, pos_list):
            cards_dict[key].append(value)
        # 转换为普通的字典
        cards_dict = dict(cards_dict)
        remove_dict = {key: [] for key in cards_dict.keys()}
        # print(cards_dict)
        if out_cards == "DX":
            helper.LeftClick2((cards_dict["X"][0][0] + 20, 650))
            self.sleep(500)

        else:
            for i in out_cards:
                cars_pos = cards_dict[i][-1][0:2]

                # print("准备点击的牌：", cards_dict[i])
                point = cars_pos[0] + 20, cars_pos[1] + 100
                img = cv2.imread("10.png")
                # img = cv2.cvtColor(np.asarray(img), cv2.COLOR_BGR2RGB)
                print((cars_pos[0] - 2, 565, 60, 60))
                check_one = self.find_cards(img=img, pos=(cars_pos[0] - 2, 565, 60, 60), mark="m", confidence=0.7)
                print("系统帮你点的牌：", check_one, "你要出的牌：", i)

                '''if check_one == i and check_one != "D" and check_one != "X":
                    # print("腾讯自动帮你选牌：", check_one)
                    img, _ = helper.Screenshot()
                    img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
                    cv2.imwrite("debug.png", img)

                else:
                    helper.LeftClick2(point)
                    # print(point)
                    self.sleep(100)
                remove_dict[i].append(cards_dict[i][-1])
                cards_dict[i].remove(cards_dict[i][-1])
                # print("remove_dict", remove_dict)
            img, _ = helper.Screenshot()
            img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
            check_cards = self.find_cards(img, (180, 590, 1050, 90), mark="m")
            for i in out_cards:
                cards = cards.replace(i, "", 1)
            print("检查剩的牌： ", check_cards, "应该剩的牌： ", cards)
            if len(check_cards) < len(cards):
                for m in check_cards:
                    cards = cards.replace(m, "", 1)
                print("系统多点的牌： ", cards)
                for n in cards:
                    # print("字典里还剩的牌： ", cards_dict)
                    cars_pos2 = cards_dict[n][-1][0:2]
                    # print("准备点回来的牌：", cars_pos2)
                    point2 = cars_pos2[0] + 20, cars_pos2[1] + 100
                    helper.LeftClick2(point2)
                    self.sleep(100)
                    remove_dict[n].append(cards_dict[n][-1])
                    cards_dict[n].remove(cards_dict[n][-1])
            elif len(check_cards) > len(cards):
                img, _ = helper.Screenshot()
                img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
                cv2.imwrite("debug2.png", img)
                for m in cards:
                    check_cards = check_cards.replace(m, "", 1)
                print("系统少点的牌： ", check_cards)
                for n in check_cards:
                    # print("删除的字典： ", remove_dict)
                    cars_pos3 = remove_dict[n][0][0:2]
                    # print("准备再点出去的牌：", cars_pos3)
                    point3 = cars_pos3[0] + 20, cars_pos3[1] + 100
                    helper.LeftClick2(point3)
                    self.sleep(300)
                    remove_dict[n].remove(remove_dict[n][0])
                    # print(remove_dict)
            self.sleep(200)
'''

if __name__ == '__main__':
    main = MyPyQT_Form()
    # main.test()
    main.click_cards("KK")

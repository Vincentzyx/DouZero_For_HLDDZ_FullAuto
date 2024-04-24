# -*- coding: utf-8 -*-
# @Time : 2024/2/16 15:10
# @Author : MaYun
# @File : main.py
# @Software: PyCharm

import GameHelper as gh
from GameHelper import GameHelper, play_sound, read_json, write_json
import sys
import json
import time
import DetermineColor as DC
from collections import defaultdict
from douzero.env.move_detector import get_move_type
import cv2
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QLabel
from PyQt5.QtGui import QKeyEvent, QIcon
from PyQt5.QtCore import QTime, QEventLoop, Qt, QFile, QTextStream, pyqtSignal, QThread
from MainWindow import Ui_Form

from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent
import traceback
from skimage.metrics import structural_similarity as ssim

import BidModel
import LandlordModel
import FarmerModel

helper = GameHelper()

EnvCard2RealCard = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9', 10: 'T', 11: 'J', 12: 'Q',
                    13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12,
                    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}

bombs = [[3, 3, 3, 3], [4, 4, 4, 4], [5, 5, 5, 5], [6, 6, 6, 6], [7, 7, 7, 7], [8, 8, 8, 8], [9, 9, 9, 9],
         [10, 10, 10, 10], [11, 11, 11, 11], [12, 12, 12, 12], [13, 13, 13, 13], [14, 14, 14, 14], [17, 17, 17, 17],
         [20, 30]]

AllCards = ['D', 'X', '2', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3']

AllEnvCard = [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7, 8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10,
              11, 11, 11, 11, 12, 12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 17, 17, 17, 17, 20, 30]


def cards_filter(location, distance):  # 牌检测结果滤波
    if len(location) == 0:
        return 0
    locList = [location[0][0]]
    poslist = [location[0]]
    count = 1
    for e in location:
        flag = 1
        for have in locList:
            if abs(e[0] - have) <= distance:
                flag = 0
                break
        if flag:
            count += 1
            locList.append(e[0])
            poslist.append(e)
    return count, poslist


def send_GG_and_MM():
    helper.ClickOnImage("chat", region=(1302, 744, 117, 56))
    time.sleep(0.5)
    helper.MouseScroll(-1000)
    time.sleep(0.5)
    helper.LeftClick((1110, 543))


def give_thumb():
    helper.ClickOnImage("chat", region=(1302, 744, 117, 56))
    time.sleep(0.5)
    helper.LeftClick((1375, 596))
    time.sleep(0.5)
    helper.LeftClick((1075, 293))


def give_coffee(side):
    if side == "right":
        print("Giving coffee to right")
        helper.MoveTo((1167, 293))
        time.sleep(1)
        helper.LeftClick((920, 237))
        time.sleep(0.1)
    elif side == "left":
        print("Giving coffee to left")
        helper.MoveTo((260, 300))
        time.sleep(1)
        helper.LeftClick((660, 237))
        time.sleep(0.1)
    else:
        print("咖啡side错误")


def compareImage(img1, img2):
    # 转换为灰度图
    gray1 = cv2.cvtColor(np.asarray(img1), cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(np.asarray(img2), cv2.COLOR_BGR2GRAY)

    # 使用结构相似性指数（SSIM）比较相似度
    ssim_index, _ = ssim(gray1, gray2, full=True)
    if ssim_index < 0.99:
        return True

    return False


def real_to_env(cards):
    env_card = [RealCard2EnvCard[c] for c in cards]
    env_card.sort()
    return env_card


def subtract_strings(str1, str2):
    result = ""
    for char1, char2 in zip(str1, str2):
        # 如果字符2在字符1中出现，则从字符1中删除该字符
        if char2 in str1:
            str1 = str1.replace(char2, '', 1)
    result = str1
    return result


class Worker(QThread):
    auto_game = pyqtSignal(int)  # Automatic start
    hand_game = pyqtSignal(int)  # Human start
    init_interface = pyqtSignal(int)  # Initialize interface
    player_display = pyqtSignal(int)  # Player Display
    state_display = pyqtSignal(str)  # 游戏状态显示
    stop = pyqtSignal(int)
    bid_display = pyqtSignal(str)  # 叫牌score
    pre_display = pyqtSignal(str)  # 局前score
    three_cards_display = pyqtSignal(str)  # Three cards display
    winrate_display = pyqtSignal(str)  # Winrate Display
    pre_cards_display = pyqtSignal(str)  # 显示AI推荐出牌
    left_cards_display = pyqtSignal(str)  # 显示上家的牌
    right_cards_display = pyqtSignal(str)  # 显示下家的牌
    recorder_display = pyqtSignal(str)  # 记牌器
    write_threshold = pyqtSignal(int)  # 阈值写入json

    def __init__(self):
        super(Worker, self).__init__()
        self.MingpaiThreshold = None
        self.FarmerJiabeiThresholdLow = None
        self.FarmerJiabeiThreshold = None
        self.JiabeiThreshold = None
        self.BidThresholds = None
        self.my_pass_sign = None
        self.my_played_cards_env = None
        self.my_played_cards_real = None
        self.auto_sign = None
        self.winrate = None
        self.in_game_flag = None
        self.initial_mingpai = None
        self.initial_multiply = None
        self.initial_cards = None
        self.RunGame = None
        self.initial_bid_rate = None
        self.initial_model_rate = None
        self.other_hands_cards_str = None
        self.stop_sign = None
        self.loop_sign = None
        self.env = None
        self.three_cards_env = None
        self.three_cards_real = None
        self.user_hand_cards_env = None
        self.user_hand_cards_real = None
        self.play_order = None
        self.card_play_data_list = None
        self.other_hand_cards = None
        self.other_played_cards_env = None
        self.other_played_cards_real = None
        self.user_position = None
        self.user_position_code = None
        self.distance = 30

        self.MyHandCardsPos = (180, 560, 1050, 90)  # 我的截图区域
        self.LPlayedCardsPos = (320, 280, 400, 120)  # 左边出牌截图区域
        self.RPlayedCardsPos = (720, 280, 400, 120)  # 右边出牌截图区域
        self.MPlayedCardsPos = (300, 350, 800, 100)  # 我的出牌截图区域

        self.LandlordCardsPos = (600, 33, 220, 103)  # 地主底牌截图区域
        self.LPassPos = (360, 360, 120, 80)  # 左边不出截图区域
        self.RPassPos = (940, 360, 120, 80)  # 右边不出截图区域
        self.MPassPos = (636, 469, 152, 87)  # 我的不出截图区域

        self.PassBtnPos = (200, 450, 1000, 120)  # 要不起截图区域
        self.GeneralBtnPos = (200, 450, 1000, 120)  # 叫地主、抢地主、加倍按钮截图区域
        self.LandlordFlagPos = [(1247, 245, 48, 52), (12, 661, 51, 53), (123, 243, 52, 54)]  # 地主标志截图区域(右-我-左)
        self.blue_cards_num = [(273, 388, 33, 42), (1117, 387, 33, 44)]  # 加倍阶段上家和下家的牌数显示区域

        self.model_path_dict = {
            'landlord': "baselines/resnet/resnet_landlord.ckpt",
            'landlord_up': "baselines/resnet/resnet_landlord_up.ckpt",
            'landlord_down': "baselines/resnet/resnet_landlord_down.ckpt"
        }
        LandlordModel.init_model("baselines/resnet/resnet_landlord.ckpt")

    def run(self):
        if self.auto_sign:
            print("现在是自动模式")
        else:
            print("现在是手动模式")
        self.loop_sign = True
        self.stop_sign = False
        self.run_threshold()
        while not self.stop_sign:
            self.detect_start_btn()
            self.init_interface.emit(1)
            self.before_start()
            self.init_cards()
            time.sleep(2)

    def run_threshold(self):
        self.write_threshold.emit(1)
        time.sleep(0.1)
        data = read_json()

        self.BidThresholds = [float(data['bid1']), float(data['bid2']), float(data['bid3'])]
        self.JiabeiThreshold = (
            (float(data['jiabei1']), float(data['jiabei2'])), (float(data['jiabei3']), float(data['jiabei4'])))
        self.FarmerJiabeiThreshold = (float(data['jiabei5']), float(data['jiabei6']))
        self.FarmerJiabeiThresholdLow = (float(data['jiabei7']), float(data['jiabei8']))
        self.MingpaiThreshold = float(data['mingpai'])

    def detect_start_btn(self):
        beans = [(308, 204, 254, 60), (295, 474, 264, 60), (882, 203, 230, 60)]
        for i in beans:
            result = helper.LocateOnScreen("over", region=i, confidence=0.9)
            if result is not None:
                print("\n豆子出现，对局结束")
                self.RunGame = False
                try:
                    if self.env is not None:
                        self.env.game_over = True
                        self.env.reset()
                    self.init_interface.emit(1)
                except AttributeError as e:
                    traceback.print_exc()
                time.sleep(3)
                break

        if self.auto_sign:
            result = helper.LocateOnScreen("continue", region=(1100, 617, 200, 74))
            if result is not None:
                if not self.loop_sign:
                    print("游戏已结束")
                    self.state_display.emit("游戏已结束")
                    self.stop.emit(1)
                else:
                    self.RunGame = False
                    try:
                        if self.env is not None:
                            self.env.game_over = True
                            self.env.reset()
                        self.init_interface.emit(1)
                    except AttributeError as e:
                        traceback.print_exc()
                        time.sleep(1)
                    helper.ClickOnImage("continue", region=(1100, 617, 200, 74))

            win = helper.LocateOnScreen("win", region=(756, 191, 240, 107))
            lose = helper.LocateOnScreen("lose", region=(756, 191, 240, 107))
            if win is not None or lose is not None:
                if not self.loop_sign:
                    print("游戏已结束")
                    self.state_display.emit("游戏已结束")
                    self.stop.emit(1)
                else:
                    self.RunGame = False
                    try:
                        if self.env is not None:
                            self.env.game_over = True
                            self.env.reset()
                        self.init_interface.emit(1)
                    except AttributeError as e:
                        traceback.print_exc()
                        time.sleep(1)
                    time.sleep(1)

            result = helper.LocateOnScreen("quick_start", region=(1107, 679, 252, 118))
            if result is not None:
                helper.ClickOnImage("quick_start", region=(1107, 679, 252, 118))
                time.sleep(1)

            result = helper.LocateOnScreen("reward", region=(587, 570, 224, 86))
            if result is not None:
                helper.ClickOnImage("reward", region=(587, 570, 224, 86))
                time.sleep(1)

            result = helper.LocateOnScreen("start_game", region=(720, 466, 261, 117))
            if result is not None:
                helper.ClickOnImage("start_game", region=(720, 466, 261, 117))
                time.sleep(1)

            result = helper.LocateOnScreen("tuoguan", region=(577, 613, 271, 128))
            if result is not None:
                helper.ClickOnImage("tuoguan", region=(577, 613, 271, 128))
                time.sleep(1)

            result = helper.LocateOnScreen("sure", region=(630, 456, 289, 143))
            if result is not None:
                helper.ClickOnImage("sure", region=(630, 456, 289, 143))
                time.sleep(1)

            result = helper.LocateOnScreen("tuijian", region=(729, 465, 219, 100))
            if result is not None:
                helper.ClickOnImage("tuijian", region=(729, 465, 219, 100))
                time.sleep(1)

            result = helper.LocateOnScreen("good", region=(434, 599, 219, 88))
            if result is not None:
                helper.ClickOnImage("good", region=(434, 599, 219, 88))
                time.sleep(1)

            result = helper.LocateOnScreen("zhidao", region=(593, 543, 224, 94))
            if result is not None:
                helper.ClickOnImage("zhidao", region=(593, 543, 224, 94))
                time.sleep(1)

            result = helper.LocateOnScreen("chacha", region=(1036, 65, 300, 230))
            if result is not None:
                helper.ClickOnImage("chacha", region=(1036, 65, 300, 230))
                time.sleep(1)
        else:
            pass

    def before_start(self):
        self.in_game_flag = False
        print("未进入游戏", end='')
        in_game = helper.LocateOnScreen("chat", region=(1302, 744, 117, 56))
        while in_game is None:
            time.sleep(1)
            print(".", end="")
            self.state_display.emit("未进入游戏")
            in_game = helper.LocateOnScreen("chat", region=(1302, 744, 117, 56))
            self.detect_start_btn()
        self.in_game_flag = True
        time.sleep(0.3)
        if self.in_game_flag:
            print("\n在游戏场内")
            print("游戏未开始", end="")
            laotou = helper.LocateOnScreen("laotou", region=self.LandlordCardsPos)
            while laotou is None:
                time.sleep(0.5)
                print(".", end="")
                self.state_display.emit("游戏未开始")
                laotou = helper.LocateOnScreen("laotou", region=self.LandlordCardsPos)
                self.detect_start_btn()

            print("\n开始游戏")
            self.state_display.emit("开始游戏")
        try:
            self.RunGame = True
            self.choose_multiples_stage()
        except Exception as e:
            print("加倍阶段有问题")

    def choose_multiples_stage(self):
        global win_rate, initialBeishu, cards_str
        self.initial_multiply = 0
        self.initial_mingpai = 0
        self.initial_bid_rate = 0
        have_bid = False
        is_stolen = 0
        cards = self.find_three_cards()
        while len(cards) == 0:
            if not self.RunGame:
                break
            if self.auto_sign:
                self.state_display.emit("自动模式")
                self.winrate_display.emit("     自动模式：   叫地主  抢地主  加倍")
                cards = self.find_my_cards()
                while len(cards) < 5:
                    if not self.RunGame or not self.auto_sign:
                        break
                    time.sleep(0.01)
                    cards = self.find_my_cards()
                    self.detect_start_btn()
                print("前6张牌：", cards)

                if "DX222" in cards:
                    ming_btn = helper.LocateOnScreen("ming_btn", region=self.GeneralBtnPos)
                    if ming_btn is not None:
                        helper.ClickOnImage("ming_btn", region=self.GeneralBtnPos)
                        print("明牌")

                while self.RunGame and self.auto_sign:
                    outterBreak = False
                    jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=self.GeneralBtnPos)
                    qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=self.GeneralBtnPos)
                    jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
                    print("自动加倍或叫地主", end="")
                    while jiaodizhu_btn is None and qiangdizhu_btn is None and jiabei_btn is None:
                        if not self.RunGame or not self.auto_sign:
                            break
                        print(".", end="")
                        time.sleep(0.1)
                        jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=self.GeneralBtnPos)
                        qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=self.GeneralBtnPos)
                        jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
                        self.detect_start_btn()
                    if jiabei_btn is None:
                        cards = self.find_my_cards()
                        while len(cards) != 17 and len(cards) != 20:
                            if not self.RunGame or not self.auto_sign:
                                break
                            time.sleep(0.2)
                            cards = self.find_my_cards()
                            self.detect_start_btn()
                        cards_str = "".join([card[0] for card in cards])
                        win_rate = BidModel.predict_score(cards_str)
                        farmer_score = FarmerModel.predict(cards_str, "farmer")
                        self.bid_display.emit("叫牌得分: " + str(round(win_rate, 3)))
                        self.pre_display.emit("不叫得分: " + str(round(farmer_score, 3)))
                        self.initial_bid_rate = round(win_rate, 3)
                        is_stolen = 0

                        if jiaodizhu_btn is not None:
                            have_bid = True
                            if win_rate > self.BidThresholds[0]:
                                helper.ClickOnImage("jiaodizhu_btn", region=self.GeneralBtnPos)
                                print("\n叫地主")

                            else:
                                helper.ClickOnImage("bujiao_btn", region=self.GeneralBtnPos)
                                print("\n不叫地主")
                        elif qiangdizhu_btn is not None:
                            is_stolen = 1
                            if have_bid:
                                threshold_index = 1
                            else:
                                threshold_index = 2
                            if win_rate > self.BidThresholds[threshold_index]:
                                helper.ClickOnImage("qiangdizhu_btn", region=self.GeneralBtnPos)
                                print("\n抢地主")
                            else:
                                helper.ClickOnImage("buqiang_btn", region=self.GeneralBtnPos)
                                print("\n不抢地主")
                            have_bid = True

                    else:
                        self.state_display.emit("加倍阶段")

                        self.three_cards_real = self.find_three_cards()
                        print("正在识别底牌", end="")
                        while len(self.three_cards_real) != 3:
                            print(".", end="")
                            if not self.RunGame or not self.auto_sign:
                                break
                            time.sleep(0.2)
                            self.three_cards_real = self.find_three_cards()
                            self.detect_start_btn()
                        print("\n底牌:", self.three_cards_real)
                        cards = self.find_my_cards()
                        while len(cards) != 17 and len(cards) != 20:
                            if not self.RunGame or not self.auto_sign:
                                break
                            time.sleep(0.2)
                            cards = self.find_my_cards()
                            self.detect_start_btn()
                        cards_str = "".join([card[0] for card in cards])
                        self.initial_cards = cards_str
                        if len(cards_str) == 20:
                            print("手牌：", cards_str)
                            self.user_position_code = 1
                            win_rate = LandlordModel.predict_by_model(cards_str, self.three_cards_real)
                            self.pre_display.emit("局前得分: " + str(round(win_rate, 3)))
                            print("预估地主得分:", round(win_rate, 3))
                        else:
                            win_rate = FarmerModel.predict(cards_str, "up")
                            print("预估农民得分:", round(win_rate, 3))
                            self.pre_display.emit("局前得分: " + str(round(win_rate, 3)))
                        if len(cards_str) == 20:
                            JiabeiThreshold = self.JiabeiThreshold[is_stolen]
                        else:
                            JiabeiThreshold = self.FarmerJiabeiThreshold

                        if len(cards_str) == 17:
                            time.sleep(3)
                            print("休息 3 秒, 观察他人加倍情况")
                        else:
                            time.sleep(2)
                            print("休息 2 秒, 观察他人加倍情况")
                        #  识别加倍数

                        if len(cards_str) == 17:
                            JiabeiThreshold = self.FarmerJiabeiThresholdLow

                        if win_rate > JiabeiThreshold[0]:
                            chaojijiabei_btn = helper.LocateOnScreen("chaojijiabei_btn", region=self.GeneralBtnPos)
                            if (chaojijiabei_btn is not None and
                                    ('DX' in cards_str or 'D2' in cards_str or 'X22' in cards_str or
                                     '222A' in cards_str or '22AAA' in cards_str)):
                                helper.ClickOnImage("chaojijiabei_btn", region=self.GeneralBtnPos)
                                print("超级加倍")
                                self.initial_multiply = 4
                            else:
                                helper.ClickOnImage("jiabei_btn", region=self.GeneralBtnPos, confidence=0.9)
                                print("加倍")
                                self.initial_multiply = 2
                        elif win_rate > JiabeiThreshold[1]:
                            print("加倍")
                            helper.ClickOnImage("jiabei_btn", region=self.GeneralBtnPos, confidence=0.9)
                            self.initial_multiply = 2
                        else:
                            print("不加倍")
                            helper.ClickOnImage("bujiabei_btn", region=self.GeneralBtnPos)
                            self.initial_multiply = 0
                        break
                    self.detect_start_btn()
                    if outterBreak:
                        break
                    time.sleep(1)

                if win_rate > self.MingpaiThreshold and len(cards_str) == 20:
                    try:
                        print("Going to Mingpai, Good Luck!")
                        time.sleep(5)
                        helper.ClickOnImage("mingpai_btn", region=self.GeneralBtnPos)
                        print("明牌")
                        self.initial_mingpai = 1
                    except Exception as e:
                        print(e)

                self.winrate = win_rate
                print("自动叫地主结束")
                self.state_display.emit("加倍结束")

            else:
                self.state_display.emit("手动模式")
                self.winrate_display.emit("     手动模式：   叫地主  抢地主  加倍")
                print("手动加倍或叫地主")
                while self.RunGame and not self.auto_sign:
                    jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=self.GeneralBtnPos)
                    qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=self.GeneralBtnPos)
                    jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)

                    while jiaodizhu_btn is None and qiangdizhu_btn is None and jiabei_btn is None:
                        if not self.RunGame or self.auto_sign:
                            break
                        time.sleep(0.1)
                        jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=self.GeneralBtnPos)
                        qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=self.GeneralBtnPos)
                        jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
                        self.detect_start_btn()
                    if jiabei_btn is None:
                        cards = self.find_my_cards()
                        while len(cards) != 17 and len(cards) != 20:
                            if not self.RunGame or self.auto_sign:
                                break
                            time.sleep(0.2)
                            cards = self.find_my_cards()
                            self.detect_start_btn()
                        cards_str = "".join([card[0] for card in cards])
                        win_rate = BidModel.predict_score(cards_str)
                        farmer_score = FarmerModel.predict(cards_str, "farmer")
                        self.bid_display.emit("叫牌得分: " + str(round(win_rate, 3)))
                        self.pre_display.emit("不叫得分: " + str(round(farmer_score, 3)))

                        if jiaodizhu_btn is not None:
                            print("\n 正在叫地主")
                            self.state_display.emit("正在叫地主")
                            time.sleep(2)

                        elif qiangdizhu_btn is not None:
                            print("\n正在抢地主")
                            self.state_display.emit("正在抢地主")
                            time.sleep(2)

                    else:
                        print("\n正在加倍")
                        self.state_display.emit("正在加倍")
                        self.three_cards_real = self.find_three_cards()
                        print("正在识别底牌", end="")
                        while len(self.three_cards_real) != 3:
                            print(".", end="")
                            if not self.RunGame or not self.auto_sign:
                                break
                            time.sleep(0.2)
                            self.three_cards_real = self.find_three_cards()
                            self.detect_start_btn()
                        print("\n底牌:", self.three_cards_real)
                        cards = self.find_my_cards()
                        while len(cards) != 17 and len(cards) != 20:
                            if not self.RunGame or not self.auto_sign:
                                break
                            time.sleep(0.2)
                            cards = self.find_my_cards()
                            self.detect_start_btn()
                        cards_str = "".join([card[0] for card in cards])
                        self.initial_cards = cards_str
                        if len(cards_str) == 20:
                            print("手牌：", cards_str)
                            self.user_position_code = 1
                            win_rate = LandlordModel.predict_by_model(cards_str, self.three_cards_real)
                            self.pre_display.emit("局前得分: " + str(round(win_rate, 3)))
                            print("预估地主得分:", round(win_rate, 3))
                        else:
                            win_rate = FarmerModel.predict(cards_str, "up")
                            print("预估农民得分:", round(win_rate, 3))
                            self.pre_display.emit("局前得分: " + str(round(win_rate, 3)))
                            time.sleep(3)
                        break
                    self.detect_start_btn()

                self.winrate = win_rate
                print("手动叫地主结束")
                self.state_display.emit("加倍结束")
                cards = self.find_three_cards()
                self.detect_start_btn()

    def init_cards(self):
        print("进入出牌前的阶段")
        # 玩家角色代码：0-地主上家, 1-地主, 2-地主下家
        self.RunGame = True
        self.user_position_code = None
        self.initial_model_rate = 0
        self.user_hand_cards_env = []
        self.my_played_cards_env = []
        self.other_played_cards_env = []
        # 其他玩家手牌（整副牌减去玩家手牌，后续再减掉历史出牌）
        self.other_hand_cards = []
        self.three_cards_env = []
        # 开局时三个玩家的手牌
        self.card_play_data_list = {}

        # 识别三张底牌
        print("正在识别底牌", end="")
        while len(self.three_cards_real) != 3:
            print(".", end="")
            if not self.RunGame:
                break
            time.sleep(0.2)
            self.three_cards_real = self.find_three_cards()
            self.detect_start_btn()
        print("\n底牌： ", self.three_cards_real)
        self.three_cards_display.emit("底牌：" + self.three_cards_real)
        self.three_cards_env = [RealCard2EnvCard[c] for c in list(self.three_cards_real)]

        # 识别玩家的角色
        time.sleep(0.5)
        print("正在识别玩家角色", end="")
        while self.user_position_code is None:
            if not self.RunGame:
                break
            print(".", end="")
            self.user_position_code = self.find_landlord()
            time.sleep(0.2)
            self.detect_start_btn()

        self.user_position = ['landlord_up', 'landlord', 'landlord_down'][self.user_position_code]
        print("我的角色：", self.user_position)
        self.player_display.emit(self.user_position_code)

        # 识别玩家手牌
        self.user_hand_cards_real = self.find_my_cards()
        if self.user_position_code == 1:
            while len(self.user_hand_cards_real) != 20:
                if not self.RunGame:
                    break
                time.sleep(0.2)
                self.user_hand_cards_real = self.find_my_cards()
                self.detect_start_btn()
            self.user_hand_cards_env = [RealCard2EnvCard[c] for c in list(self.user_hand_cards_real)]
        else:
            while len(self.user_hand_cards_real) != 17:
                if not self.RunGame:
                    break
                time.sleep(0.2)
                self.user_hand_cards_real = self.find_my_cards()
                self.detect_start_btn()
            self.user_hand_cards_env = [RealCard2EnvCard[c] for c in list(self.user_hand_cards_real)]

        # 整副牌减去玩家手上的牌，就是其他人的手牌,再分配给另外两个角色（如何分配对AI判断没有影响）
        for i in set(AllEnvCard):
            self.other_hand_cards.extend([i] * (AllEnvCard.count(i) - self.user_hand_cards_env.count(i)))
        self.other_hands_cards_str = str(''.join([EnvCard2RealCard[c] for c in self.other_hand_cards]))[::-1]
        self.recorder_display.emit(self.other_hands_cards_str)
        self.card_play_data_list.update({
            'three_landlord_cards': self.three_cards_env,
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 0) % 3]:
                self.user_hand_cards_env,
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 1) % 3]:
                self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 != 1 else self.other_hand_cards[17:],
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 2) % 3]:
                self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 == 1 else self.other_hand_cards[17:]
        })
        print("开始对局")
        print("手牌:", self.user_hand_cards_real)
        print("底牌:", self.three_cards_real)

        # 出牌顺序：0-玩家出牌, 1-玩家下家出牌, 2-玩家上家出牌
        self.play_order = 0 if self.user_position == "landlord" else 1 if self.user_position == "landlord_up" else 2

        # 创建一个代表玩家的AI
        AI = [0, 0]
        AI[0] = self.user_position
        AI[1] = DeepAgent(self.user_position, self.model_path_dict[self.user_position])
        self.env = GameEnv(AI)

        try:
            self.game_start()
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            traceback.print_tb(exc_tb)
            self.RunGame = False
            if self.env is not None:
                self.env.game_over = True
                self.env.reset()
            self.init_interface.emit(1)

    def game_start(self):
        self.my_pass_sign = False
        self.env.card_play_init(self.card_play_data_list)
        print("开始对局")
        self.state_display.emit("游戏开始")
        first_run = True

        while not self.env.game_over:
            if not self.RunGame:
                break
            while self.play_order == 0:
                if not self.RunGame:
                    break
                cards = self.find_played_cards(self.MPlayedCardsPos)
                if len(cards) > 0:
                    time.sleep(0.5)
                    cards = self.find_played_cards(self.MPlayedCardsPos)
                if len(cards) == 0:

                    action_message, action_list = self.env.step(self.user_position, update=False)
                    score = float(action_message['win_rate'])
                    if "resnet" in self.model_path_dict[self.user_position]:
                        score *= 8
                    hand_cards_str = ''.join(
                        [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])
                    action_list = action_list[:3]
                    if not self.winrate:
                        self.winrate = 0
                    self.bid_display.emit("当前得分：" + str(round(float(action_list[0][1]), 3)))
                    self.pre_cards_display.emit(action_message["action"] if action_message["action"] else "pass")
                    action_list_str = " | ".join([ainfo[0] + " = " + ainfo[1] for ainfo in action_list])
                    print(action_list_str)
                    self.winrate_display.emit(action_list_str)

                    if self.auto_sign:
                        if first_run:
                            self.initial_model_rate = round(float(action_message["win_rate"]), 3)  # win_rate at start
                        if action_message["action"] == "":
                            self.env.step(self.user_position, [])
                            hand_cards_str = ''.join(
                                [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])
                            print("出牌:", "Pass", "| 得分:", round(action_message["win_rate"], 4), "| 剩余手牌:",
                                  hand_cards_str)

                            pass_btn = helper.LocateOnScreen("pass_btn", region=self.PassBtnPos, confidence=0.7)
                            yaobuqi = helper.LocateOnScreen("yaobuqi", region=self.GeneralBtnPos, confidence=0.7)
                            buchu = helper.LocateOnScreen("buchu", region=self.MPassPos)
                            while pass_btn is None and yaobuqi is None and buchu is None:
                                if not self.RunGame or not self.auto_sign:
                                    break
                                pass_btn = helper.LocateOnScreen("pass_btn", region=self.PassBtnPos, confidence=0.7)
                                yaobuqi = helper.LocateOnScreen("yaobuqi", region=self.GeneralBtnPos, confidence=0.7)
                                buchu = helper.LocateOnScreen("buchu", region=self.MPassPos)
                                self.detect_start_btn()

                            if not self.my_pass_sign:
                                if pass_btn is not None:
                                    helper.ClickOnImage("pass_btn", region=self.PassBtnPos, confidence=0.7)
                                if yaobuqi is not None:
                                    helper.ClickOnImage("yaobuqi", region=self.GeneralBtnPos, confidence=0.7)
                                if buchu is not None:
                                    print("你们太牛X！ 我要不起")
                                    time.sleep(0.5)
                                time.sleep(0.2)
                            else:
                                self.my_pass_sign = False
                            time.sleep(0.1)
                        else:
                            self.click_cards(action_message["action"])
                            play_card = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.7)
                            while play_card is None:
                                if not self.RunGame or not self.auto_sign:
                                    break
                                time.sleep(0.2)
                                play_card = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.7)
                                self.detect_start_btn()
                            if first_run:
                                time.sleep(0.5)
                            try:
                                helper.ClickOnImage("play_card", region=self.PassBtnPos, confidence=0.7)
                            except Exception as e:
                                print("没找到出牌按钮")
                            print("点击出牌按钮")
                            time.sleep(0.2)
                            play_card = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.7)
                            if play_card is not None:
                                self.click_cards(action_message["action"])
                                time.sleep(0.5)
                                helper.ClickOnImage("play_card", region=self.PassBtnPos, confidence=0.7)

                            self.my_played_cards_env = [RealCard2EnvCard[c] for c in list(action_message["action"])]
                            self.my_played_cards_env.sort()
                            self.env.step(self.user_position, self.my_played_cards_env)

                            hand_cards_str = ''.join(
                                [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])
                            print("出牌:", action_message["action"] if action_message["action"] else "Pass", "| 得分:",
                                  round(action_message["win_rate"], 4), "| 剩余手牌:", hand_cards_str)

                            if action_message["action"] == "DX":
                                time.sleep(0.1)
                            ani = self.animation(action_message["action"])
                            if ani:
                                time.sleep(0.5)

                            if len(hand_cards_str) == 0:
                                self.RunGame = False
                                try:
                                    if self.env is not None:
                                        self.env.game_over = True
                                        self.env.reset()
                                    self.init_interface.emit(1)

                                except AttributeError as e:
                                    traceback.print_exc()
                                    print("程序走到这里")
                                    time.sleep(1)
                                break
                        hand_cards_str = ''.join(
                            [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])
                        # print("炸弹数量：", self.env.info_sets[self.user_position].player_hand_cards)
                        if len(hand_cards_str) == 4 and self.env.info_sets[
                            self.user_position].player_hand_cards in bombs:
                            if self.user_position == "landlord_up":
                                give_coffee("left")
                            elif self.user_position == "landlord_down":
                                give_coffee("right")
                            time.sleep(1)
                        if len(hand_cards_str) == 2 and self.user_position != "landlord":
                            if hand_cards_str[0] == hand_cards_str[1]:
                                send_GG_and_MM()
                                time.sleep(0.5)
                            else:
                                give_thumb()
                                time.sleep(0.5)

                    if not self.auto_sign:
                        print("现在是手动模式，请手动出牌")
                        play_sound("music/1.wav")
                        if action_message["action"] == "":
                            self.pre_cards_display.emit("推荐：pass")
                        else:
                            self.pre_cards_display.emit(f"推荐：" + action_message["action"])
                        pass_flag = helper.LocateOnScreen('buchu', region=self.MPassPos)
                        centralCards = self.find_played_cards(self.MPlayedCardsPos)
                        print("等待自己出牌", end="")
                        while len(centralCards) == 0 and pass_flag is None:
                            if not self.RunGame or self.auto_sign or self.env.game_over:
                                break
                            print(".", end="")
                            time.sleep(0.2)
                            have_ani = self.waitUntilNoAnimation()
                            if have_ani:
                                self.pre_cards_display.emit("等待动画")
                                time.sleep(0.2)
                            pass_flag = helper.LocateOnScreen('buchu', region=self.MPassPos)
                            centralCards = self.find_played_cards(self.MPlayedCardsPos)
                            self.detect_start_btn()

                        if pass_flag is None:
                            while True:
                                if not self.RunGame or self.auto_sign:
                                    break
                                centralOne = self.find_played_cards(self.MPlayedCardsPos)
                                time.sleep(0.3)
                                centralTwo = self.find_played_cards(self.MPlayedCardsPos)
                                if centralOne == centralTwo and len(centralOne) > 0:
                                    self.my_played_cards_real = centralOne
                                    if ("X" in centralOne or "D" in centralOne) and not ("DX" in centralOne):
                                        time.sleep(0.5)
                                        self.my_played_cards_real = self.find_played_cards(self.MPlayedCardsPos)
                                        if len(self.my_played_cards_real) == 0:
                                            self.my_played_cards_real = centralOne
                                    break
                                self.detect_start_btn()
                        else:
                            self.my_played_cards_real = ""
                        print("\n自己出牌：", self.my_played_cards_real if self.my_played_cards_real else "pass")
                        self.my_played_cards_env = [RealCard2EnvCard[c] for c in list(self.my_played_cards_real)]
                        self.my_played_cards_env.sort()
                        action_message, _ = self.env.step(self.user_position, self.my_played_cards_env)
                        hand_cards_str = ''.join(
                            [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])

                        print("出牌:", action_message["action"] if action_message["action"] else "Pass", "| 得分:",
                              round(action_message["win_rate"], 4), "| 剩余手牌:", hand_cards_str)

                        self.pre_cards_display.emit(self.my_played_cards_real if self.my_played_cards_real else "pass")
                    time.sleep(0.5)
                    self.play_order = 1
                else:
                    print("已经出过牌")
                    time.sleep(0.5)
                    self.play_order = 1
                first_run = False
                self.detect_start_btn()
            self.detect_start_btn()

            if self.play_order == 1:
                self.right_cards_display.emit("等待下家出牌")

                pass_flag = helper.LocateOnScreen('buchu', region=self.RPassPos)
                rightCards = self.find_other_cards(self.RPlayedCardsPos)
                print("等待下家出牌", end="")

                while len(rightCards) == 0 and pass_flag is None:
                    if not self.RunGame:
                        break
                    print(".", end="")
                    time.sleep(0.2)
                    have_ani = self.waitUntilNoAnimation()
                    if have_ani:
                        self.right_cards_display.emit("等待动画")
                        time.sleep(0.2)
                    pass_flag = helper.LocateOnScreen('buchu', region=self.RPassPos)
                    rightCards = self.find_other_cards(self.RPlayedCardsPos)
                    self.detect_start_btn()

                if pass_flag is None:
                    while True:
                        if not self.RunGame:
                            break
                        rightOne = self.find_other_cards(self.RPlayedCardsPos)
                        time.sleep(0.3)
                        rightTwo = self.find_other_cards(self.RPlayedCardsPos)

                        if rightOne == rightTwo and len(rightOne) > 0:
                            self.other_played_cards_real = rightOne
                            if "X" in rightOne or "D" in rightOne and not ("DX" in rightOne):
                                time.sleep(0.5)
                                self.other_played_cards_real = self.find_other_cards(self.RPlayedCardsPos)
                                if len(self.other_played_cards_real) == 0:
                                    self.other_played_cards_real = rightOne
                            break
                        else:
                            pass_flag = helper.LocateOnScreen('buchu', region=self.RPassPos)
                            if pass_flag is not None:
                                self.other_played_cards_real = ""
                                break
                        self.detect_start_btn()
                else:
                    self.other_played_cards_real = ""
                print("\n下家出牌：", self.other_played_cards_real if self.other_played_cards_real else "pass")
                self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
                self.other_played_cards_env.sort()
                self.env.step(self.user_position, self.other_played_cards_env)

                self.right_cards_display.emit(self.other_played_cards_real if self.other_played_cards_real else "pass")
                self.other_hands_cards_str = subtract_strings(self.other_hands_cards_str, self.other_played_cards_real)
                self.recorder_display.emit(self.other_hands_cards_str)
                time.sleep(0.2)
                self.play_order = 2

            if self.play_order == 2:
                self.left_cards_display.emit("等待上家出牌")

                pass_flag = helper.LocateOnScreen('buchu', region=self.LPassPos)
                leftCards = self.find_other_cards(self.LPlayedCardsPos)
                print("等待上家出牌", end="")
                while len(leftCards) == 0 and pass_flag is None:
                    if not self.RunGame:
                        break
                    print(".", end="")
                    time.sleep(0.2)
                    have_ani = self.waitUntilNoAnimation()
                    if have_ani:
                        self.left_cards_display.emit("等待动画")
                        time.sleep(0.2)
                    pass_flag = helper.LocateOnScreen('buchu', region=self.LPassPos)
                    leftCards = self.find_other_cards(self.LPlayedCardsPos)
                    self.detect_start_btn()

                if pass_flag is None:
                    while True:
                        if not self.RunGame:
                            break
                        leftOne = self.find_other_cards(self.LPlayedCardsPos)
                        time.sleep(0.3)
                        leftTwo = self.find_other_cards(self.LPlayedCardsPos)
                        if leftOne == leftTwo and len(leftOne) > 0:
                            self.other_played_cards_real = leftOne
                            if ("X" in leftOne or "D" in leftOne) and not ("DX" in leftOne):
                                time.sleep(0.5)
                                self.other_played_cards_real = self.find_other_cards(self.LPlayedCardsPos)
                                if len(self.other_played_cards_real) == 0:
                                    self.other_played_cards_real = leftOne
                            break
                        else:
                            pass_flag = helper.LocateOnScreen('buchu', region=self.LPassPos)
                            if pass_flag is not None:
                                self.other_played_cards_real = ""
                                break
                        self.detect_start_btn()
                else:
                    self.other_played_cards_real = ""
                print("\n上家出牌：", self.other_played_cards_real if self.other_played_cards_real else "pass")
                self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
                self.other_played_cards_env.sort()
                self.env.step(self.user_position, self.other_played_cards_env)

                self.left_cards_display.emit(self.other_played_cards_real if self.other_played_cards_real else "pass")
                self.other_hands_cards_str = subtract_strings(self.other_hands_cards_str,
                                                              self.other_played_cards_real)
                self.recorder_display.emit(self.other_hands_cards_str)
                time.sleep(0.05)
                self.play_order = 0

        if not self.loop_sign:
            self.stop.emit(1)
            print("游戏结束")
        self.state_display.emit("游戏结束")
        self.init_interface.emit(1)
        print("本局已结束")
        print()
        time.sleep(5)

    def find_cards(self, img, pos, mark="", confidence=0.8):
        cards_real = ""
        D_king = 0
        X_king = 0
        for card in AllCards:
            result = gh.LocateAllOnImage(img, helper.PicsCV[mark + card], region=pos, confidence=confidence)

            if len(result) > 0:
                count, s = cards_filter(list(result), self.distance)
                if card == "X" or card == "D":
                    for a in s:
                        classifier = DC.ColorClassify(debug=True)
                        img1 = img[pos[1]:pos[1] + pos[3], pos[0]:pos[0] + pos[2]]
                        img2 = img1[a[1]:a[1] + a[3] - 50, a[0]:a[0] + 20]  # 注意连着裁切时img不能重名
                        result = classifier.classify(img2)
                        for b in result:
                            if b[0] == "Red":
                                if b[1] > 0.7:
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
        img, _ = helper.Screenshot()
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        my_cards_real = self.find_cards(img, self.MyHandCardsPos, mark="m")
        return my_cards_real

    def find_other_cards(self, pos):
        img, _ = helper.Screenshot()
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        other_cards_real = self.find_cards(img, pos, mark="o")
        return other_cards_real

    def find_played_cards(self, pos):
        img, _ = helper.Screenshot()
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        other_cards_real = self.find_cards(img, pos, mark="c")
        return other_cards_real

    def find_three_cards(self):
        img, _ = helper.Screenshot()
        img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        landlord__cards_real = self.find_cards(img, self.LandlordCardsPos, mark="z")
        return landlord__cards_real

    def click_cards(self, out_cards):
        try:
            cards = self.find_my_cards()
            num = len(cards)
            space = 45.6
            res1 = helper.LocateOnScreen("up_left", region=self.MyHandCardsPos, confidence=0.65)
            while res1 is None:
                if not self.RunGame:
                    break
                print("未找到手牌区域")
                time.sleep(0.5)
                res1 = helper.LocateOnScreen("up_left", region=self.MyHandCardsPos, confidence=0.65)
                self.detect_start_btn()
            pos = res1[0] + 6, res1[1] + 7

            res2 = helper.LocateOnScreen("up_left", region=(180, 580, 1050, 90), confidence=0.65)
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
                time.sleep(0.5)

            else:
                for i in out_cards:
                    cars_pos = cards_dict[i][-1][0:2]

                    # print("准备点击的牌：", cards_dict[i])
                    point = cars_pos[0] + 20, cars_pos[1] + 100
                    img, _ = helper.Screenshot()
                    img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
                    check_one = self.find_cards(img=img, pos=(cars_pos[0] - 2, 565, 60, 60), mark="m", confidence=0.8)
                    # print("系统帮你点的牌：", check_one, "你要出的牌：", i)

                    if check_one == i and check_one != "D" and check_one != "X":
                        print("腾讯自动帮你选牌：", check_one)

                    else:
                        helper.LeftClick2(point)
                        # print(point)
                        time.sleep(0.1)
                    remove_dict[i].append(cards_dict[i][-1])
                    cards_dict[i].remove(cards_dict[i][-1])
                    # print("remove_dict", remove_dict)
                img, _ = helper.Screenshot()
                img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
                check_cards = self.find_cards(img, (180, 590, 1050, 90), mark="m")
                for i in out_cards:
                    cards = cards.replace(i, "", 1)
                # print("检查剩的牌： ", check_cards, "应该剩的牌： ", cards)
                if len(check_cards) < len(cards):
                    for m in check_cards:
                        cards = cards.replace(m, "", 1)
                    # print("系统多点的牌： ", cards)
                    for n in cards:
                        # print("字典里还剩的牌： ", cards_dict)
                        cars_pos2 = cards_dict[n][-1][0:2]
                        # print("准备点回来的牌：", cars_pos2)
                        point2 = cars_pos2[0] + 20, cars_pos2[1] + 100
                        helper.LeftClick2(point2)
                        time.sleep(0.1)
                        remove_dict[n].append(cards_dict[n][-1])
                        cards_dict[n].remove(cards_dict[n][-1])
                elif len(check_cards) > len(cards):
                    for m in cards:
                        check_cards = check_cards.replace(m, "", 1)
                    # print("系统少点的牌： ", check_cards)
                    for n in check_cards:
                        # print("删除的字典： ", remove_dict)
                        cars_pos3 = remove_dict[n][0][0:2]
                        # print("准备再点出去的牌：", cars_pos3)
                        point3 = cars_pos3[0] + 20, cars_pos3[1] + 100
                        helper.LeftClick2(point3)
                        time.sleep(0.3)
                        remove_dict[n].remove(remove_dict[n][0])
                        # print(remove_dict)
        except Exception as e:
            print("检测到出牌错误")
            traceback.print_exc()
        time.sleep(0.2)

    def find_landlord(self):
        my_cards = self.find_my_cards()
        if len(my_cards) == 17:
            left_cards = self.find_other_cards(self.LPlayedCardsPos)
            right_cards = self.find_other_cards(self.RPlayedCardsPos)
            if len(left_cards) > 0:
                return 2
            elif len(right_cards) > 0:
                return 0
        elif len(my_cards) == 20:
            return 1

    def animation(self, cards):
        move_type = get_move_type(real_to_env(cards))
        animation_types = {4, 5, 13, 14, 8, 9, 10, 11, 12}
        if move_type["type"] in animation_types or len(cards) >= 6:
            return True

    def waitUntilNoAnimation(self, ms=0.1):
        ani = self.haveAnimation(ms)
        if ani:
            print("\n检测到炸弹、顺子、飞机 Biu~~ Biu~~  Bomb!!! Bomb!!!")
            return True
        return False

    def haveAnimation(self, waitTime=0.1):
        regions = [
            (960, 160, 960 + 20, 160 + 20),  # 下家动画位置
            (485, 160, 485 + 20, 160 + 20),  # 上家动画位置
            (700, 400, 700 + 20, 400 + 20),  # 自己上方动画位置
        ]
        img, _ = helper.Screenshot()
        lastImg = img
        for i in range(2):
            time.sleep(waitTime)
            img, _ = helper.Screenshot()
            for region in regions:
                if compareImage(img.crop(region), lastImg.crop(region)):
                    return True
            lastImg = img

        return False


class MyPyQT_Form(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super(MyPyQT_Form, self).__init__()
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint |  # 使能最小化按钮
                            QtCore.Qt.WindowStaysOnTopHint |  # 窗体总在最前端
                            QtCore.Qt.WindowCloseButtonHint)
        self.setWindowIcon(QIcon(':/pics/favicon.ico'))
        self.setWindowTitle("DouZero欢乐斗地主  v5.7")
        play_sound("music/2.wav")
        self.setFixedSize(self.width(), self.height())  # 固定窗体大小
        self.move(20, 20)
        window_pale = QtGui.QPalette()

        self.setPalette(window_pale)
        self.setWindowOpacity(1)
        self.HandButton.clicked.connect(self.hand_game)
        self.AutoButton.clicked.connect(self.auto_game)
        self.StopButton.clicked.connect(self.stop)
        self.ResetButton.clicked.connect(self.init_threshold)
        self.ClassicsButton.setStyleSheet('background-color: rgba(255, 170, 0, 0.5);')

        self.read_threshold()
        self.Players = [self.RPlayedCard, self.PredictedCard, self.LPlayedCard]
        self.thread = Worker()
        self.thread.change_mode = False
        self.ClassicsButton.setStyleSheet('background-color: rgba(255, 170, 0, 0.5);')
        self.thread.auto_game.connect(self.auto_game)
        self.thread.hand_game.connect(self.hand_game)
        self.thread.init_interface.connect(self.init_interface)
        self.thread.player_display.connect(self.player_display)
        self.thread.state_display.connect(self.state_display)
        self.thread.three_cards_display.connect(self.three_cards_display)
        self.thread.bid_display.connect(self.bid_display)
        self.thread.pre_display.connect(self.pre_display)
        self.thread.stop.connect(self.stop)
        self.thread.winrate_display.connect(self.winrate_display)
        self.thread.pre_cards_display.connect(self.pre_cards_display)
        self.thread.left_cards_display.connect(self.left_cards_display)
        self.thread.right_cards_display.connect(self.right_cards_display)
        self.thread.recorder_display.connect(self.cards_recorder)
        self.thread.write_threshold.connect(self.write_threshold)

    def hand_game(self, result):
        self.thread.auto_sign = False
        self.thread.start()
        self.AutoButton.setStyleSheet('background-color: none;')
        self.HandButton.setStyleSheet('background-color: rgba(255, 85, 255, 0.5);')

    def auto_game(self, result):
        self.thread.auto_sign = True
        self.thread.start()

        self.AutoButton.setStyleSheet('background-color: rgba(255, 85, 255, 0.5);')
        self.HandButton.setStyleSheet('background-color: none;')

    def stop(self, result):
        print()
        print("停止线程")
        self.thread.terminate()
        self.init_interface(1)
        self.AutoButton.setStyleSheet('background-color: none;')
        self.HandButton.setStyleSheet('background-color: none;')

    def player_display(self, result):
        for player in self.Players:
            player.setStyleSheet('background-color: rgba(0, 255, 0, 0);')
        self.Players[result].setStyleSheet('background-color: rgba(0, 255, 0, 0.5);')

    def init_threshold(self):
        self.bid_lineEdit_1.setText("0.2")
        self.bid_lineEdit_2.setText("0.4")
        self.bid_lineEdit_3.setText("0.5")
        self.jiabei_lineEdit_1.setText("0.5")
        self.jiabei_lineEdit_2.setText("0.4")
        self.jiabei_lineEdit_3.setText("0.6")
        self.jiabei_lineEdit_4.setText("0.5")
        self.jiabei_lineEdit_5.setText("1.3")
        self.jiabei_lineEdit_6.setText("1.1")
        self.jiabei_lineEdit_7.setText("1.2")
        self.jiabei_lineEdit_8.setText("1.0")
        self.mingpai_lineEdit.setText("1.5")

        data = {'bid1': self.bid_lineEdit_1.text(), 'bid2': self.bid_lineEdit_2.text(),
                'bid3': self.bid_lineEdit_3.text(), 'jiabei1': self.jiabei_lineEdit_1.text(),
                'jiabei2': self.jiabei_lineEdit_2.text(), 'jiabei3': self.jiabei_lineEdit_3.text(),
                'jiabei4': self.jiabei_lineEdit_4.text(), 'jiabei5': self.jiabei_lineEdit_5.text(),
                'jiabei6': self.jiabei_lineEdit_6.text(), 'jiabei7': self.jiabei_lineEdit_7.text(),
                'jiabei8': self.jiabei_lineEdit_8.text(), 'mingpai': self.mingpai_lineEdit.text()}
        write_json(data)

    def write_threshold(self, result):
        data = {'bid1': self.bid_lineEdit_1.text(), 'bid2': self.bid_lineEdit_2.text(),
                'bid3': self.bid_lineEdit_3.text(), 'jiabei1': self.jiabei_lineEdit_1.text(),
                'jiabei2': self.jiabei_lineEdit_2.text(), 'jiabei3': self.jiabei_lineEdit_3.text(),
                'jiabei4': self.jiabei_lineEdit_4.text(), 'jiabei5': self.jiabei_lineEdit_5.text(),
                'jiabei6': self.jiabei_lineEdit_6.text(), 'jiabei7': self.jiabei_lineEdit_7.text(),
                'jiabei8': self.jiabei_lineEdit_8.text(), 'mingpai': self.mingpai_lineEdit.text()}
        write_json(data)

    def read_threshold(self):
        data = read_json()
        self.bid_lineEdit_1.setText(data['bid1'])
        self.bid_lineEdit_2.setText(data['bid2'])
        self.bid_lineEdit_3.setText(data['bid3'])
        self.jiabei_lineEdit_1.setText(data['jiabei1'])
        self.jiabei_lineEdit_2.setText(data['jiabei2'])
        self.jiabei_lineEdit_3.setText(data['jiabei3'])
        self.jiabei_lineEdit_4.setText(data['jiabei4'])
        self.jiabei_lineEdit_5.setText(data['jiabei5'])
        self.jiabei_lineEdit_6.setText(data['jiabei6'])
        self.jiabei_lineEdit_7.setText(data['jiabei7'])
        self.jiabei_lineEdit_8.setText(data['jiabei8'])
        self.mingpai_lineEdit.setText(data['mingpai'])

    def init_interface(self, result):
        self.WinRate.setText("评分")
        self.WinRate.setStyleSheet('background-color: none;')
        self.label.setText("游戏状态")
        self.BidWinrate.setText("叫牌得分")
        self.PreWinrate.setText("局前得分")
        self.label.setStyleSheet('background-color: none;')
        self.LPlayedCard.setText("上家出牌区域")
        self.RPlayedCard.setText("下家出牌区域")
        self.PredictedCard.setText("AI出牌区域")
        self.ThreeLandlordCards.setText("底牌")
        self.recorder2zero()
        for player in self.Players:
            player.setStyleSheet('background-color: none;')

    def state_display(self, result):
        self.label.setText(result)
        self.label.setStyleSheet('background-color: rgba(255, 0, 0, 0.5);')

    def three_cards_display(self, result):
        self.ThreeLandlordCards.setText(result)

    def bid_display(self, result):
        self.BidWinrate.setText(result)

    def pre_display(self, result):
        self.PreWinrate.setText(result)

    def pre_cards_display(self, result):
        self.PredictedCard.setText(result)
        self.PredictedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0.5);')
        self.LPlayedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0);')
        self.RPlayedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0);')

    def left_cards_display(self, result):
        self.LPlayedCard.setText(result)
        self.PredictedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0);')
        self.LPlayedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0.5);')
        self.RPlayedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0);')

    def right_cards_display(self, result):
        self.RPlayedCard.setText(result)
        self.PredictedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0);')
        self.LPlayedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0);')
        self.RPlayedCard.setStyleSheet('background-color: rgba(0, 255, 0, 0.5);')

    def winrate_display(self, result):
        self.WinRate.setText(result)
        self.WinRate.setStyleSheet('background-color: rgba(255, 85, 0, 0.4);')

    def cards_recorder(self, result):
        for i in range(15):
            char = AllCards[i]
            num = result.count(char)
            newItem = QTableWidgetItem(str(num))
            newItem.setTextAlignment(Qt.AlignHCenter)
            self.tableWidget.setItem(0, i, newItem)

    def recorder2zero(self):
        for i in range(15):
            newItem = QTableWidgetItem("0")
            newItem.setTextAlignment(Qt.AlignHCenter)
            self.tableWidget.setItem(0, i, newItem)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    main = MyPyQT_Form()
    style_file = QFile("style.qss")
    stream = QTextStream(style_file)
    style_sheet = stream.readAll()
    main.setStyleSheet(style_sheet)
    main.show()
    sys.exit(app.exec_())

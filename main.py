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

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsPixmapItem, QInputDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QIcon
from PyQt5.QtCore import QTime, QEventLoop
from MainWindow import Ui_Form

from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent

import BidModel
import LandlordModel
import FarmerModel

EnvCard2RealCard = {3: '3', 4: '4', 5: '5', 6: '6', 7: '7',
                    8: '8', 9: '9', 10: 'T', 11: 'J', 12: 'Q',
                    13: 'K', 14: 'A', 17: '2', 20: 'X', 30: 'D'}

RealCard2EnvCard = {'3': 3, '4': 4, '5': 5, '6': 6, '7': 7,
                    '8': 8, '9': 9, 'T': 10, 'J': 11, 'Q': 12,
                    'K': 13, 'A': 14, '2': 17, 'X': 20, 'D': 30}

AllEnvCard = [3, 3, 3, 3, 4, 4, 4, 4, 5, 5, 5, 5, 6, 6, 6, 6, 7, 7, 7, 7,
              8, 8, 8, 8, 9, 9, 9, 9, 10, 10, 10, 10, 11, 11, 11, 11, 12,
              12, 12, 12, 13, 13, 13, 13, 14, 14, 14, 14, 17, 17, 17, 17, 20, 30]

AllCards = ['rD', 'bX', 'b2', 'r2', 'bA', 'rA', 'bK', 'rK', 'bQ', 'rQ', 'bJ', 'rJ', 'bT', 'rT',
            'b9', 'r9', 'b8', 'r8', 'b7', 'r7', 'b6', 'r6', 'b5', 'r5', 'b4', 'r4', 'b3', 'r3']

helper = GameHelper()
helper.ScreenZoomRate = 1.25  # 请修改屏幕缩放比

class MyPyQT_Form(QtWidgets.QWidget, Ui_Form):
    def __init__(self):
        super(MyPyQT_Form, self).__init__()
        self.setupUi(self)
        self.setWindowFlags(QtCore.Qt.WindowMinimizeButtonHint |  # 使能最小化按钮
                            QtCore.Qt.WindowCloseButtonHint)  # 窗体总在最前端 QtCore.Qt.WindowStaysOnTopHint
        self.setFixedSize(self.width(), self.height())  # 固定窗体大小
        # self.setWindowIcon(QIcon('pics/favicon.ico'))
        window_pale = QtGui.QPalette()
        # window_pale.setBrush(self.backgroundRole(), QtGui.QBrush(QtGui.QPixmap("pics/bg.png")))
        self.setPalette(window_pale)
        self.Players = [self.RPlayer, self.Player, self.LPlayer]
        self.counter = QTime()

        # 参数
        self.MyConfidence = 0.95  # 我的牌的置信度
        self.OtherConfidence = 0.9  # 别人的牌的置信度
        self.WhiteConfidence = 0.95  # 检测白块的置信度
        self.LandlordFlagConfidence = 0.9  # # 检测地主标志的置信度
        self.ThreeLandlordCardsConfidence = 0.9  # 检测地主底牌的置信度
        self.PassConfidence = 0.85
        self.WaitTime = 1  # 等待状态稳定延时
        self.MyFilter = 40  # 我的牌检测结果过滤参数
        self.OtherFilter = 25  # 别人的牌检测结果过滤参数
        self.SleepTime = 0.1  # 循环中睡眠时间
        self.RunGame = False
        self.AutoPlay = False
        # 坐标
        self.MyHandCardsPos = (250, 764, 1141, 70)  # 我的截图区域
        self.LPlayedCardsPos = (463, 355, 380, 250)  # 左边截图区域
        self.RPlayedCardsPos = (946, 355, 380, 250)  # 右边截图区域
        self.LandlordFlagPos = [(1281, 276, 110, 140), (267, 695, 110, 140), (424, 237, 110, 140)]  # 地主标志截图区域(右-我-左)
        self.ThreeLandlordCardsPos = (763, 37, 287, 136)  # 地主底牌截图区域，resize成349x168
        self.PassBtnPos = (686, 659, 419, 100)
        self.GeneralBtnPos = (616, 631, 576, 117)
        # 信号量
        self.shouldExit = 0  # 通知上一轮记牌结束
        self.canRecord = threading.Lock()  # 开始记牌
        self.card_play_model_path_dict = {
            'landlord': "baselines/douzero_ADP/landlord.ckpt",
            'landlord_up': "baselines/douzero_ADP/landlord_up.ckpt",
            'landlord_down': "baselines/douzero_ADP/landlord_down.ckpt"
        }
        # cards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
        # print(cards)
        # exit()

    def init_display(self):
        self.WinRate.setText("评分")
        self.InitCard.setText("开始")
        self.UserHandCards.setText("手牌")
        self.LPlayedCard.setText("上家出牌区域")
        self.RPlayedCard.setText("下家出牌区域")
        self.PredictedCard.setText("AI出牌区域")
        self.ThreeLandlordCards.setText("地主牌")
        self.SwitchMode.setText("自动" if self.AutoPlay else "单局")
        for player in self.Players:
            player.setStyleSheet('background-color: rgba(255, 0, 0, 0);')

    def switch_mode(self):
        self.AutoPlay = not self.AutoPlay
        self.SwitchMode.setText("自动" if self.AutoPlay else "单局")

    def init_cards(self):
        self.RunGame = True
        GameHelper.Interrupt = False
        self.init_display()
        # 玩家手牌
        self.user_hand_cards_real = ""
        self.user_hand_cards_env = []
        # 其他玩家出牌
        self.other_played_cards_real = ""
        self.other_played_cards_env = []
        # 其他玩家手牌（整副牌减去玩家手牌，后续再减掉历史出牌）
        self.other_hand_cards = []
        # 三张底牌
        self.three_landlord_cards_real = ""
        self.three_landlord_cards_env = []
        # 玩家角色代码：0-地主上家, 1-地主, 2-地主下家
        self.user_position_code = None
        self.user_position = ""
        # 开局时三个玩家的手牌
        self.card_play_data_list = {}
        # 出牌顺序：0-玩家出牌, 1-玩家下家出牌, 2-玩家上家出牌
        self.play_order = 0

        self.env = None

        # 识别玩家手牌
        self.user_hand_cards_real = self.find_my_cards(self.MyHandCardsPos)
        self.UserHandCards.setText(self.user_hand_cards_real)
        self.user_hand_cards_env = [RealCard2EnvCard[c] for c in list(self.user_hand_cards_real)]
        # 识别三张底牌
        self.three_landlord_cards_real = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
        self.ThreeLandlordCards.setText("底牌：" + self.three_landlord_cards_real)
        self.three_landlord_cards_env = [RealCard2EnvCard[c] for c in list(self.three_landlord_cards_real)]
        for testCount in range(1, 5):
            if len(self.three_landlord_cards_env) > 3:
                self.ThreeLandlordCardsConfidence += 0.05
            elif len(self.three_landlord_cards_env) < 3:
                self.ThreeLandlordCardsConfidence -= 0.05
            else:
                break
            self.three_landlord_cards_real = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
            self.ThreeLandlordCards.setText("底牌：" + self.three_landlord_cards_real)
            self.three_landlord_cards_env = [RealCard2EnvCard[c] for c in list(self.three_landlord_cards_real)]
        # 识别玩家的角色
        self.user_position_code = self.find_landlord(self.LandlordFlagPos)
        if self.user_position_code is None:
            items = ("地主上家", "地主", "地主下家")
            item, okPressed = QInputDialog.getItem(self, "选择角色", "未识别到地主，请手动选择角色:", items, 0, False)
            if okPressed and item:
                self.user_position_code = items.index(item)
            else:
                return
        self.user_position = ['landlord_up', 'landlord', 'landlord_down'][self.user_position_code]
        for player in self.Players:
            player.setStyleSheet('background-color: rgba(255, 0, 0, 0);')
        self.Players[self.user_position_code].setStyleSheet('background-color: rgba(255, 0, 0, 0.1);')

        # 整副牌减去玩家手上的牌，就是其他人的手牌,再分配给另外两个角色（如何分配对AI判断没有影响）
        for i in set(AllEnvCard):
            self.other_hand_cards.extend([i] * (AllEnvCard.count(i) - self.user_hand_cards_env.count(i)))
        self.card_play_data_list.update({
            'three_landlord_cards': self.three_landlord_cards_env,
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 0) % 3]:
                self.user_hand_cards_env,
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 1) % 3]:
                self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 != 1 else self.other_hand_cards[17:],
            ['landlord_up', 'landlord', 'landlord_down'][(self.user_position_code + 2) % 3]:
                self.other_hand_cards[0:17] if (self.user_position_code + 1) % 3 == 1 else self.other_hand_cards[17:]
        })
        print("开始对局")
        print("手牌:",self.user_hand_cards_real)
        print("地主牌:",self.three_landlord_cards_real)
        # 生成手牌结束，校验手牌数量
        if len(self.card_play_data_list["three_landlord_cards"]) != 3:
            QMessageBox.critical(self, "底牌识别出错", "底牌必须是3张！", QMessageBox.Yes, QMessageBox.Yes)
            self.init_display()
            return
        if len(self.card_play_data_list["landlord_up"]) != 17 or \
                len(self.card_play_data_list["landlord_down"]) != 17 or \
                len(self.card_play_data_list["landlord"]) != 20:
            QMessageBox.critical(self, "手牌识别出错", "初始手牌数目有误", QMessageBox.Yes, QMessageBox.Yes)
            self.init_display()
            return
        # 得到出牌顺序
        self.play_order = 0 if self.user_position == "landlord" else 1 if self.user_position == "landlord_up" else 2

        # 创建一个代表玩家的AI
        ai_players = [0, 0]
        ai_players[0] = self.user_position
        ai_players[1] = DeepAgent(self.user_position, self.card_play_model_path_dict[self.user_position])

        self.env = GameEnv(ai_players)
        try:
            self.start()
        except:
            self.stop()

    def sleep(self, ms):
        self.counter.restart()
        while self.counter.elapsed() < ms:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)

    def start(self):
        self.env.card_play_init(self.card_play_data_list)
        print("开始出牌\n")
        while not self.env.game_over:
            # 玩家出牌时就通过智能体获取action，否则通过识别获取其他玩家出牌
            if self.play_order == 0:
                self.PredictedCard.setText("...")
                action_message = self.env.step(self.user_position)
                # 更新界面
                self.UserHandCards.setText("手牌：" + str(''.join(
                    [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards]))[::-1])

                self.PredictedCard.setText(action_message["action"] if action_message["action"] else "不出")
                self.WinRate.setText("评分：" + action_message["win_rate"])
                print("\n手牌：", str(''.join(
                    [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])))
                print("出牌：", action_message["action"] if action_message["action"] else "不出", "， 胜率：",
                      action_message["win_rate"])
                if action_message["action"] == "":
                    helper.ClickOnImage("pass_btn", region=self.PassBtnPos)
                else:
                    helper.SelectCards(action_message["action"])
                    tryCount = 20
                    result = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.85)
                    while result is None and tryCount > 0:
                        if not self.RunGame:
                            break
                        print("等待出牌按钮")
                        self.detect_start_btn()
                        tryCount -= 1
                        result = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.85)
                        self.sleep(100)
                    helper.ClickOnImage("play_card", region=self.PassBtnPos, confidence=0.85)
                self.sleep(2200)
                self.detect_start_btn()
                self.play_order = 1
            elif self.play_order == 1:
                self.RPlayedCard.setText("...")
                pass_flag = helper.LocateOnScreen('pass',
                                                       region=self.RPlayedCardsPos,
                                                       confidence=self.PassConfidence)
                self.detect_start_btn()
                while self.RunGame and self.have_white(self.RPlayedCardsPos) == 0 and pass_flag is None:
                    print("等待下家出牌")
                    self.sleep(100)
                    pass_flag = helper.LocateOnScreen('pass', region=self.RPlayedCardsPos,
                                                           confidence=self.PassConfidence)
                    self.detect_start_btn()
                self.sleep(200)
                # 未找到"不出"
                if pass_flag is None:
                    # 识别下家出牌
                    self.RPlayedCard.setText("等待动画")
                    self.sleep(1200)
                    self.RPlayedCard.setText("识别中")
                    self.other_played_cards_real = self.find_other_cards(self.RPlayedCardsPos)
                    print("下家出牌", self.other_played_cards_real)
                    self.sleep(500)
                # 找到"不出"
                else:
                    self.other_played_cards_real = ""
                print("\n下家出牌：", self.other_played_cards_real)
                self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
                self.env.step(self.user_position, self.other_played_cards_env)
                # 更新界面
                self.RPlayedCard.setText(self.other_played_cards_real if self.other_played_cards_real else "不出")
                self.play_order = 2
                self.sleep(500)
            elif self.play_order == 2:
                self.LPlayedCard.setText("...")
                self.detect_start_btn()
                pass_flag = helper.LocateOnScreen('pass', region=self.LPlayedCardsPos,
                                                       confidence=self.PassConfidence)
                while self.RunGame and self.have_white(self.LPlayedCardsPos) == 0 and pass_flag is None:
                    print("等待上家出牌")
                    self.detect_start_btn()
                    self.sleep(100)
                    pass_flag = helper.LocateOnScreen('pass', region=self.LPlayedCardsPos,
                                                           confidence=self.PassConfidence)
                self.sleep(200)
                # 不出
                # 未找到"不出"
                if pass_flag is None:
                    # 识别上家出牌
                    self.LPlayedCard.setText("等待动画")
                    self.sleep(1200)
                    self.LPlayedCard.setText("识别中")
                    self.other_played_cards_real = self.find_other_cards(self.LPlayedCardsPos)
                # 找到"不出"
                else:
                    self.other_played_cards_real = ""
                print("\n上家出牌：", self.other_played_cards_real)
                self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
                self.env.step(self.user_position, self.other_played_cards_env)
                self.play_order = 0
                # 更新界面
                self.LPlayedCard.setText(self.other_played_cards_real if self.other_played_cards_real else "不出")
                self.sleep(500)
            else:
                pass
            self.sleep(100)

        print("{}胜，本局结束!\n".format("农民" if self.env.winner == "farmer" else "地主"))
        # QMessageBox.information(self, "本局结束", "{}胜！".format("农民" if self.env.winner == "farmer" else "地主"),
        #                         QMessageBox.Yes, QMessageBox.Yes)
        self.detect_start_btn()

    def find_landlord(self, landlord_flag_pos):
        for pos in landlord_flag_pos:
            result = helper.LocateOnScreen("landlord_words", region=pos,
                                                confidence=self.LandlordFlagConfidence)
            if result is not None:
                return landlord_flag_pos.index(pos)
        return None

    def detect_start_btn(self):
        result = helper.LocateOnScreen("change_player_btn", region=(400, 400, 934, 404))
        if result is not None:
            self.RunGame = False
            self.stop()
        result = helper.LocateOnScreen("yes_btn", region=(680, 661, 435, 225))
        if result is not None:
            helper.ClickOnImage("yes_btn", region=(680, 661, 435, 225))
            self.sleep(1000)
        result = helper.LocateOnScreen("get_award_btn", region=(680, 661, 435, 225))
        if result is not None:
            helper.ClickOnImage("get_award_btn", region=(680, 661, 435, 225))
            self.sleep(1000)
        result = helper.LocateOnScreen("yes_btn_sm", region=(669, 583, 468, 100))
        if result is not None:
            helper.ClickOnImage("yes_btn_sm", region=(669, 583, 468, 100))
            self.sleep(200)


    def find_three_landlord_cards(self, pos):
        img, _ = helper.Screenshot()
        img = img.crop((pos[0], pos[1], pos[0] + pos[2], pos[1] + pos[3]))
        img = img.resize((349, 168))
        three_landlord_cards_real = ""
        for card in AllCards:
            result = pyautogui.locateAll(needleImage=helper.Pics['o' + card], haystackImage=img,
                                         confidence=self.ThreeLandlordCardsConfidence)
            three_landlord_cards_real += card[1] * self.cards_filter(list(result), self.OtherFilter)
        if len(three_landlord_cards_real) > 3:
            three_landlord_cards_real = ""
            for card in AllCards:
                result = pyautogui.locateAll(needleImage=helper.Pics['o' + card], haystackImage=img,
                                             confidence=self.ThreeLandlordCardsConfidence + 0.05)
                three_landlord_cards_real += card[1] * self.cards_filter(list(result), self.OtherFilter)
        if len(three_landlord_cards_real) < 3:
            three_landlord_cards_real = ""
            for card in AllCards:
                result = pyautogui.locateAll(needleImage=helper.Pics['o' + card], haystackImage=img,
                                             confidence=self.ThreeLandlordCardsConfidence + 0.1)
                three_landlord_cards_real += card[1] * self.cards_filter(list(result), self.OtherFilter)
        return three_landlord_cards_real

    def find_my_cards(self, pos):
        user_hand_cards_real = ""
        img, _ = helper.Screenshot()
        cards, _ = helper.GetCards(img)
        for c in cards:
            user_hand_cards_real += c[0]
        # for card in AllCards:
        #     result = pyautogui.locateAll(needleImage=helper.Pics['m'+card], haystackImage=img, confidence=self.MyConfidence)
        #     user_hand_cards_real += card[1] * self.cards_filter(list(result), self.MyFilter)
        return user_hand_cards_real

    def find_other_cards(self, pos):
        other_played_cards_real = ""
        self.sleep(500)
        img, _ = helper.Screenshot(region=pos)
        for card in AllCards:
            result = pyautogui.locateAll(needleImage=helper.Pics['o' + card], haystackImage=img,
                                         confidence=self.OtherConfidence)
            other_played_cards_real += card[1] * self.cards_filter(list(result), self.OtherFilter)
        return other_played_cards_real

    def cards_filter(self, location, distance):  # 牌检测结果滤波
        if len(location) == 0:
            return 0
        locList = [location[0][0]]
        count = 1
        for e in location:
            flag = 1  # “是新的”标志
            for have in locList:
                if abs(e[0] - have) <= distance:
                    flag = 0
                    break
            if flag:
                count += 1
                locList.append(e[0])
        return count

    def have_white(self, pos):  # 是否有白块
        img, _ = helper.Screenshot()
        result = pyautogui.locate(needleImage=helper.Pics["white"], haystackImage=img,
                                  region=pos, confidence=self.WhiteConfidence)
        if result is None:
            return 0
        else:
            return 1

    def stop(self):
        try:
            self.RunGame = False
            self.env.game_over = True
            self.env.reset()
            self.init_display()
            self.PreWinrate.setText("局前预估胜率：")
            self.BidWinrate.setText("叫牌预估胜率：")
        except AttributeError as e:
            pass
        if self.AutoPlay:
            play_btn = helper.LocateOnScreen("change_player_btn", region=(400, 400, 934, 404))
            while play_btn is None and self.AutoPlay:
                play_btn = helper.LocateOnScreen("change_player_btn", region=(400, 400, 934, 404))
                self.sleep(100)
            if play_btn is not None:
                helper.LeftClick((play_btn[0], play_btn[1]))
                self.beforeStart()
                img, _ = helper.Screenshot()
                img = gh.DrawRectWithText(img, (play_btn[0], play_btn[1],10,10))
                gh.ShowImg(img)

    def beforeStart(self):
        GameHelper.Interrupt = True
        thresholds = [
            [75, 60],
            [85, 70]
        ]
        while True:
            outterBreak = False
            jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=(765, 663, 116, 50))
            qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=(783, 663, 116, 50))
            jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
            self.detect_start_btn()
            while jiaodizhu_btn is None and qiangdizhu_btn is None and jiabei_btn is None:
                self.detect_start_btn()
                print("等待加倍或叫地主")
                self.sleep(100)
                jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=(765, 663, 116, 50))
                qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=(783, 663, 116, 50))
                jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
            if jiabei_btn is None:
                img, _ = helper.Screenshot()
                cards, _ = helper.GetCards(img)
                cards_str = "".join([card[0] for card in cards])
                win_rate = BidModel.predict(cards_str)
                print("预计叫地主胜率：", win_rate)
                self.BidWinrate.setText("叫牌预估胜率：" + str(round(win_rate, 2)) + "%")
                is_stolen = 0
                if jiaodizhu_btn is not None:
                    if win_rate > 55:
                        helper.ClickOnImage("jiaodizhu_btn", region=(765, 663, 116, 50), confidence=0.9)
                    else:
                        helper.ClickOnImage("bujiao_btn", region=self.GeneralBtnPos)
                elif qiangdizhu_btn is not None:
                    is_stolen = 1
                    if win_rate > 60:
                        helper.ClickOnImage("qiangdizhu_btn", region=(783, 663, 116, 50), confidence=0.9)
                    else:
                        helper.ClickOnImage("buqiang_btn", region=self.GeneralBtnPos)
                else:
                    pass
            else:
                llcards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
                print("地主牌:", llcards)
                img, _ = helper.Screenshot()
                cards, _ = helper.GetCards(img)
                cards_str = "".join([card[0] for card in cards])
                if len(cards_str) == 20:
                    win_rate = LandlordModel.predict(cards_str)
                    self.PreWinrate.setText("局前预估胜率：" + str(round(win_rate, 2)) + "%")
                    print("预估地主胜率:", win_rate)
                else:
                    user_position_code = self.find_landlord(self.LandlordFlagPos)
                    user_position = "up"
                    while user_position_code is None:
                        user_position_code = self.find_landlord(self.LandlordFlagPos)
                        self.sleep(50)
                    user_position = ['up', 'landlord', 'down'][user_position_code]
                    win_rate = FarmerModel.predict(cards_str, llcards, user_position) - 5
                    print("预估农民胜率:", win_rate)
                    self.PreWinrate.setText("局前预估胜率：" + str(round(win_rate, 2)) + "%")
                if win_rate > thresholds[is_stolen][0]:
                    chaojijiabei_btn = helper.LocateOnScreen("chaojijiabei_btn", region=self.GeneralBtnPos)
                    if chaojijiabei_btn is not None:
                        helper.ClickOnImage("chaojijiabei_btn", region=self.GeneralBtnPos)
                    else:
                        helper.ClickOnImage("jiabei_btn", region=self.GeneralBtnPos)
                elif win_rate > thresholds[is_stolen][1]:
                    helper.ClickOnImage("jiabei_btn", region=self.GeneralBtnPos)
                else:
                    helper.ClickOnImage("bujiabei_btn", region=self.GeneralBtnPos)
                outterBreak = True
                break
            if outterBreak:
                break

        llcards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
        while len(llcards) != 3:
            print("等待地主牌", llcards)
            self.sleep(100)
            llcards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)

        self.sleep(4000)
        self.init_cards()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet("""
    QPushButton{
        text-align : center;
        background-color : white;
        font: bold;
        border-color: gray;
        border-width: 2px;
        border-radius: 10px;
        padding: 6px;
        height : 14px;
        border-style: outset;
        font : 14px;
    }
    QPushButton:hover{
        background-color : light gray;
    }
    QPushButton:pressed{
        text-align : center;
        background-color : gray;
        font: bold;
        border-color: gray;
        border-width: 2px;
        border-radius: 10px;
        padding: 6px;
        height : 14px;
        border-style: outset;
        font : 14px;
        padding-left:9px;
        padding-top:9px;
    }
    QComboBox{
        background:transparent;
        border: 1px solid rgba(200, 200, 200, 100);
        font-weight: bold;
    }
    QComboBox:drop-down{
        border: 0px;
    }
    QComboBox QAbstractItemView:item{
        height: 30px;
    }
    QLabel{
        background:transparent;
        font-weight: bold;
    }
    """)
    my_pyqt_form = MyPyQT_Form()
    my_pyqt_form.show()
    sys.exit(app.exec_())

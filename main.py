# -*- coding: utf-8 -*-
# Created by: Raf
# Modify by: Vincentzyx
import collections


import GameHelper as gh
from GameHelper import GameHelper
import sys
import time
import pyautogui
from PIL import Image
import numpy as np
import cv2
import traceback
import warnings

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QTime, QEventLoop
from MainWindow import Ui_Form

from douzero.env.game import GameEnv
from douzero.evaluation.deep_agent import DeepAgent
from douzero.env.move_detector import get_move_type
import BidModel
import LandlordModel
import FarmerModel

warnings.filterwarnings('ignore')


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
helper.ScreenZoomRate = 1.25

def manual_landlord_requirements(cards_str):
    counter = collections.Counter(cards_str)
    if (counter['D'] == 1 and counter['2'] >= 1 and counter["A"] >= 1) \
            or (counter['D'] == 1 and counter['2'] >= 2) \
            or (counter['D'] == 1 and len([key for key in counter if counter[key] == 4]) >= 1) \
            or (counter['D'] == 1 and counter['X'] == 1) \
            or (len([key for key in counter if counter[key] == 4]) >= 2) \
            or (counter["X"] == 1 and ((counter["2"] >= 2) or (counter["2"] >= 2 and counter["A"] >= 2) or (
            counter["2"] >= 2 and len([key for key in counter if counter[key] == 4]) >= 1))) \
            or (counter["2"] >= 2 and len([key for key in counter if counter[key] == 4]) >= 1):
        return True
    else:
        return False


def manual_mingpai_requirements(cards_str):
    counter = collections.Counter(cards_str)
    if (counter['D'] == 1 and counter['2'] >= 2) \
            or (counter['D'] == 1 and counter['2'] >= 1 and counter['X'] == 1) \
            or (counter['D'] == 1 and counter['2'] >= 1 and counter['A'] >= 2) \
            or (len([key for key in counter if counter[key] == 4]) >= 2) \
            or (counter["X"] == 1 and ((counter["2"] >= 2) or (counter["2"] >= 2 and counter["A"] >= 2) or (
            counter["2"] >= 2 and len([key for key in counter if counter[key] == 4]) >= 1))) \
            or ("DX" in cards_str and len([key for key in counter if counter[key] == 4]) >= 1):
        return True
    else:
        return False


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
        self.env = None
        self.counter = QTime()

        # 参数
        self.MyConfidence = 0.95  # 我的牌的置信度
        self.OtherConfidence = 0.89  # 别人的牌的置信度
        self.WhiteConfidence = 0.95  # 检测白块的置信度
        self.LandlordFlagConfidence = 0.85  # # 检测地主标志的置信度
        self.ThreeLandlordCardsConfidence = 0.9  # 检测地主底牌的置信度
        self.PassConfidence = 0.85
        self.WaitTime = 1  # 等待状态稳定延时
        self.MyFilter = 40  # 我的牌检测结果过滤参数
        self.OtherFilter = 25  # 别人的牌检测结果过滤参数
        self.SleepTime = 0.1  # 循环中睡眠时间
        self.RunGame = False
        self.AutoPlay = False
        # ------ 阈值 ------
        self.BidThresholds = [0,  # 叫地主阈值
                              0.3,  # 抢地主阈值 (自己第一个叫地主)
                              0]  # 抢地主阈值 (自己非第一个叫地主)
        self.JiabeiThreshold = (
            (0.3, 0.15),  # 叫地主 超级加倍 加倍 阈值
            (0.5, 0.15)  # 叫地主 超级加倍 加倍 阈值  (在地主是抢来的情况下)
        )
        self.FarmerJiabeiThreshold = (6, 1.2)
        self.MingpaiThreshold = 0.93
        self.stop_when_no_chaojia = True  # 是否在没有超级加倍的时候关闭自动模式
        self.use_manual_landlord_requirements = False  # 手动规则
        self.use_manual_mingpai_requirements = True  # Manual Mingpai
        # ------------------
        # 坐标
        self.landlord_position_code = 0
        self.play_order = 0
        self.MyHandCardsPos = (250, 764, 1141, 70)  # 我的截图区域
        self.LPassPos = (463, 355, 380, 250)  # 左边不出截图区域
        self.RPassPos = (946, 355, 380, 250)  # 右边不出截图区域
        self.LPlayedCardsPos = (463, 392, 327, 90)  # 左边出牌截图区域
        self.RPlayedCardsPos = (936, 392, 337, 90)  # 右边出牌截图区域
        self.LandlordFlagPos = [(1281, 276, 110, 140), (267, 695, 110, 140), (424, 237, 110, 140)]  # 地主标志截图区域(右-我-左)
        self.ThreeLandlordCardsPos = (763, 37, 287, 136)  # 地主底牌截图区域，resize成349x168
        self.PassBtnPos = (686, 659, 419, 100)

        self.GeneralBtnPos = (616, 631, 576, 117)
        self.LastValidPlayCardEnv = []
        self.LastValidPlayPos = 0
        # Game Log Variables
        self.GameRecord = []
        self.game_type = ""
        self.initial_cards = ""
        self.initial_bid_rate = ""
        self.initial_model_rate = ""
        self.initial_mingpai = ""
        self.initial_multiply = ""
        # -------------------
        self.shouldExit = 0  # 通知上一轮记牌结束
        self.card_play_model_path_dict = {
            'landlord': "baselines/resnet/resnet_landlord.ckpt",
            'landlord_up': "baselines/resnet/resnet_landlord_up.ckpt",
            'landlord_down': "baselines/resnet/resnet_landlord_down.ckpt"
        }
        self.card_play_wp_model_path = {
            'landlord': "baselines/douzero_WP/landlord.ckpt",
            'landlord_up': "baselines/douzero_WP/landlord_up.ckpt",
            'landlord_down': "baselines/douzero_WP/landlord_down.ckpt"
        }
        LandlordModel.init_model("baselines/douzero_WP/landlord.ckpt")

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

    def auto_start(self):
        self.game_loop()

    def switch_mode(self):
        self.AutoPlay = not self.AutoPlay
        self.SwitchMode.setText("自动" if self.AutoPlay else "单局")

    def init_cards(self):
        self.RunGame = True
        GameHelper.Interrupt = False
        self.init_display()
        self.initial_model_rate = 0

        self.user_hand_cards_real = ""
        self.user_hand_cards_env = []
        self.other_played_cards_real = ""
        self.other_played_cards_env = []
        self.upper_played_cards_real = ""
        self.lower_played_cards_real = ""

        self.other_hand_cards = []

        self.three_landlord_cards_real = ""
        self.three_landlord_cards_env = []
        # 玩家角色代码：0-地主上家, 1-地主, 2-地主下家
        self.user_position_code = None
        self.user_position = ""

        self.card_play_data_list = {}

        self.play_order = 0

        self.env = None

        self.user_hand_cards_real = self.find_my_cards(self.MyHandCardsPos)
        self.UserHandCards.setText(self.user_hand_cards_real)
        self.user_hand_cards_env = [RealCard2EnvCard[c] for c in list(self.user_hand_cards_real)]

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

        self.user_position_code = self.find_landlord(self.LandlordFlagPos)
        try_count = 5
        while self.user_position_code is None and self.RunGame and try_count > 0:
            print("玩家角色获取失败！重试中…")
            try_count -= 1
            helper.LeftClick((900, 550))
            self.sleep(500)
            self.user_position_code = self.find_landlord(self.LandlordFlagPos)
        if self.user_position_code is None:
            return
        self.user_position = ['landlord_up', 'landlord', 'landlord_down'][self.user_position_code]
        for player in self.Players:
            player.setStyleSheet('background-color: rgba(255, 0, 0, 0);')
        self.Players[self.user_position_code].setStyleSheet('background-color: rgba(255, 0, 0, 0.1);')

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

        self.play_order = 0 if self.user_position == "landlord" else 1 if self.user_position == "landlord_up" else 2
        self.LastValidPlayPos = self.play_order

        ai_players = [self.user_position,
                      DeepAgent(self.user_position, self.card_play_model_path_dict[self.user_position])]
        # ai_players2 = [self.user_position,
        #                DeepAgent(self.user_position, self.card_play_wp_model_path[self.user_position])]
        self.env = GameEnv(ai_players, None)

        try:
            self.start()
        except Exception as e:
            print("运行时出现错误，已重置\n", repr(e))
            traceback.print_exc()
            self.stop()

    def sleep(self, ms):
        self.counter.restart()
        while self.counter.elapsed() < ms:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)

    def waitUntilNoAnimation(self, ms=150):
        ani = self.haveAnimation(ms)
        iter_cnt = 0
        # wait at most (3 * 2 * 150)ms, about 1 sec
        while ani and iter_cnt < 3:
            if iter_cnt == 0:
                print("等待动画", end="")
            elif iter_cnt % 2 == 0:
                print(".", end="")
            iter_cnt += 1
            ani = self.haveAnimation(ms)
        if iter_cnt > 0:
            print("\t动画结束", end="")
        print()
        self.sleep(600)

    def real_to_env(self, cards):
        env_card = [RealCard2EnvCard[c] for c in cards]
        env_card.sort()
        return env_card

    @staticmethod
    def move_type_tostr(move_type):
        mtype = move_type["type"]
        mtype_map = ["", "单张", "对子", "三张", "炸弹", "王炸", "三带一", "三带一对", "顺子", "连对", "飞机", "飞机带单根", "飞机带一对", "四带二", "四带两对",
                     "不是合法牌型"]
        t_str = mtype_map[mtype]
        if "len" in move_type:
            t_str += " 长度: " + str(move_type["len"])
        return t_str

    # Optimize by 错过
    def handle_others(self, playPos, label, nick):
        label.setText("等待出牌中")
        QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)  # 更新界面
        # passPos 识别"不出"区域和识别牌的区域不一样（识别牌的区域很小），所以用 passPos
        passPos = self.LPassPos if nick == "上家" else self.RPassPos
        pass_flag = helper.LocateOnScreen('pass', region=passPos, confidence=self.PassConfidence)
        lastCards = ""
        sameCount = 0
        sameCountSingle = 0  # 如果长度为 1，可能是顺子的起始，所以算两次
        need_newline = 2
        print("等待", nick, "出牌", end="")
        while self.RunGame and pass_flag is None:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)
            img, _ = helper.Screenshot()  # 只用一次截图，find_other_cards 和 LocateOnScreen 添加了 img 参数
            need_newline += 1
            if need_newline % 2 == 0:
                print(".", end="")
                need_newline = 0
            st = time.time()
            cards = self.find_other_cards(pos=playPos, img=img)  # img
            move_type = get_move_type(self.real_to_env(cards))

            last_played_cards = self.upper_played_cards_real if nick == "上家" else self.lower_played_cards_real
            last_play_count = 0
            if cards == last_played_cards and last_play_count <= 2:
                last_play_count += 1
                self.sleep(300)

            if len(cards) == 0:  # 如果没有卡，不要等 300 毫秒，直接搜索 pass
                pass_flag = helper.LocateOnScreen('pass', region=passPos, confidence=self.PassConfidence,
                                                  img=img)  # 需要在 helper 中增加img这个参数，默认为 None
            elif cards == lastCards and len(cards) > 0:
                sameCount += 1
                requireCounts = 2 if len(cards) == 1 else 1
                if sameCount >= requireCounts and move_type["type"] != 15:
                    break
                else:
                    if need_newline > 2:
                        need_newline = 0
                        print()
                    # print("检测到", sameCount, "次", self.move_type_tostr(move_type))
                    need_newline += 1
                    label.setText(cards)
                    self.sleep(100)
            else:
                lastCards = cards
                sameCount = 0
                print(cards, end=" ")
                et = time.time()
                if et - st < 0.3:
                    self.sleep(300 - (et - st) * 1000)
            # 不管牌的长度，都要执行，除非 break 了
            # 20% 的概率寻找 change_player
            self.detect_start_btn()

        if pass_flag is None:
            self.other_played_cards_real = lastCards
            print("\n" + nick, "出牌", self.other_played_cards_real)
            label.setText(self.other_played_cards_real)
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)  # 更新界面
        else:
            self.other_played_cards_real = ""
            label.setText("不出")
            self.sleep(200)
            print("\n" + nick, "不要")
        if not self.RunGame:
            self.other_played_cards_real = ""
        self.other_played_cards_env = [RealCard2EnvCard[c] for c in list(self.other_played_cards_real)]
        self.other_played_cards_env.sort()
        self.env.step(self.user_position, self.other_played_cards_env)
        # self.animation_sleep(cards)
        cards = self.other_played_cards_real
        # 更新上下家手牌
        if nick == "上家":
            self.upper_played_cards_real = cards
        else:
            self.lower_played_cards_real = cards

        move_type = get_move_type(self.real_to_env(cards))
        animation_types = {4, 5, 13, 14, 8, 9, 10, 11, 12}
        if move_type["type"] in animation_types or len(cards) >= 6:
            self.waitUntilNoAnimation()

    def animation_sleep(self, cards, normalTime=0):
        if (len(cards) == 4 and len(set(cards)) == 1) or \
                len(cards) >= 6:  # 飞机也要休息一下
            print("飞机休息 2秒")
            self.sleep(2200)
        elif "D" in cards and "X" in cards:
            print("王炸休息 3 秒")
            self.sleep(3000)
        elif len(cards) == 5 and len(set(cards)) == 5:
            print("顺子休息 2 秒")
            self.sleep(2200)
        else:
            print("休息{}秒".format(normalTime / 1000))
            self.sleep(normalTime)

    @staticmethod
    def action_to_str(action):
        if len(action) == 0:
            return "Pass"
        else:
            return "".join([EnvCard2RealCard[card] for card in action])

    def card_play_data_tostr(self, card_play_data):
        s = "---------- 对局信息 ----------\n"
        s += "      地主牌: " + self.action_to_str(card_play_data["three_landlord_cards"]) + "\n" + \
             "    地主手牌: " + self.action_to_str(card_play_data["landlord"]) + "\n" + \
             "地主上家手牌:" + self.action_to_str(card_play_data["landlord_up"]) + "\n" + \
             "地主下家手牌:" + self.action_to_str(card_play_data["landlord_down"])
        s += "\n------------------------------"
        return s

    def record_cards(self):
        try:
            for card in self.other_played_cards_env:
                self.other_hand_cards.remove(card)
        except ValueError as e:
            traceback.print_exc()

    def game_loop(self):
        while True:
            try_count = 0
            while self.detect_start_btn(True) is None and try_count < 5:
                try_count += 1
                self.sleep(300)
            self.before_start()
            self.init_cards()
            if not self.AutoPlay:
                break

    def start(self):
        self.GameRecord.clear()
        self.env.card_play_init(self.card_play_data_list)
        cards_left = []
        print("开始对局")
        print("手牌:", self.user_hand_cards_real)
        first_run = True
        st = time.time()
        step_count = 0
        while not self.env.game_over and self.RunGame:
            if self.play_order == 0:
                self.PredictedCard.setText("...")
                action_message, action_list = self.env.step(self.user_position)
                self.UserHandCards.setText("手牌：" + str(''.join(
                    [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards]))[::-1])
                action_list = action_list[:8]
                action_list_str = "\n".join([ainfo[0] + " " + ainfo[1] for ainfo in action_list])
                self.PredictedCard.setText(action_message["action"] if action_message["action"] else "不出")
                self.WinRate.setText(action_list_str)
                action_list_str = " | ".join([ainfo[0] + " " + ainfo[1] for ainfo in action_list])
                # self.sleep(400)
                hand_cards_str = ''.join(
                    [EnvCard2RealCard[c] for c in self.env.info_sets[self.user_position].player_hand_cards])
                if first_run:
                    self.initial_model_rate = round(float(action_message["win_rate"]), 3)  # win_rate at start
                    first_run = False
                print("出牌:", action_message["action"] if action_message["action"] else "Pass", "| 得分:",
                      round(action_message["win_rate"], 3), "| 剩余手牌:", hand_cards_str)
                print(action_list_str)
                if not (self.upper_played_cards_real == "DX" or self.lower_played_cards_real == "DX" or
                        (len(hand_cards_str + action_message["action"]) == 1 and len(
                            self.upper_played_cards_real) > 1) or
                        (len(hand_cards_str + action_message["action"]) == 1 and len(
                            self.lower_played_cards_real) > 1)):
                    if action_message["action"] == "":
                        tryCount = 2
                        result = helper.LocateOnScreen("pass_btn", region=self.PassBtnPos, confidence=0.85)
                        passSign = helper.LocateOnScreen("pass", region=(830, 655, 150, 70), confidence=0.85)
                        while result is None is None and tryCount > 0:
                            if not self.RunGame:
                                break
                            if passSign is not None and tryCount <= 0:
                                break
                            print("等待不出按钮")
                            self.detect_start_btn()
                            tryCount -= 1
                            result = helper.LocateOnScreen("pass_btn", region=self.PassBtnPos, confidence=0.85)
                            passSign = helper.LocateOnScreen("pass", region=(830, 655, 150, 70), confidence=0.85)
                            self.sleep(100)
                        helper.ClickOnImage("pass_btn", region=self.PassBtnPos, confidence=0.85)
                    else:
                        if len(hand_cards_str) == 0 and len(action_message["action"]) == 1:
                            helper.SelectCards(action_message["action"], True)
                        else:
                            helper.SelectCards(action_message["action"])
                        tryCount = 10
                        result = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.85)
                        while result is None and tryCount > 0:
                            print("等待出牌按钮")
                            tryCount -= 1
                            result = helper.LocateOnScreen("play_card", region=self.PassBtnPos, confidence=0.85)
                            self.sleep(100)
                        self.sleep(100)
                        helper.ClickOnImage("play_card", region=self.PassBtnPos, confidence=0.85)
                    self.sleep(300)
                else:
                    print("要不起，跳过出牌")
                self.GameRecord.append(action_message["action"] if action_message["action"] != "" else "Pass")
                self.sleep(500)
                if action_message["action"]:
                    cards = action_message["action"]
                    move_type = get_move_type(self.real_to_env(cards))
                    animation_types = {4, 5, 13, 14, 8, 9, 10, 11, 12}
                    if move_type["type"] in animation_types or len(cards) >= 6:
                        self.waitUntilNoAnimation()

                self.detect_start_btn()

                self.play_order = 1

            elif self.play_order == 1:
                if self.other_played_cards_real != "DX" or len(self.other_played_cards_real) == 4 and len(
                        set(self.other_played_cards_real)) == 1:
                    self.handle_others(self.RPlayedCardsPos, self.RPlayedCard, "下家")
                else:
                    self.other_played_cards_real = ""
                    self.other_played_cards_env = ""
                    self.env.step(self.user_position, [])
                self.GameRecord.append(self.other_played_cards_real if self.other_played_cards_real != "" else "Pass")
                self.record_cards()
                self.play_order = 2
                self.sleep(200)

            elif self.play_order == 2:
                if self.other_played_cards_real != "DX" or len(self.other_played_cards_real) == 4 and len(
                        set(self.other_played_cards_real)) == 1:
                    self.handle_others(self.LPlayedCardsPos, self.LPlayedCard, "上家")
                else:
                    self.other_played_cards_real = ""
                    self.other_played_cards_env = ""
                    self.env.step(self.user_position, [])
                self.GameRecord.append(self.other_played_cards_real if self.other_played_cards_real != "" else "Pass")
                self.record_cards()
                self.play_order = 0
                self.sleep(100)
            step_count = (step_count + 1) % 3
            self.sleep(20)

        self.sleep(500)
        self.RunGame = False

    def find_landlord(self, landlord_flag_pos):
        for pos in landlord_flag_pos:
            result = helper.LocateOnScreen("landlord_words", region=pos, confidence=self.LandlordFlagConfidence)
            if result is not None:
                return landlord_flag_pos.index(pos)
        return None

    # 先看有没有换对手这个按钮，如果有的话，启动 detect_start_btn, 耗时 0.16秒
    def detect_change_player(self, image=None):
        if image:
            result = helper.LocateOnScreen("change_player_btn", region=(400, 400, 934, 800), img=image)
        else:
            result = helper.LocateOnScreen("change_player_btn", region=(400, 400, 934, 800))
        if result is not None:
            self.detect_start_btn()

    def detect_popup(self):
        img, _ = helper.Screenshot()
        result = helper.LocateOnScreen("yes_btn", region=(680, 661, 435, 225), img=img)
        if result is not None:
            helper.ClickOnImage("yes_btn", region=(680, 661, 435, 225), img=img)
            self.sleep(1000)
        result = helper.LocateOnScreen("get_award_btn", region=(680, 661, 435, 225), img=img)
        if result is not None:
            helper.ClickOnImage("get_award_btn", region=(680, 661, 435, 225), img=img)
            self.sleep(1000)
        result = helper.LocateOnScreen("yes_btn_sm", region=(669, 583, 468, 100), img=img)
        if result is not None:
            helper.ClickOnImage("yes_btn_sm", region=(669, 583, 468, 100), img=img)
            self.sleep(1000)

    # 耗时 0.7 秒
    def detect_start_btn(self, click=False):
        img, _ = helper.Screenshot()
        result = helper.LocateOnScreen("change_player_btn", region=(400, 400, 934, 800), img=img, confidence=0.8)
        if self.AutoPlay and result is not None:
            print("检测到换对手按钮")
            self.stop()
            self.RunGame = False
            if self.AutoPlay:
                if click:
                    print("点击换对手")
                    helper.ClickOnImage("change_player_btn", region=(400, 400, 934, 800), img=img, confidence=0.8)
                    self.sleep(1000)
                    return True
            else:
                return
        result = helper.LocateOnScreen("finish_round", region=(810, 840, 200, 80), confidence=0.8, img=img)
        if result is not None:
            helper.ClickOnImage("finish_round", region=(810, 840, 200, 80), confidence=0.8, img=img)
            self.sleep(1000)
        result = helper.LocateOnScreen("next_round", region=(958, 869, 300, 100), confidence=0.8, img=img)
        if result is not None:
            helper.ClickOnImage("next_round", region=(958, 869, 300, 100), confidence=0.8, img=img)
            self.sleep(1000)
        result = helper.LocateOnScreen("yes_btn", region=(680, 661, 435, 225), img=img)
        if result is not None:
            helper.ClickOnImage("yes_btn", region=(680, 661, 435, 225), img=img)
            self.sleep(1000)
        result = helper.LocateOnScreen("get_award_btn", region=(680, 661, 435, 225), img=img)
        if result is not None:
            helper.ClickOnImage("get_award_btn", region=(680, 661, 435, 225), img=img)
            self.sleep(1000)
        result = helper.LocateOnScreen("yes_btn_sm", region=(669, 583, 468, 100), img=img)
        if result is not None:
            helper.ClickOnImage("yes_btn_sm", region=(669, 583, 468, 100), img=img)
            self.sleep(200)

    def find_three_landlord_cards(self, pos):
        img, _ = helper.Screenshot(region=pos)
        # img = img.crop((pos[0], pos[1], pos[0] + pos[2], pos[1] + pos[3]))
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
                                             confidence=self.ThreeLandlordCardsConfidence - 0.1)
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
        return user_hand_cards_real

    def find_other_cards(self, pos, img=None):
        other_played_cards_real = ""
        if not img:
            img, _ = helper.Screenshot()
        imgCv = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
        for card in AllCards:
            result = gh.LocateAllOnImage(imgCv, helper.PicsCV['o' + card], region=pos, confidence=self.OtherConfidence)
            if len(result) > 0:
                other_played_cards_real += card[1] * self.cards_filter(list(result), self.OtherFilter)
        return other_played_cards_real

    @staticmethod
    def filter_image_white(img: Image, threshold=170):
        width, height = img.size
        pixels = img.load()
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                if abs(r - g) < 20 and abs(r - b) < 20 and r > threshold:
                    pixels[x, y] = (255 - r, 255 - g, 255 - b)
                else:
                    pixels[x, y] = (255, 255, 255)

    @staticmethod
    def filter_image_orange(img: Image, threshold=200):
        width, height = img.size
        pixels = img.load()
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                if r - b > 30 and r > threshold:
                    pixels[x, y] = (255 - r, 255 - r, 255 - r)
                else:
                    pixels[x, y] = (255, 255, 255)

    @staticmethod
    def filter_image_dark(img: Image, threshold=550):
        width, height = img.size
        pixels = img.load()
        for y in range(height):
            for x in range(width):
                r, g, b = pixels[x, y]
                if r + g + b > threshold:
                    pixels[x, y] = (255, 255, 255)
                else:
                    pixels[x, y] = (0, 0, 0)

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
            if self.env is not None:
                self.env.game_over = True
                self.env.reset()
            self.init_display()
            self.PreWinrate.setText("局前预估得分: ")
            self.BidWinrate.setText("叫牌预估得分: ")
        except AttributeError as e:
            traceback.print_exc()

    def compareImage(self, im1, im2):
        if im1.size != im2.size:
            return False
        size = im1.size
        for y in range(size[1]):
            for x in range(size[0]):
                if im1.getpixel((x, y)) != im2.getpixel((x, y)):
                    return False
        return True

    def haveAnimation(self, waitTime=200):
        regions = [
            (1122, 585, 1122 + 30, 585 + 30),  # 开始游戏右上
            (763, 625, 763 + 30, 625 + 30),  # 自家出牌上方
            (478, 433, 852, 630),  # 经典玩法新手场 对家使用
            (880, 540, 880 + 20, 540 + 20)  # 炸弹时使用，正中央
        ]
        img, _ = helper.Screenshot()
        lastImg = img
        for i in range(2):
            self.sleep(waitTime)
            img, _ = helper.Screenshot()
            for region in regions:
                if not self.compareImage(img.crop(region), lastImg.crop(region)):
                    return True
            lastImg = img

        return False

    def before_start(self):
        self.RunGame = True
        GameHelper.Interrupt = True
        have_bid = False
        is_taodou = False
        is_stolen = 0
        self.initial_multiply = 0
        self.initial_mingpai = 0
        self.initial_bid_rate = 0
        while self.RunGame:
            outterBreak = False
            jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=(765, 663, 116, 50))
            qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=(783, 663, 116, 50))
            jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
            self.detect_start_btn()
            print("等待加倍或叫地主", end="")
            while jiaodizhu_btn is None and qiangdizhu_btn is None and jiabei_btn is None and self.RunGame:
                self.detect_start_btn()
                print(".", end="")
                self.sleep(100)
                jiaodizhu_btn = helper.LocateOnScreen("jiaodizhu_btn", region=(765, 663, 116, 50))
                qiangdizhu_btn = helper.LocateOnScreen("qiangdizhu_btn", region=(783, 663, 116, 50))
                jiabei_btn = helper.LocateOnScreen("jiabei_btn", region=self.GeneralBtnPos)
            if jiabei_btn is None:
                img, _ = helper.Screenshot()
                cards, _ = helper.GetCards(img)
                cards_str = "".join([card[0] for card in cards])
                win_rate = BidModel.predict_score(cards_str)
                farmer_score = FarmerModel.predict(cards_str, "farmer")
                if not have_bid:
                    with open("cardslog.txt", "a") as f:
                        f.write(str(int(time.time())) + " " + cards_str + " " + str(round(win_rate, 2)) + "\n")
                print("\n叫牌预估得分: " + str(round(win_rate, 3)) + " 不叫预估得分: " + str(round(farmer_score, 3)))
                self.BidWinrate.setText(
                    "叫牌预估得分: " + str(round(win_rate, 3)) + " 不叫预估得分: " + str(round(farmer_score, 3)))
                self.sleep(10)
                self.initial_bid_rate = round(win_rate, 3)
                is_stolen = 0
                compare_winrate = win_rate
                if compare_winrate > 0:
                    compare_winrate *= 2.5
                landlord_requirement = True
                if self.use_manual_landlord_requirements:
                    landlord_requirement = manual_landlord_requirements(cards_str)

                if jiaodizhu_btn is not None:
                    have_bid = True
                    if win_rate > self.BidThresholds[0] and compare_winrate > farmer_score and landlord_requirement:
                        helper.ClickOnImage("jiaodizhu_btn", region=(765, 663, 116, 50), confidence=0.9)
                    else:
                        helper.ClickOnImage("bujiao_btn", region=self.GeneralBtnPos)
                elif qiangdizhu_btn is not None:
                    is_stolen = 1
                    if have_bid:
                        threshold_index = 1
                    else:
                        threshold_index = 2
                    if win_rate > self.BidThresholds[
                        threshold_index] and compare_winrate > farmer_score and landlord_requirement:
                        helper.ClickOnImage("qiangdizhu_btn", region=(783, 663, 116, 50), confidence=0.9)
                    else:
                        helper.ClickOnImage("buqiang_btn", region=self.GeneralBtnPos)
                    have_bid = True
                else:
                    pass
                if have_bid:
                    result = helper.LocateOnScreen("taodouchang", region=(835, 439, 140, 40), confidence=0.9)
                    if result is not None:
                        is_taodou = True
                        print("淘豆场，跳过加倍")
                        break
            else:
                llcards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
                print("地主牌:", llcards)
                img, _ = helper.Screenshot()
                cards, _ = helper.GetCards(img)
                cards_str = "".join([card[0] for card in cards])
                self.initial_cards = cards_str
                if len(cards_str) == 20:
                    # win_rate = LandlordModel.predict(cards_str)
                    win_rate = LandlordModel.predict_by_model(cards_str, llcards)
                    self.PreWinrate.setText("局前预估得分: " + str(round(win_rate, 3)))
                    print("预估地主得分:", round(win_rate, 3))
                else:
                    user_position_code = self.find_landlord(self.LandlordFlagPos)
                    user_position = "up"
                    while user_position_code is None:
                        user_position_code = self.find_landlord(self.LandlordFlagPos)
                        self.sleep(50)
                    user_position = ['up', 'landlord', 'down'][user_position_code]
                    self.landlord_position_code = user_position_code
                    win_rate = FarmerModel.predict(cards_str, user_position)
                    print("预估农民得分:", round(win_rate, 3))
                    self.PreWinrate.setText("局前预估得分: " + str(round(win_rate, 3)))
                if len(cards_str) == 20:
                    JiabeiThreshold = self.JiabeiThreshold[is_stolen]
                else:
                    JiabeiThreshold = self.FarmerJiabeiThreshold

                print("等待其他人加倍……")
                self.sleep(3500)

                chaojijiabei_btn = helper.LocateOnScreen("chaojijiabei_btn", region=self.GeneralBtnPos, confidence=0.78)
                if chaojijiabei_btn is None and self.stop_when_no_chaojia:
                    self.AutoPlay = False
                    self.SwitchMode.setText("自动" if self.AutoPlay else "单局")
                    self.sleep(10)
                    print("检测到没有超级加倍卡，已停止自动模式")
                if win_rate > JiabeiThreshold[0]:
                    chaojijiabei_btn = helper.LocateOnScreen("chaojijiabei_btn", region=self.GeneralBtnPos, confidence=0.78)
                    if chaojijiabei_btn is not None:
                        helper.ClickOnImage("chaojijiabei_btn", region=self.GeneralBtnPos, confidence=0.78)
                        self.initial_multiply = 4
                    else:
                        helper.ClickOnImage("jiabei_btn", region=self.GeneralBtnPos)
                        self.initial_multiply = 2
                elif win_rate > JiabeiThreshold[1]:
                    helper.ClickOnImage("jiabei_btn", region=self.GeneralBtnPos)
                    self.initial_multiply = 2
                else:
                    helper.ClickOnImage("bujiabei_btn", region=self.GeneralBtnPos)
                    self.initial_multiply = 1
                outterBreak = True
                break
            if outterBreak:
                break

        llcards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)
        wait_count = 0
        while len(llcards) != 3 and self.RunGame and wait_count < 15:
            print("等待地主牌", llcards)
            self.sleep(200)
            wait_count += 1
            llcards = self.find_three_landlord_cards(self.ThreeLandlordCardsPos)

        print("等待加倍环节结束")
        if not is_taodou:
            if len(cards_str) == 20:
                self.sleep(5000)
        else:
            self.sleep(3000)
        if win_rate > self.MingpaiThreshold:
            helper.ClickOnImage("mingpai_btn", region=self.GeneralBtnPos)
            self.initial_mingpai = 1
        print("结束")


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

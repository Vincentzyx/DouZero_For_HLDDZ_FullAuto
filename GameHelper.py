# -*- coding: utf-8 -*-
# Created by: Vincentzyx
import win32gui
import win32ui
import win32api
from ctypes import windll
from PIL import Image
import cv2
import pyautogui
import matplotlib.pyplot as plt
import numpy as np
import os
import time
import threading
from win32con import WM_LBUTTONDOWN, MK_LBUTTON, WM_LBUTTONUP, WM_MOUSEMOVE
import multiprocessing as mp

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QTime, QEventLoop

Pics = {}
ReqQueue = mp.Queue()
ResultQueue = mp.Queue()
Processes = []

def GetSingleCardQueue(reqQ, resQ, Pics):
    while True:
        while not reqQ.empty():
            image, i, sx, sy, sw, sh, checkSelect = reqQ.get()
            result = GetSingleCard(image, i, sx, sy, sw, sh, checkSelect, Pics)
            del image
            if result is not None:
                resQ.put(result)
        time.sleep(0.01)

def ShowImg(image):
    plt.imshow(image)
    plt.show()

def DrawRectWithText(image, rect, text):
    img = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    x, y, w, h = rect
    img2 = cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
    img2 = cv2.putText(img2, text, (x, y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    return Image.fromarray(cv2.cvtColor(img2, cv2.COLOR_BGR2RGB))

def CompareCard(card):
    order = {"3": 0, "4": 1, "5": 2, "6": 3, "7": 4, "8": 5, "9": 6, "T": 7, "J": 8, "Q": 9, "K": 10, "A": 11, "2": 12,
             "X": 13, "D": 14}
    return order[card]

def CompareCardInfo(card):
    order = {"3": 0, "4": 1, "5": 2, "6": 3, "7": 4, "8": 5, "9": 6, "T": 7, "J": 8, "Q": 9, "K": 10, "A": 11, "2": 12,
             "X": 13, "D": 14}
    return order[card[0]]

def CompareCards(cards1, cards2):
    if len(cards1) != len(cards2):
        return False
    cards1.sort(key=CompareCard)
    cards2.sort(key=CompareCard)
    for i in range(0, len(cards1)):
        if cards1[i] != cards2[i]:
            return False
    return True

def GetListDifference(l1, l2):
    temp1 = []
    temp1.extend(l1)
    temp2 = []
    temp2.extend(l2)
    for i in l2:
        if i in temp1:
            temp1.remove(i)
    for i in l1:
        if i in temp2:
            temp2.remove(i)
    return temp1, temp2

def FindImage(fromImage, template, threshold=0.9):
    w, h, _ = template.shape
    fromImage = cv2.cvtColor(np.asarray(fromImage), cv2.COLOR_RGB2BGR)
    res = cv2.matchTemplate(fromImage, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(res >= threshold)
    points = []
    for pt in zip(*loc[::-1]):
        points.append(pt)
    return points

def GetSingleCard(image, i, sx, sy, sw, sh, checkSelect, Pics):
    cardSearchFrom = 0
    AllCardsNC = ['rD', 'bX', '2', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3']
    currCard = ""
    ci = cardSearchFrom
    while ci < len(AllCardsNC):
        if "r" in AllCardsNC[ci] or "b" in AllCardsNC[ci]:
            result = pyautogui.locate(needleImage=Pics["m" + AllCardsNC[ci]], haystackImage=image,
                                      region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.9)
            if result is not None:
                cardPos = (sx + 50 * i + sw // 2, sy - checkSelect * 25 + sh // 2)
                cardSearchFrom = ci
                currCard = AllCardsNC[ci][1]
                cardInfo = (currCard, cardPos)
                return cardInfo
                break
        else:
            outerBreak = False
            for card_type in ["r", "b"]:
                result = pyautogui.locate(needleImage=Pics["m" + card_type + AllCardsNC[ci]],
                                          haystackImage=image,
                                          region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.9)
                if result is not None:
                    cardPos = (sx + 50 * i + sw // 2, sy - checkSelect * 25 + sh // 2)
                    cardSearchFrom = ci
                    currCard = AllCardsNC[ci]
                    cardInfo = (currCard, cardPos)
                    outerBreak = True
                    return cardInfo
                    break
            if outerBreak:
                break
            if ci == len(AllCardsNC) - 1 and checkSelect == 0:
                checkSelect = 1
                ci = cardSearchFrom - 1
        ci += 1
    return None

def RunThreads():
    for file in os.listdir("pics"):
        info = file.split(".")
        if info[1] == "png":
            tmpImage = Image.open("pics/" + file)
            Pics.update({info[0]: tmpImage})
    for ti in range(20):
        p = mp.Process(target=GetSingleCardQueue, args=(ReqQueue, ResultQueue, Pics))
        p.start()


def LocateOnImage(image, template, region=None, confidence=0.9):
    if region is not None:
        x, y, w, h = region
        imgShape = image.shape
        image = image[y:y+h, x:x+w,:]
    res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    if (res >= confidence).any():
        return True
    else:
        return None


class GameHelper:
    def __init__(self):
        self.ScreenZoomRate = 1.25
        self.Pics = {}
        self.PicsCV = {}
        self.Handle = win32gui.FindWindow("Hlddz", None)
        self.Interrupt = False
        for file in os.listdir("pics"):
            info = file.split(".")
            if info[1] == "png":
                tmpImage = Image.open("pics/" + file)
                imgCv = cv2.imread("pics/" + file)
                self.Pics.update({info[0]: tmpImage})
                self.PicsCV.update({info[0]: imgCv})

    def Screenshot(self, region=None):  # -> (im, (left, top))
        hwnd = self.Handle
        # im = Image.open(r"C:\Users\q9294\Desktop\llc.png")
        # im = im.resize((1796, 1047))
        # return im, (0,0)
        left, top, right, bot = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bot - top
        width = int(width / self.ScreenZoomRate)
        height = int(height / self.ScreenZoomRate)
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)
        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 0)
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        im = Image.frombuffer(
            "RGB",
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1)
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)
        im = im.resize((1796, 1047))
        if region is not None:
            im = im.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
        if result:
            return im, (left, top)
        else:
            return None, (0, 0)

    def LocateOnScreen(self, templateName, region, confidence=0.9):
        image, _ = self.Screenshot()
        return pyautogui.locate(needleImage=self.Pics[templateName],
                                haystackImage=image, region=region, confidence=confidence)

    def ClickOnImage(self, templateName, region=None, confidence=0.9):
        image, _ = self.Screenshot()
        result = pyautogui.locate(needleImage=self.Pics[templateName], haystackImage=image, confidence=confidence, region=region)
        if result is not None:
            self.LeftClick((result[0],result[1]))

    def GetCardsState(self, image):
        st = time.time()
        states = []
        cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                        region=(313, 747, 1144, 200), confidence=0.85)
        if cardStartPos is None:
            return []
        sx = cardStartPos[0] + 10
        cardSearchFrom = 0
        sy, sw, sh = 770, 50, 55
        for i in range(0, 20):
            haveWhite = pyautogui.locate(needleImage=self.Pics["card_white"], haystackImage=image,
                                         region=(sx + 50 * i, sy, 50, 50), confidence=0.8)
            if haveWhite is not None:
                break
            result = pyautogui.locate(needleImage=self.Pics["card_upper_edge"], haystackImage=image,
                                      region=(sx + 50 * i, 720, sw, 38), confidence=0.9)
            checkSelect = 0
            if result is not None:
                result = pyautogui.locate(needleImage=self.Pics['card_overlap'], haystackImage=image,
                                          region=(sx + 50 * i, 750, sw, 38), confidence=0.85)
                if result is None:
                    checkSelect = 1
            states.append(checkSelect)
        print("GetStates Costs ", time.time()-st)
        return states

    def GetCardsMulti(self, image):
        st = time.time()
        cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                        region=(313, 747, 1144, 200), confidence=0.85)
        if cardStartPos is None:
            return [],[]
        sx = cardStartPos[0] + 10
        AllCardsNC = ['rD', 'bX', '2', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3']
        hand_cards = []
        select_map = []
        cardSearchFrom = 0
        sy, sw, sh = 770, 50, 55
        for i in range(0, 20):
            haveWhite = pyautogui.locate(needleImage=self.Pics["card_white"], haystackImage=image,
                                         region=(sx + 50 * i, sy, 60, 60), confidence=0.8)
            if haveWhite is not None:
                break
            result = pyautogui.locate(needleImage=self.Pics["card_upper_edge"], haystackImage=image,
                                      region=(sx + 50 * i, 720, sw, 50), confidence=0.9)
            checkSelect = 0
            if result is not None:
                result = pyautogui.locate(needleImage=self.Pics['card_overlap'], haystackImage=image,
                                          region=(sx + 50 * i, 750, sw, 50), confidence=0.85)
                if result is None:
                    checkSelect = 1
            select_map.append(checkSelect)
            ReqQueue.put((image, i, sx, sy, sw, sh, checkSelect))
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)
        st = time.time()
        while len(hand_cards) != len(select_map):
            while not ResultQueue.empty():
                hand_cards.append(ResultQueue.get())
            time.sleep(0.01)
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)
        hand_cards.sort(key=CompareCardInfo, reverse=True)
        print("GetCardsMP Costs ", time.time()-st)
        return hand_cards, select_map

    def GetCards(self, image):
        st = time.time()
        imgCv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                        region=(313, 747, 1144, 200), confidence=0.85)
        if cardStartPos is None:
            return [],[]
        sx = cardStartPos[0] + 10
        AllCardsNC = ['rD', 'bX', '2', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3']
        hand_cards = []
        select_map = []
        cardSearchFrom = 0
        sy, sw, sh = 770, 50, 55
        for i in range(0, 20):
            haveWhite = pyautogui.locate(needleImage=self.Pics["card_white"], haystackImage=image,
                                         region=(sx + 50 * i, sy, 60, 60), confidence=0.8)
            if haveWhite is not None:
                break
            result = pyautogui.locate(needleImage=self.Pics["card_upper_edge"], haystackImage=image,
                                      region=(sx + 50 * i, 720, sw, 50), confidence=0.9)
            checkSelect = 0
            if result is not None:
                result = pyautogui.locate(needleImage=self.Pics['card_overlap'], haystackImage=image,
                                          region=(sx + 50 * i, 750, sw, 50), confidence=0.85)
                if result is None:
                    checkSelect = 1
            select_map.append(checkSelect)
            currCard = ""
            ci = cardSearchFrom
            while ci < len(AllCardsNC):
                if "r" in AllCardsNC[ci] or "b" in AllCardsNC[ci]:
                    result = LocateOnImage(imgCv, self.PicsCV["m" + AllCardsNC[ci]], region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.91)
                    # result = pyautogui.locate(needleImage=self.Pics["m" + AllCardsNC[ci]], haystackImage=image,
                    #                           region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.9)
                    if result is not None:
                        cardPos = (sx + 50 * i + sw // 2, sy - checkSelect * 25 + sh // 2)
                        cardSearchFrom = ci
                        currCard = AllCardsNC[ci][1]
                        cardInfo = (currCard, cardPos)
                        hand_cards.append(cardInfo)
                else:
                    outerBreak = False
                    for card_type in ["r", "b"]:
                        result = LocateOnImage(imgCv, self.PicsCV["m" + card_type + AllCardsNC[ci]], region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.91)
                        # result = pyautogui.locate(needleImage=self.Pics["m" + card_type + AllCardsNC[ci]],
                        #                           haystackImage=image,
                        #                           region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.9)
                        if result is not None:
                            cardPos = (sx + 50 * i + sw // 2, sy - checkSelect * 25 + sh // 2)
                            cardSearchFrom = ci
                            currCard = AllCardsNC[ci]
                            cardInfo = (currCard, cardPos)
                            hand_cards.append(cardInfo)
                            outerBreak = True
                            break
                    if outerBreak:
                        break
                    if ci == len(AllCardsNC) - 1 and checkSelect == 0:
                        checkSelect = 1
                        ci = cardSearchFrom - 1
                ci += 1
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)
        print("GetCards Costs ", time.time()-st)
        return hand_cards, select_map

    def LeftClick(self, pos):
        x, y = pos
        lParam = win32api.MAKELONG(x, y)
        win32gui.PostMessage(self.Handle, WM_MOUSEMOVE, MK_LBUTTON, lParam)
        win32gui.PostMessage(self.Handle, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
        win32gui.PostMessage(self.Handle, WM_LBUTTONUP, MK_LBUTTON, lParam)

    def SelectCards(self, cards):
        cards = [card for card in cards]
        tobeSelected = []
        tobeSelected.extend(cards)
        image, windowPos = self.Screenshot()
        handCardsInfo, states = self.GetCards(image)
        cardSelectMap = []
        for card in handCardsInfo:
            c = card[0]
            if c in tobeSelected:
                cardSelectMap.append(1)
                tobeSelected.remove(c)
            else:
                cardSelectMap.append(0)
        clickMap = []
        handcards = [c[0] for c in handCardsInfo]
        for i in range(0, len(cardSelectMap)):
            if cardSelectMap[i] == states[i]:
                clickMap.append(0)
            else:
                clickMap.append(1)
        while 1 in clickMap:
            for i in range(0, len(clickMap)):
                if clickMap[i] == 1:
                    self.LeftClick(handCardsInfo[i][1])
                    break
            time.sleep(0.1)
            if self.Interrupt:
                break
            image, _ = self.Screenshot()
            states = self.GetCardsState(image)
            clickMap = []
            for i in range(0, len(cardSelectMap)):
                if cardSelectMap[i] == states[i]:
                    clickMap.append(0)
                else:
                    clickMap.append(1)
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)


# for file in os.listdir("pics"):
#     info = file.split(".")
#     if info[1] == "png":
#         tmpImage = Image.open("pics/" + file)
#         imgBGR = cv2.imread("pics/" + file)
#         Pics.update({info[0]: tmpImage})

if __name__ == "__main__":
    mp.freeze_support()
    class A:
        def __init__(self):
            pass


    Pics = {}
    PicsCV = {}
    Handle = win32gui.FindWindow("Hlddz", None)
    form = A()
    form.MyHandCardsPos = (250, 764, 1141, 70)  # 我的截图区域
    form.LPlayedCardsPos = (463, 355, 380, 250)  # 左边截图区域
    form.RPlayedCardsPos = (946, 355, 380, 250)  # 右边截图区域
    form.LandlordFlagPos = [(1281, 276, 110, 140), (267, 695, 110, 140), (424, 237, 110, 140)]  # 地主标志截图区域(右-我-左)
    form.ThreeLandlordCardsPos = (753, 32, 287, 136)  # 地主底牌截图区域，resize成349x168
    form.PassBtnPoss = (686, 659, 419, 100)
    GameHelper = GameHelper()
    # img, _ = GameHelper.Screenshot()
    img = Image.open(r"C:\Users\q9294\Desktop\cardselect.png")
    img2 = Image.open(r"pics/card_corner.png")
    img = img.resize((1796, 1047))
    # imgcv = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    # st = time.time()
    # re = LocateOnImage(imgcv, GameHelper.PicsCV["card_edge"], region=None, confidence=0.999)
    # print(re)
    # print(time.time()-st)
    # st = time.time()
    # re = pyautogui.locate(needleImage=GameHelper.Pics["card_edge"], haystackImage=img, confidence=0.9)
    # print(re)
    # print(time.time()-st)
    # st = time.time()
    img, _ = GameHelper.Screenshot()
    cards, _= GameHelper.GetCards(img)
    # cards = "".join([i[0] for i in cards])
    print(cards)
    print(len(cards))
    # et = time.time()
    # print(et - st)
    # pos2 = pyautogui.locate(needleImage=Pics["card_edge"], haystackImage=img, confidence=0.9)
    # pos = FindImage(img, PicsCV["card_corner"], threshold=0.7)
    # print(pos)
    # print(pos2)
    # for p in pos:
    #     img = DrawRectWithText(img, (p[0], p[1], 50, 50), "p1")
    # img = DrawRectWithText(img, (pos2[0], pos2[1], 50, 50), "p2")
    # img = DrawRectWithText(img, (sx+50*i, sy-checkSelect*25,sw,sh), c)
    # img = DrawRectWithText(img, form.LPlayedCardsPos, "LPlayed")
    # img = DrawRectWithText(img, form.RPlayedCardsPos, "RPlayed")
    # img = DrawRectWithText(img, form.MyHandCardsPos, "MyCard")
    # img = DrawRectWithText(img, form.ThreeLandlordCardsPos, "ThreeLLCPos")
    # img = DrawRectWithText(img, form.LandlordFlagPos[0], "RFlag")
    # img = DrawRectWithText(img, form.LandlordFlagPos[1], "MyFlag")
    # img = DrawRectWithText(img, form.LandlordFlagPos[2], "LFlag")
    # img = DrawRectWithText(img, form.PassBtnPoss, "Btns")
    # ShowImg(img)
    exit()

# -*- coding: utf-8 -*-
# Created by: Vincentzyx
import ctypes

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
from win32con import WM_LBUTTONDOWN, MK_LBUTTON, WM_LBUTTONUP, WM_MOUSEMOVE

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QTime, QEventLoop

Pics = {}

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

def LocateAllOnImage(image, template, region=None, confidence=0.9):
    if region is not None:
        x, y, w, h = region
        imgShape = image.shape
        image = image[y:y+h, x:x+w,:]
    w, h = image.shape[1], image.shape[0]
    res = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where( res >= confidence)
    points = []
    for pt in zip(*loc[::-1]):
        points.append((pt[0], pt[1], w, h))
    return points

class GameHelper:
    def __init__(self):
        self.counter = QTime()
        self.ScreenZoomRate = 1.25
        self.Pics = {}
        self.PicsCV = {}
        st = time.time()
        self.Handle = win32gui.FindWindow("Hlddz", None)
        self.Interrupt = False
        self.RealRate = (1796, 1047)
        self.GetZoomRate()
        for file in os.listdir("./pics"):
            info = file.split(".")
            if info[1] == "png":
                tmpImage = Image.open("./pics/" + file)
                imgCv = cv2.imread("./pics/" + file)
                self.Pics.update({info[0]: tmpImage})
                self.PicsCV.update({info[0]: imgCv})

    def sleep(self, ms):
        self.counter.restart()
        while self.counter.elapsed() < ms:
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 50)

    def Screenshot(self, region=None):  # -> (im, (left, top))
        try_count = 3
        success = False
        while try_count > 0 and not success:
            try:
                try_count -= 1
                # im = Image.open(r"C:\Users\Vincentzyx\Desktop\Snipaste_2021-12-22_22-58-02.png")
                # im = im.resize((1796, 1047))
                # if region is not None:
                #     im = im.crop((region[0], region[1], region[0] + region[2], region[1] + region[3]))
                # ShowImg(im)
                # return im, (0,0)
                # self.GetZoomRate()
                self.Handle = win32gui.FindWindow("Hlddz", None)
                hwnd = self.Handle
                left, top, right, bot = win32gui.GetWindowRect(hwnd)
                width = right - left
                height = bot - top
                self.RealRate = (width, height)
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
                    success = True
                    return im, (left, top)
            except Exception as e:
                print("截图时出现错误:", repr(e))
                self.sleep(200)
        return None, (0,0)

    def GetZoomRate(self):
        self.ScreenZoomRate = ctypes.windll.shcore.GetScaleFactorForDevice(0) / 100

    def LocateOnScreen(self, templateName, region, confidence=0.9, img=None):
        if img is not None:
            image = img
        else:
            image, _ = self.Screenshot()
        imgcv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        return LocateOnImage(imgcv, self.PicsCV[templateName], region=region, confidence=confidence)
        # return pyautogui.locate(needleImage=self.Pics[templateName],
        #                         haystackImage=image, region=region, confidence=confidence)

    def ClickOnImage(self, templateName, region=None, confidence=0.9, img=None):
        if img is not None:
            image = img
        else:
            image, _ = self.Screenshot()
        result = pyautogui.locate(needleImage=self.Pics[templateName], haystackImage=image, confidence=confidence, region=region)
        if result is not None:
            self.LeftClick((result[0], result[1]))

    def GetCardsState(self, image):
        st = time.time()
        imgCv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        states = []
        tryCount = 10
        cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                        region=(313, 747, 1144, 200), confidence=0.80)
        while cardStartPos is None and tryCount > 0:
            self.LeftClick((900, 550))
            self.sleep(150)
            cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                            region=(313, 747, 1144, 200), confidence=0.80)
            print("找不到手牌起始位置")
            tryCount -= 1
        if cardStartPos is None:
            return []
        sx = cardStartPos[0] + 10
        cardSearchFrom = 0
        sy, sw, sh = 770, 50, 55
        for i in range(0, 20):
            haveWhite = LocateOnImage(imgCv, self.PicsCV["card_white"], region=(sx + 50 * i, sy, 60, 60), confidence=0.9)
            if haveWhite is not None:
                break
            result = LocateOnImage(imgCv, self.PicsCV["card_upper_edge"], region=(sx + 50 * i, 720, sw, 50), confidence=0.9)
            checkSelect = 0
            if result is not None:
                result = LocateOnImage(imgCv, self.PicsCV["card_overlap"], region=(sx + 50 * i, 750, sw, 50), confidence=0.85)
                if result is None:
                    checkSelect = 1
            states.append(checkSelect)
        return states

    def GetCards(self, image):
        st = time.time()
        imgCv = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
        tryCount = 10
        cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                        region=(313, 747, 1144, 200), confidence=0.80)
        while cardStartPos is None and tryCount > 0:
            self.LeftClick((900, 550))
            self.sleep(150)
            cardStartPos = pyautogui.locate(needleImage=self.Pics["card_edge"], haystackImage=image,
                                            region=(313, 747, 1144, 200), confidence=0.80)
            print("找不到手牌起始位置")
            tryCount -= 1
        if cardStartPos is None:
            return [],[]
        sx = cardStartPos[0] + 10
        AllCardsNC = ['rD', 'bX', '2', 'A', 'K', 'Q', 'J', 'T', '9', '8', '7', '6', '5', '4', '3']
        hand_cards = []
        select_map = []
        cardSearchFrom = 0
        sy, sw, sh = 770, 50, 55
        for i in range(0, 20):
            # haveWhite = pyautogui.locate(needleImage=self.Pics["card_white"], haystackImage=image,
            #                              region=(sx + 50 * i, sy, 60, 60), confidence=0.8)
            haveWhite = LocateOnImage(imgCv, self.PicsCV["card_white"], region=(sx + 50 * i, sy, 60, 60), confidence=0.88)
            if haveWhite is not None:
                break
            result = LocateOnImage(imgCv, self.PicsCV["card_upper_edge"], region=(sx + 50 * i, 720, sw, 50), confidence=0.88)
            # result = pyautogui.locate(needleImage=self.Pics["card_upper_edge"], haystackImage=image,
            #                           region=(sx + 50 * i, 720, sw, 50), confidence=0.9)
            checkSelect = 0
            if result is not None:
                # result = pyautogui.locate(needleImage=self.Pics['card_overlap'], haystackImage=image,
                #                           region=(sx + 50 * i, 750, sw, 50), confidence=0.85)
                result = LocateOnImage(imgCv, self.PicsCV["card_overlap"], region=(sx + 50 * i, 750, sw, 50), confidence=0.83)
                if result is None:
                    checkSelect = 1
            select_map.append(checkSelect)
            currCard = ""
            forBreak = False
            ci = cardSearchFrom
            while ci < len(AllCardsNC):
                if "r" in AllCardsNC[ci] or "b" in AllCardsNC[ci]:
                    outerBreak = False
                    result = LocateOnImage(imgCv, self.PicsCV["m" + AllCardsNC[ci]], region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.89)
                    # result = pyautogui.locate(needleImage=self.Pics["m" + AllCardsNC[ci]], haystackImage=image,
                    #                           region=(sx + 50 * i, sy - checkSelect * 25, sw, sh), confidence=0.9)
                    if result is not None:
                        cardPos = (sx + 50 * i + sw // 2, sy - checkSelect * 25 + sh // 2)
                        cardSearchFrom = ci
                        currCard = AllCardsNC[ci][1]
                        cardInfo = (currCard, cardPos)
                        hand_cards.append(cardInfo)
                        outerBreak = True
                        break
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
                if ci == len(AllCardsNC):
                    forBreak = True
            if forBreak:
                break
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)
        return hand_cards, select_map

    def LeftClick(self, pos):
        x, y = pos
        x = (x / 1796) * self.RealRate[0]
        y = (y / 1047) * self.RealRate[1]
        x = int(x)
        y = int(y)
        lParam = win32api.MAKELONG(x, y)
        win32gui.PostMessage(self.Handle, WM_MOUSEMOVE, MK_LBUTTON, lParam)
        win32gui.PostMessage(self.Handle, WM_LBUTTONDOWN, MK_LBUTTON, lParam)
        win32gui.PostMessage(self.Handle, WM_LBUTTONUP, MK_LBUTTON, lParam)

    def SelectCards(self, cards, no_check=False):
        cards = [card for card in cards]
        tobeSelected = []
        tobeSelected.extend(cards)
        image, windowPos = self.Screenshot()
        while image.size[0] == 0:
            image, windowPos = self.Screenshot()
        handCardsInfo, states = self.GetCards(image)
        cardSelectMap = []
        for card_i in range(len(handCardsInfo)-1, -1, -1):
            card = handCardsInfo[card_i]
            c = card[0]
            if c in tobeSelected:
                # cardSelectMap.append(1)
                cardSelectMap.insert(0, 1)
                tobeSelected.remove(c)
            else:
                # cardSelectMap.append(0)
                cardSelectMap.insert(0, 0)
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
            if no_check:
                return
            image, _ = self.Screenshot()
            while image.size[0] == 0:
                image, windowPos = self.Screenshot()
            states = self.GetCardsState(image)
            clickMap = []
            for i in range(0, len(cardSelectMap)):
                if cardSelectMap[i] == states[i]:
                    clickMap.append(0)
                else:
                    clickMap.append(1)
            QtWidgets.QApplication.processEvents(QEventLoop.AllEvents, 10)

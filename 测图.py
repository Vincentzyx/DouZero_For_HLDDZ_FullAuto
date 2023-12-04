from GameHelper import GameHelper
import numpy as np
import cv2
from main import MyPyQT_Form as form
from collections import defaultdict
import GameHelper as gh

helper = GameHelper()
helper.ScreenZoomRate = 1.0

img = cv2.imread("888.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
res1 = helper.LocateOnScreen("top_left_corner", img=img, region=(192, 700, 1448, 220), confidence=0.7)
res2 = helper.LocateOnScreen("top_right_corner", img=img, region=(192, 700, 1448, 220), confidence=0.7)
area = res1[0] + 15, res1[1] + 10, res2[0] - res1[0] - 100, 200
print(res1, res2)
if res1 is not None:
    res3 = helper.LocateOnScreen("top_left_corner", img=img, region=(192, 720, 1448, 200), confidence=0.7)
    print(res3)
    area = res3[0] + 15, res3[1] + 10, res2[0] - res3[0] - 100, 200

# img = img[pos[1]:pos[1]+pos[3], pos[0]:pos[0]+pos[2]]
cards = "KKQJT98765"
num = len(cards)
space = 57
pos_list = [(area[0] + i * space, area[1]) for i in range(num)]

# 将两个列表合并转为字典
cards_dict = defaultdict(list)
for key, value in zip(cards, pos_list):
    cards_dict[key].append(value)
# 转换为普通的字典
cards_dict = dict(cards_dict)
print(cards_dict)
i = "10"
cars_pos = cards_dict[i][-1][0:2]
print(cars_pos)

point = cars_pos[0] + 20, cars_pos[1] + 50
check_white = helper.LocateOnScreen("selected", img=img, region=(cars_pos[0], 700, 60, 90), confidence=0.85)
img = gh.DrawRectWithText(img, (cars_pos[0], 700, 60, 90), "test")
img = gh.DrawRectWithText(img, area, "test")
gh.ShowImg(img)

print("检查牌的上面有没有牌：", check_white)

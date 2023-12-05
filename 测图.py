from GameHelper import GameHelper
import numpy as np
import cv2
from main import MyPyQT_Form as form
from collections import defaultdict
import GameHelper as gh

helper = GameHelper()
helper.ScreenZoomRate = 1.0

img = cv2.imread("debug2.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
cards = "AAAKQQQJTT9876655"
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
from main import MyPyQT_Form as form
point = cars_pos[0] + 20, cars_pos[1] + 50
check_one = form.find_cards(img=img, pos=(cars_pos[0] + 5, 700, 60, 90), mark="m", confidence=0.8)
img = gh.DrawRectWithText(img, (cars_pos[0] + 5, 700, 60, 90), "test")
img = gh.DrawRectWithText(img, area, "test")
gh.ShowImg(img)

print("检查牌的上面有没有牌：", check_one)

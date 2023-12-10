from GameHelper import GameHelper
import numpy as np
import cv2
from main import MyPyQT_Form as form
from collections import defaultdict
import GameHelper as gh

GeneralBtnPos = (268, 481, 1240, 255)
helper = GameHelper()
helper.ScreenZoomRate = 1.0

img = cv2.imread("1.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
result = helper.LocateOnScreen("qiangdizhu_btn", img=img, region=GeneralBtnPos)
print(result)

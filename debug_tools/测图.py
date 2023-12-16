from GameHelper import GameHelper
import numpy as np
import cv2
from skimage.metrics import structural_similarity as ssim
from main import MyPyQT_Form as form
from collections import defaultdict
import GameHelper as gh

pos = (200, 450, 1000, 120)
helper = GameHelper()
# helper.ScreenZoomRate = 1.0
# img, _ = helper.Screenshot()
img = cv2.imread("9.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
result = helper.LocateOnScreen("buqiang_btn", img=img, region=pos, confidence=0.8)
# helper.ClickOnImage("bujiao_btn", img=img, region=GeneralBtnPos, confidence=0.8)
print(result)




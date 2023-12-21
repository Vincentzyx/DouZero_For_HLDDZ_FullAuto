import GameHelper as gh
from GameHelper import GameHelper
import cv2
import numpy as np

GameHelper = GameHelper()

img = cv2.imread("1.png")
# img = cv2.cvtColor(np.asarray(img), cv2.COLOR_BGR2RGB)
# img, _ = GameHelper.Screenshot()
img = gh.DrawRectWithText(img, (970, 510, 1200, 630), "test")

gh.ShowImg(img)

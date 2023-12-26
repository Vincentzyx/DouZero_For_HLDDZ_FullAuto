import GameHelper as gh
from GameHelper import GameHelper
import cv2
import numpy as np

GameHelper = GameHelper()

# img = cv2.imread("1.png")

img, _ = GameHelper.Screenshot()
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_BGR2RGB)
img = gh.DrawRectWithText(img, (180, 560, 1050, 90), "test")

gh.ShowImg(img)

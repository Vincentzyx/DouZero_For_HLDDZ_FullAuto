import GameHelper as gh
from GameHelper import GameHelper
import cv2
import numpy as np

GameHelper = GameHelper()
# img, _ = GameHelper.Screenshot()

img = cv2.imread("1.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_BGR2RGB)
# cv2.imwrite("111.png", img)

# img, _ = GameHelper.Screenshot()
img = gh.DrawRectWithText(img, (123, 243, 52, 54), "test")

gh.ShowImg(img)

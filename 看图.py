import cv2
import numpy as np
import GameHelper as gh
from GameHelper import GameHelper
from PIL import Image

GameHelper = GameHelper()
GameHelper.ScreenZoomRate = 1.0
img = cv2.imread("1.png")
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
gh.ShowImg(img)

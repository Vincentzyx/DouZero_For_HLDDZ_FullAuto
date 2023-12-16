import collections
import random
import time

import PIL
import GameHelper as gh
from GameHelper import GameHelper
import cv2
from PIL import Image
import numpy as np

helper = GameHelper()
helper.ScreenZoomRate = 1.0
import DetermineColor as DC

img = cv2.imread("30.png")
# img, _ = helper.Screenshot()
img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
cut_img = img[505:505 + 46, 344:344 + 36]
cv2.imwrite('999.png', cut_img)
print("保存完毕")
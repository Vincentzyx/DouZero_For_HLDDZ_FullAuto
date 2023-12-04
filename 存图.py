from GameHelper import GameHelper
from PIL import Image
import cv2

GameHelper = GameHelper()
GameHelper.ScreenZoomRate = 1.0
img, _ = GameHelper.Screenshot()
img.save("1.png")
print("图片保存成功")

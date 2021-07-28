import GameHelper as gh
from GameHelper import GameHelper

GameHelper = GameHelper()
GameHelper.ScreenZoomRate = 1.25
img, _ = GameHelper.Screenshot()
img = gh.DrawRectWithText(img, (313, 747, 1144, 200), "test")
img.save("test.png")
gh.ShowImg(img)
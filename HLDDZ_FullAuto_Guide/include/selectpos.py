import cv2
import include.GameHelper as gh
from include.GameHelper import GameHelper
import numpy as np
from include.tools import Logger

GameHelper = GameHelper()
GameHelper.ScreenZoomRate = 1.0
global img
global point1, point2


def on_mouse(event, x, y, flags, param):
    global img, point1, point2, cut_img
    img2 = img.copy()
    if event == cv2.EVENT_LBUTTONDOWN:  # 左键点击
        point1 = (x, y)
        cv2.circle(img2, point1, 10, (0, 255, 0), 2)
        cv2.imshow("image", img2)
    elif event == cv2.EVENT_MOUSEMOVE and (flags & cv2.EVENT_FLAG_LBUTTON):  # 按住左键拖曳
        cv2.rectangle(img2, point1, (x, y), (255, 0, 0), 2)
        cv2.imshow("image", img2)
    elif event == cv2.EVENT_LBUTTONUP:  # 左键释放
        point2 = (x, y)
        cv2.rectangle(img2, point1, point2, (0, 0, 255), 2)
        cv2.imshow("image", img2)
        min_x = min(point1[0], point2[0])
        min_y = min(point1[1], point2[1])
        width = abs(point1[0] - point2[0])
        height = abs(point1[1] - point2[1])
        cut_img = (min_x, min_y, width, height)
        Logger.Info(f"选区坐标为  {cut_img} ，关闭窗口生效")


def main():
    global img

    # img, _ = GameHelper.Screenshot()
    # img.save("111.png")
    img = cv2.imread("PrintScreen.png")
    # img = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)

    cv2.namedWindow("image")
    cv2.setMouseCallback("image", on_mouse)
    cv2.imshow("image", img)
    cv2.waitKey(0)
    return cut_img


if __name__ == "__main__":
    main()

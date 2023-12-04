import cv2
import numpy as np


class ColorClassify(object):
    def __init__(self, debug=True):
        self.debug = debug
        # 颜色范围，主要参考HSV颜色分量分布表：
        # 其中，gray和white进行了平衡中线调整，使白色占比更大些
        self.hsv_color = {
            "Gray": [(0, 180), (0, 43), (46, 150)],
            "White": [(0, 180), (0, 30), (151, 255)],
            "Red": [[(0, 10), (156, 180)], (43, 255), (46, 255)],
            "Orange": [(11, 25), (43, 255), (46, 255)],
            "Green": [(35, 77), (43, 255), (46, 255)],
            "Blue": [(100, 124), (43, 255), (46, 255)],
        }

        """{
            "Black": [(0, 180), (0, 255), (0, 46)],
            "Gray": [(0, 180), (0, 43), (46, 150)],
            "White": [(0, 180), (0, 30), (151, 255)],
            "Red": [[(0, 10), (156, 180)], (43, 255), (46, 255)],
            "Orange": [(11, 25), (43, 255), (46, 255)],
            "Yellow": [(26, 34), (43, 255), (46, 255)],
            "Green": [(35, 77), (43, 255), (46, 255)],
            "CyanBlue": [(78, 99), (43, 255), (46, 255)],
            "Blue": [(100, 124), (43, 255), (46, 255)],
            "Purple": [(125, 155), (43, 255), (46, 255)]
        }"""

    def get_hsv_hist(self, img_hsv):
        h, s, v = img_hsv[:, :, 0], img_hsv[:, :, 1], img_hsv[:, :, 2]

        h_bins = [0, 11, 26, 35, 78, 100, 125, 156, 180]
        h_hist = np.histogram(h, h_bins)
        s_bins = [0, 30, 43, 255]
        s_hist = np.histogram(s, s_bins)
        v_bins = [0, 46, 151, 255]
        v_hist = np.histogram(v, v_bins)

        return [h_hist, s_hist, v_hist]

    def get_hsv_info(self, h_hist, s_hist, v_hist):
        infos = {
            "h": {
                "hist": h_hist,
                "argsort": None,
                "sort_normal": None,
                "arg_values": [],
            },
            "s": {
                "hist": s_hist,
                "argsort": None,
                "sort_normal": None,
                "arg_values": [],
            },
            "v": {
                "hist": v_hist,
                "argsort": None,
                "sort_normal": None,
                "arg_values": [],
            }
        }
        for k in infos:
            hist = infos[k]['hist']
            argsort = np.argsort(hist[0])[::-1][:2]  # 逆序排列, 取前面最大的两个
            infos[k]['argsort'] = argsort
            infos[k]['sort_normal'] = hist[0][argsort] / (sum(hist[0]) * 3)
            for idx in argsort:
                value_mean = round(np.mean([hist[1][idx], hist[1][idx + 1]]))
                infos[k]['arg_values'].append(value_mean)
        return infos

    def get_hsv_main_info(self, h_hist, s_hist, v_hist):
        h_main_idx = np.argmax(h_hist[0])
        h_main = [h_hist[1][h_main_idx], h_hist[1][h_main_idx + 1]]

        s_weights = np.array([1, 1, 1])
        s_array = s_hist[0] * s_weights
        s_main_idx = np.argmax(s_array)
        s_main = [s_hist[1][s_main_idx], s_hist[1][s_main_idx + 1]]

        v_weights = np.array([1, 1, 1])
        v_array = v_hist[0] * v_weights
        v_main_idx = np.argmax(v_array)
        v_main = [v_hist[1][v_main_idx], v_hist[1][v_main_idx + 1]]

        if self.debug:
            print("h_hist: {}\ns_hist: {}\nv_hist: {}".format(h_hist, s_hist, v_hist))
            print("h_main: {}, s_main: {}, v_main: {}".format(h_main, s_main, v_main))
        return np.mean(h_main), np.mean(s_main), np.mean(v_main)

    def hsv2color(self, infos):
        # print(infos)
        h_info = infos['h']
        s_info = infos['s']
        v_info = infos['v']
        result = {}
        for snh, avh in zip(h_info['sort_normal'], h_info['arg_values']):
            for sns, avs in zip(s_info['sort_normal'], s_info['arg_values']):
                for snv, avv in zip(v_info['sort_normal'], v_info['arg_values']):
                    cls = self.hsv2color_one(avh, avs, avv)
                    if cls is None:
                        pass
                        # print(avh, avs, avv)
                        continue
                    score = snh + sns + snv
                    if cls in result.keys():
                        result[cls] = max(score, result[cls])
                    else:
                        result[cls] = score
        return sorted(result.items(), key=lambda kv: (kv[1], kv[0]))[::-1]

    def hsv2color_one(self, h_mean, s_mean, v_mean):
        for cls, value in self.hsv_color.items():
            if isinstance(value[0], list):
                h_flag = value[0][0][0] <= h_mean <= value[0][0][1] or value[0][1][0] <= h_mean <= value[0][1][1]
            else:
                h_flag = value[0][0] <= h_mean <= value[0][1]
            s_flag = value[1][0] <= s_mean <= value[1][1]
            v_flag = value[2][0] <= v_mean <= value[2][1]
            if h_flag and s_flag and v_flag:
                return cls
        return None

    def classify(self, img):
        img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        h_hist, s_hist, v_hist = self.get_hsv_hist(img_hsv)

        # 仅用hsv每个分量的最大值
        # h_mean, s_mean, v_mean = self.get_hsv_main_info(h_hist, s_hist, v_hist)
        # return self.hsv2color_one(h_mean, s_mean, v_mean)

        infos = self.get_hsv_info(h_hist, s_hist, v_hist)
        return self.hsv2color(infos)


if __name__ == "__main__":
    classifier = ColorClassify(debug=True)
    img = cv2.imread("pics/ob8.png")
    result = classifier.classify(img)
    print(result)
    cls, score = result[1]
    for i in result:
        print(i[0])
        if i[0] == "Red":
            print(i[1])

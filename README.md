# DouZero_For_HLDDZ_FullAuto: 将DouZero用于欢乐斗地主自动化
* 本项目基于[DouZero](https://github.com/kwai/DouZero) 和  [DouZero_For_Happy_DouDiZhu](https://github.com/tianqiraf/DouZero_For_HappyDouDiZhu)
* 感谢 girgle（QQ群马云）对新版欢乐斗地主进行了适配，现在仓库代码已支持新版欢乐斗地主

* 环境配置请移步项目DouZero

* 模型默认为ADP，更换模型请修改main.py中的模型路径，如果需要加载Resnet新模型，请保证游戏路径或文件名中存在关键词 "resnet"

  ```python
  self.card_play_model_path_dict = {
      'landlord': "baselines/resnet_landlord.ckpt",
      'landlord_up': "baselines/resnet_landlord_up.ckpt",
      'landlord_down': "baselines/resnet_landlord_down.ckpt"
  }
  ```

* 

* 运行main.py即可

* 在原 [DouZero_For_Happy_DouDiZhu](https://github.com/tianqiraf/DouZero_For_HappyDouDiZhu) 的基础上加入了自动出牌，基于手牌自动叫牌，加倍，同时修改截屏方式为窗口区域截屏，游戏原窗口遮挡不影响游戏进行。

*   **请勿把游戏界面最小化，否则无法使用**

## 说明
*   欢乐斗地主使用 **窗口** 模式运行
*   **如果觉得这个项目有用，请给一个Star谢谢！**
*   **本项目仅供学习以及技术交流，请勿用于其它目的，否则后果自负。**

## 使用步骤（最新版本跳过此步骤）
1. 先使用 `debug_screenshot.py`  确认自己的屏幕缩放比

2. 修改 `main.py` 中屏幕缩放比为自己屏幕的缩放比

3. 点击游戏中开始游戏后点击程序的 `自动开始`

4. 如果需要自动继续下一把，点击单局按钮，使其变为自动

## 自动叫牌/加倍原理

用DouZero自我博弈N局，对于随机到的每种手牌，随机生成若干种对手手牌，把该牌型和赢的局数扔进一个简单的全连接网络进行训练，得到手牌与胜率之间的关系，最后根据预期胜率，以一定阈值进行叫牌和加倍。

## 潜在Bug
*   有较低几率把王炸识别为不出


## 鸣谢
*   本项目基于[DouZero](https://github.com/kwai/DouZero)  [DouZero_For_Happy_DouDiZhu](https://github.com/tianqiraf/DouZero_For_HappyDouDiZhu) 

## 其他

欢迎加入QQ群交流自动化相关：565142377  密码 douzero

也可以在原作者[DouZero_For_Happy_DouDiZhu](https://github.com/tianqiraf/DouZero_For_HappyDouDiZhu) 的QQ群交流


                                                       使用说明
                                                       
* 第一步：安装完python环境之后在pycharm上运行main.py（游戏设置为窗口模式，不需要改分辨率和缩放比。
  * 注意：
  * 1.不要拉伸默认的窗口大小，一不小心拉伸窗口的朋友，请自行从网上找句柄工具将窗口恢复到默认的1440×810大小。
  * 2.游戏背景要使用默认的蓝色桌子，不然识别会有问题）。  
* 第二步：全屏进入新版QQ欢乐斗地主。
* 第三步：点击《斗地主合集》，再进入欢乐经典场或经典场（推荐经典场，因为欢乐经典场炸弹太多）  。
* 第四步：选择相对应的场次。
* 第五步：进入到游戏的开始界面。
* 第六步：点击软件的手动或自动开始（优点：出牌的时候可以在手动和自动之间切换）。

* 最后感谢大家的理解和支持，一个人的力量有限，希望大家多多反馈BUG，确认后我会尽快处理。

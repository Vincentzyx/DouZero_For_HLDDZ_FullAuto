# DouZero_For_HLDDZ_FullAuto: 将DouZero用于欢乐斗地主自动化
* 本项目基于[DouZero](https://github.com/kwai/DouZero) 和  [DouZero_For_Happy_DouDiZhu](https://github.com/tianqiraf/DouZero_For_HappyDouDiZhu) 

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

## 使用步骤
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

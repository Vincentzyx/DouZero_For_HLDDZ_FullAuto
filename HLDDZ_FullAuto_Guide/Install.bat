@echo off
chcp 65001
echo 正在获取pip版本，若版本过低，会自动升级
echo.
echo.

echo ===============================================
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pip -U
echo ===============================================
echo.
echo.

echo 正在获取环境依赖
echo ===============================================

pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
echo ===============================================
echo.
echo.
echo 环境配置完成
echo 请关闭此窗口继续操作


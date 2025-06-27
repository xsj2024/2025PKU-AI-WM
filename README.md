# 2025年北大AI基础大作业未名组
组成员：周泽坤，谢尚杰，徐恺，焦思源

## 项目综述
这是一个自动游玩Slay the Spire游戏的脚本。Slay the Spire是一款经典的卡牌Rougue游戏，其具有丰富巧妙的游戏设计，对玩家的熟练度和思维能力有很高的要求。

我们写的脚本可以在VScode中运行，也可以运行打包好的.exe文件。

在开始运行脚本前，需要提前安装和打开Slay the Spire游戏本体的窗口，并进入游戏，注意调节输入法为EN。

脚本开始运行后，预期就不再需要人工的输入，而是由大模型做出所有关键决策。并通过控制鼠标和键盘完成这些操作。

## 环境依赖
如果你希望在VScode中运行该程序，下面是你可能需要在环境中配置的库：(建议使用pip install安装这些库)

（也可以在requirements.txt中看到）

（如果你只想运行text_spire，即脚本本身，标注“非必要”的库可以不安装。）

### AI和机器学习相关
camel-ai

torch（非必要）

torchvision（非必要）

ultralytics

scikit-learn（非必要）

numpy

scipy（非必要）

### 计算机视觉和图像处理
opencv-python

Pillow（非必要）

### OCR相关
easyocr（非必要）

paddleocr（非必要）

cnocr

onnxruntime（非必要）

### 环境配置
python-dotenv

### 界面和系统交互
pyautogui

keyboard

### 数据处理和进度条
tqdm（非必要）

pandas（非必要）

### 深度学习框架相关
paddle-bfloat（非必要）

paddlepaddle（非必要）

### 其他实用库

typing-extensions（非必要）

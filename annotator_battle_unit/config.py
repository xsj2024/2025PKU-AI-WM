import os
from pathlib import Path
import torch

class Config:
    # 项目根目录
    BASE_DIR = Path(__file__).parent
    
    # 模型配置
    MODEL_NAME = "yolov8n.pt"  # 默认使用YOLOv8nano模型
    MODEL_PATH = str(BASE_DIR / "models" / MODEL_NAME)

    CAPTURE_INTERVAL = 0.033  # 30 FPS (~0.033秒)
    
    # 窗口捕获配置
    CAPTURE_INTERVAL = 0.1  # 截图间隔(秒)
    GAME_WINDOW_TITLE = "Modded Slay the Spire"
    MAX_FOCUS_ATTEMPTS = 3  # 最大焦点尝试次数
    
    # 覆盖层配置
    OVERLAY_COLOR = (0, 255, 0)  # BGR颜色格式
    OVERLAY_OPACITY = 0.5  # 0-1之间的透明度值
    OVERLAY_THICKNESS = 2
    OVERLAY_FONT_SCALE = 0.5
    
    YOLO_DATA_DIR = str(BASE_DIR / "yolo_dataset")  # YOLO格式数据集目录
    YOLO_DATA_DIR_REAL = str(BASE_DIR / "yolo_dataset/real")  # YOLO格式数据集目录
    # YOLO_DATA_DIR_REAL = str(BASE_DIR / "yolo_dataset/tempdata")  # YOLO格式数据集目录
    _CLASS_NAMES = []  # 你的具体类别列表

    TRAIN_VAL_SPLIT = 0.8  # 训练集比例
    
    # 训练参数
    TRAIN_EPOCHS = 20
    AUGMENT_FACTOR = 50 # 每张图片数据增强数量
    # 图像尺寸处理配置
    IMAGE_SIZE = 640  # 模型输入尺寸（正方形）
    PAD_COLOR = (114, 114, 114)  # 填充色（YOLO标准灰色）
    SCALE_FILL = False  # True=拉伸填充 False=保持比例填充
    AUTO_ORIENT = False  # 自动旋转方向不正的图片
    DEVICE = "0"  # "0"=GPU, "cpu"=CPU
    FONT_SIZE_PT = 15

    MIN_SAMPLES = 1

    # 模型初始化配置
    INIT_WITH_COCO = False  # 设为True则加载COCO权重，False则初始化空白模型
    MODEL_STRICT_LOAD = False  # 允许加载不匹配的权重（用于空白初始化）

    BATCH_SIZE = 8  # 基础值
    # if torch.cuda.get_device_properties(0).total_memory < 8e9:  # <8GB显存
    #     BATCH_SIZE = 4

    # 增强强度配置（根据样本量自动调节）
    AUG_INTENSITY = 0.5  # 0-1范围，0.5为中等强度

    CONF_THRESHOLD = 0.5 # 置信度阈值
    
    # 基础增强
    BASE_AUG = {
        'hsv_h': 0.015,
        'hsv_s': 0.7,
        'hsv_v': 0.4,
        'translate': 0.1,
        'scale': 0.5,
        'flipud': 0.15,
        'fliplr': 0.5
    }
    
    # 高级增强（样本量<100时激活）
    ADVANCED_AUG = {
        'mosaic': 0.8,
        'mixup': 0.3,
        'cutout': 0.5,
        'grid_mask': 0.5
    }

    @classmethod
    def load_class_name(cls):
        with open(os.path.join(cls.YOLO_DATA_DIR,"class_names.txt"),"r") as f:
            cls._CLASS_NAMES = eval(f.readline())

    @classmethod
    def save_class_name(cls):
        with open(os.path.join(cls.YOLO_DATA_DIR,"class_names.txt"),"w") as f:
            f.write(str(cls._CLASS_NAMES))

    @classmethod
    def query_class_id(cls, name):
        if name not in cls._CLASS_NAMES:
            cls._CLASS_NAMES.append(name)
            cls.save_class_name()
            return cls._CLASS_NAMES.__len__() - 1
        else:
            return cls._CLASS_NAMES.index(name)
    
    @classmethod
    def query_class_name(cls, ind):
        return cls._CLASS_NAMES[ind]
Config.load_class_name()
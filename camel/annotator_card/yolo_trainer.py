from ultralytics import YOLO
import os
from .config import Config
from .dataset_manager import DatasetManager
import shutil
import time

class YOLOTrainer:
    def __init__(self):
        self.model = None
        
    def prepare_training(self):
        """准备训练环境"""
        # 生成dataset.yaml
        yaml_path = DatasetManager.generate_yaml()
        
        return yaml_path

    def train(self):
        """执行训练流程"""
        yaml_path = self.prepare_training()
        
        # 初始化模型
        self.model = YOLO(Config.MODEL_NAME)
        timestamp = int(time.time())
        name = f"train{timestamp}"

        # 训练参数
        results = self.model.train(
            data=yaml_path,
            epochs=Config.TRAIN_EPOCHS,
            imgsz=Config.IMAGE_SIZE,
            device=Config.DEVICE,
            project=os.path.join(Config.YOLO_DATA_DIR, "runs"),
            name=name,
            rect=False,
        )
        shutil.copyfile(os.path.join(Config.YOLO_DATA_DIR, "runs",name,"weights/best.pt"), Config.MODEL_PATH)
        
        return results

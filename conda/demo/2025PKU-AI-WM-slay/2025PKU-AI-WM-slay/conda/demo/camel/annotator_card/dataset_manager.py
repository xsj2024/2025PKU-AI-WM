import os
import cv2
import numpy as np
from .config import Config
from .image_processor import ImageProcessor
from pathlib import Path
import yaml
import random
import shutil

class DatasetManager:
    @staticmethod
    def generate_yaml():
        """自动生成dataset.yaml文件"""
        yaml_path = os.path.join(Config.YOLO_DATA_DIR, "dataset.yaml")
        content = {
            "path": str(Path(Config.YOLO_DATA_DIR).resolve()),
            "train": "images",
            "val": "images",
            "names": {i: name for i, name in enumerate(Config._CLASS_NAMES)}
        }
        
        with open(yaml_path, 'w') as f:
            yaml.dump(content, f, sort_keys=False)
            
        print(f"Generated dataset.yaml at {yaml_path}")
        return yaml_path
    
    @staticmethod
    def process_image(img_path):
        """处理单张图片并保存"""
        img = cv2.imread(img_path)
        processed, ratios = ImageProcessor.auto_pad(img)
        cv2.imwrite(img_path, processed)
        return ratios  # 返回缩放比例用于调整标注坐标
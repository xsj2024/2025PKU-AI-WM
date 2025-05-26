from ultralytics import YOLO
import os
from pathlib import Path
from .config import Config
from .image_processor import ImageProcessor
import numpy as np

class ModelManager:
    def __init__(self, model_path=None):
        self.model = None
        self.model_path = model_path or Config.MODEL_PATH
        self._init_model()

    def _init_model(self):
        """Initialize YOLO model with error handling"""
        # 创建模型目录如果不存在
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        
        print(f"Loading model from: {self.model_path}")
        if Config.INIT_WITH_COCO:
            print("Loading COCO-pretrained model...")
            self.model = YOLO(self.model_path)  # 正常加载预训练
        else:
            print("Initializing blank model...")
            # 关键步骤：创建无预权重的模型结构
            if os.path.exists(self.model_path):
                print(f"加载已有模型: {self.model_path}")
                self.model = YOLO(self.model_path,)
            else:
                print(f"创建空白模型并保存到: {self.model_path}")
                self.model = YOLO("yolov8n.yaml")  # 仅加载架构文件
                self.model.save(self.model_path)  # 保存空白模型
        print("Model initialized")
        
    def detect_all(self, image):
        """优化版检测函数（含坐标修正和异常处理）"""
        # 输入验证
        if image is None or image.size == 0:
            return []

        try:
            orig_h, orig_w = image.shape[:2]
            processed, ratios, pads = ImageProcessor.auto_pad(image)
            w_ratio, h_ratio = ratios
            pad_top, pad_left = pads if pads else (0, 0)
            results = self.model(processed, verbose=False, conf=Config.CONF_THRESHOLD)
            output = []
            for result in results:
                if not hasattr(result, 'boxes') or result.boxes is None:
                    continue
                boxes_tensor = result.boxes.data.clone()
                boxes = boxes_tensor.cpu().numpy()
                boxes[:, [0, 2]] /= w_ratio
                boxes[:, [1, 3]] /= h_ratio
                boxes[:, [0, 2]] -= pad_left
                boxes[:, [1, 3]] -= pad_top
                boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, orig_w - 1)
                boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, orig_h - 1)
                cls_ids = result.boxes.cls.cpu().numpy().astype(int)
                names = getattr(result, 'names', {})
                for box, cls_id in zip(boxes, cls_ids):
                    label = names.get(cls_id, cls_id)
                    x1, y1, x2, y2 = map(int, box[:4])
                    output.append((label, x1, y1, x2, y2))
            return output
        except Exception as e:
            print(f"Detection error: {str(e)}")
            return []

    def detect_existing(self, image):
        """检测图像中是否已存在标注（基于当前模型）"""
        if image is None or image.size == 0:
            return False
            
        # 这里可以添加你的检测逻辑
        results = self.detect_all(image)
        return len(results[0].boxes) > 0 if results else False

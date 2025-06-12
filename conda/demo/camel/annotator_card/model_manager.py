from ultralytics import YOLO
import os
from pathlib import Path
from .config import Config
from .image_processor import ImageProcessor
import numpy as np
import cv2

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
            return None

        try:
            orig_h, orig_w = image.shape[:2]
            
            # 显式获取填充参数（假设auto_pad返回: processed_img, (w_ratio, h_ratio), (pad_top, pad_left)）
            processed, ratios, pads = ImageProcessor.auto_pad(image)
            w_ratio, h_ratio = ratios
            pad_top, pad_left = pads if pads else (0, 0)  # 兼容无padding的情况

            # 模型推理
            results = self.model(processed, verbose=False,conf=Config.CONF_THRESHOLD)

            for result in results:
                if not hasattr(result, 'boxes') or result.boxes is None:
                    continue

                # 获取原始数据（保留设备信息）
                boxes_tensor = result.boxes.data.clone()  # 避免修改原始tensor
                # 如果置信度低于阈值，直接跳过
                # confidences = boxes_tensor[:, 4].cpu().numpy()  # 置信度通常在结果的第5列

                # print(confidences)
                # if confidences < Config.CONF_THRESHOLD:
                #     continue
                boxes = boxes_tensor.cpu().numpy()

                # 坐标修正分两步：
                # 1. 先缩放回原始图像比例
                boxes[:, [0, 2]] /= w_ratio  # x坐标
                boxes[:, [1, 3]] /= h_ratio  # y坐标
                
                # 2. 减去填充区域的偏移（关键修正！）
                boxes[:, [0, 2]] -= pad_left
                boxes[:, [1, 3]] -= pad_top

                # 边界保护
                boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, orig_w - 1)
                boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, orig_h - 1)

                # 重构Boxes对象（保持原设备）
                result.boxes = type(result.boxes)(
                    boxes_tensor.new_tensor(boxes),  # 自动继承原设备
                    orig_shape=(orig_h, orig_w)
                )
            return results

        except Exception as e:
            print(f"Detection error: {str(e)}")
            return None




    def detect_existing(self, image):
        """检测图像中是否已存在标注（基于当前模型）"""
        if image is None or image.size == 0:
            return False
            
        # 这里可以添加你的检测逻辑
        results = self.detect_all(image)
        return len(results[0].boxes) > 0 if results else False

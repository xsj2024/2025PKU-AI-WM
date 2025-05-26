import cv2
import json
import os
import numpy as np
from config import Config
import time
from yolo_trainer import YOLOTrainer  # 顶部新增导入
from augment_manager import YOLOAugmenter
import shutil

class AnnotationTool:
    def __init__(self, model_manager):
        self.model = model_manager
        self.drawing = False
        self.ix, self.iy = -1, -1  # 选框起始坐标
        self.fx, self.fy = -1, -1  # 选框结束坐标
        self.current_bbox = None    # 当前选框
        self.active = False         # 标注模式激活状态
        self._init_yolo_dirs()  # 新增初始化方法

    def _init_yolo_dirs(self):
        """初始化YOLO所需的所有目录"""
        dirs = [
            "images", "real/images",
            "labels", "real/labels",
            "runs"
        ]
        for d in dirs:
            os.makedirs(os.path.join(Config.YOLO_DATA_DIR, d), exist_ok=True)
    
    def enter_annotation_mode(self):
        """进入标注模式"""
        self.active = True
        self.reset_state()
        
    def exit_annotation_mode(self):
        """退出标注模式"""
        self.active = False
        self.reset_state()

    def reset_state(self):
        """重置标注状态"""
        self.drawing = False
        self.ix = self.iy = -1
        self.fx = self.fy = -1
        self.current_bbox = None

    def process_frame(self, frame):
        """
        在帧上处理标注逻辑
        返回带标注的帧和当前选框状态 (x,y,w,h)
        """
        display = frame.copy()
        
        if not self.active:
            return display, None

        # 绘制当前选框（如果存在）
        if self.drawing and self.ix != -1 and self.iy != -1:
            cv2.rectangle(display, (self.ix, self.iy), (self.fx, self.fy), (0, 255, 0), 1)
            
        # 绘制提示文本
        cv2.putText(display, "ANNOTATION MODE", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(display, "Drag left mouse to select | ESC to cancel | ENTER to confirm", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

        return display, self.current_bbox

    def handle_mouse(self, event, x, y, flags):
        """处理鼠标事件（由主窗口调用）"""
        if not self.active:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.ix, self.iy = x, y
            self.fx, self.fy = x, y
            
        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.fx, self.fy = x, y
                # 实时计算当前选框
                self.current_bbox = (
                    min(self.ix, self.fx),
                    min(self.iy, self.fy),
                    abs(self.fx - self.ix),
                    abs(self.fy - self.iy)
                )
                
        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.fx, self.fy = x, y
            self.current_bbox = (
                min(self.ix, self.fx),
                min(self.iy, self.fy),
                abs(self.fx - self.ix),
                abs(self.fy - self.iy)
            )

    def confirm_selection(self):
        """确认当前选框"""
        if self.current_bbox and self.current_bbox[2] > 5 and self.current_bbox[3] > 5:
            return self.current_bbox
        return None

    # def label_region(self, frame, bbox):
    #     """标注区域（同你的原始实现）"""
    #     x, y, w, h = bbox
    #     cropped = frame[y:y+h, x:x+w]
        
    #     if self.model.detect_existing(cropped):
    #         print("Similar object already exists in database")
    #         return False
            
    #     cv2.imshow("Selected Region", cropped)
    #     print("Enter label for this object: ")
    #     label = input().strip()
    #     cv2.destroyWindow("Selected Region")
        
    #     if not label:
    #         return False
            
    #     self._save_annotation(cropped, bbox, label)
    #     return True
    def label_region(self, full_frame, bbox):
        """标注区域（基于完整图像）"""
        x, y, w, h = bbox
        if self.model.detect_existing(full_frame[y:y+h, x:x+w]):  # 仅在裁剪区域做检测
            print("Similar object already exists in database")
            return False
            
        # 显示选框预览（可选）
        preview = full_frame.copy()
        cv2.rectangle(preview, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.imshow("Selected Region", preview)
        
        # 输入标签
        print("Enter label for this object: ")
        label = input().strip()
        cv2.destroyAllWindows()
        
        if not label:
            return False
            
        self._save_annotation(full_frame, bbox, label)  # 传递完整图像
        return True

        
    def _save_annotation(self, full_image, bbox, label):
        """保存完整图像 + YOLO格式标注"""
        timestamp = int(time.time())
        
        # 保存完整图像（而非裁剪区域）
        img_path = os.path.join(Config.YOLO_DATA_DIR_REAL, "images", f"{timestamp}.png")
        cv2.imwrite(img_path, full_image)
        
        # 用完整图像的尺寸生成YOLO标注
        self._save_yolo_label(full_image, bbox, label, timestamp)

    def _save_yolo_label(self, full_image, bbox, label, timestamp):
        """生成YOLO格式的txt标注文件（基于完整图像尺寸）"""
        try:
            class_id = Config.CLASS_NAMES.index(label.lower())
        except ValueError:
            class_id = 0  # 默认类别

        # 获取完整图像尺寸
        img_h, img_w = full_image.shape[:2]  # OpenCV格式是(height, width)
        
        # 提取BBox参数（注意x,y是左上角，w,h是宽度和高度）
        x, y, w, h = bbox
        
        # 计算中心点坐标（归一化）
        x_center = (x + w/2) / img_w
        y_center = (y + h/2) / img_h
        width_norm = w / img_w
        height_norm = h / img_h
        
        # 确保值合法（避免越界）
        x_center = np.clip(x_center, 0, 1)
        y_center = np.clip(y_center, 0, 1)
        width_norm = np.clip(width_norm, 0, 1 - x_center)
        height_norm = np.clip(height_norm, 0, 1 - y_center)
        
        # 写入标签文件
        label_path = os.path.join(Config.YOLO_DATA_DIR_REAL, "labels", f"{timestamp}.txt")
        with open(label_path, 'w') as f:
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}")

    def check_dataset_ready(self, min_samples=1):
        """Check if enough samples collected for training"""
        img_dir = os.path.join(Config.YOLO_DATA_DIR_REAL, "images")
        count = len(os.listdir(img_dir))
        print(f"Current dataset size: {count}/{min_samples}")
        return count >= Config.MIN_SAMPLES
    def get_yolo_dataset_stats(self):
        """Print statistics about collected data"""
        img_dir = os.path.join(Config.YOLO_DATA_DIR_REAL, "images")
        label_dir = os.path.join(Config.YOLO_DATA_DIR_REAL, "labels")
        
        print("\nYOLO Dataset Statistics:")
        print(f"- Images: {len(os.listdir(img_dir))}")
        print(f"- Labels: {len(os.listdir(label_dir))}")
        
        # Count per class
        class_counts = {name: 0 for name in Config.CLASS_NAMES}
        for label_file in os.listdir(label_dir):
            with open(os.path.join(label_dir, label_file)) as f:
                for line in f:
                    class_id = int(line.split()[0])
                    class_counts[Config.CLASS_NAMES[class_id]] += 1
        
        print("\nClass Distribution:")
        for name, count in class_counts.items():
            print(f"- {name}: {count}")
    def start_training(self):
        """启动训练流程"""
        if not self.check_dataset_ready():
            print(f"Not enough samples (min {Config.MIN_SAMPLES} required)")
            return False
        try:
            shutil.rmtree(os.path.join(Config.YOLO_DATA_DIR,"images"))
        except: pass
        try:
            shutil.rmtree(os.path.join(Config.YOLO_DATA_DIR,"labels"))
        except: pass
        augmenter = YOLOAugmenter(Config.YOLO_DATA_DIR, augment_factor=50)
        augmenter.process_dataset(Config.YOLO_DATA_DIR_REAL)  # 替换为你的数据集路径

        print("Starting YOLO training...")

        trainer = YOLOTrainer()
        result = trainer.train()

        try:
            shutil.rmtree(os.path.join(Config.YOLO_DATA_DIR,"images"))
        except: pass
        try:
            shutil.rmtree(os.path.join(Config.YOLO_DATA_DIR,"labels"))
        except: pass

        if result:
            print("Training completed successfully!")
            return True
        return False
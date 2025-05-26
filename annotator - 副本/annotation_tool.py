import cv2
import json
import os
import numpy as np
from config import Config
import time
from yolo_trainer import YOLOTrainer
from augment_manager import YOLOAugmenter
import shutil

class AnnotationTool:
    def __init__(self, model_manager):
        self.drawing = False
        self.ix, self.iy = -1, -1  # 选框起始坐标
        self.fx, self.fy = -1, -1  # 选框结束坐标
        self.current_bbox = None    # 当前选框
        self.active = False         # 标注模式激活状态
        self.annotations = []       # 存储多个标注的列表
        self.current_label = None   # 当前正在处理的标签
        self.selected_annotation_index = -1  # 当前选中的标注索引
        self._init_yolo_dirs()

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
        self.annotations = []
        
    def exit_annotation_mode(self):
        """退出标注模式"""
        self.active = False
        self.reset_state()
        self.annotations = []


    def reset_state(self):
        """重置标注状态"""
        self.drawing = False
        self.ix = self.iy = -1
        self.fx = self.fy = -1
        self.current_bbox = None
        self.selected_annotation_index = -1  # 重置选中状态

    def process_frame(self, frame):
        """
        在帧上处理标注逻辑
        返回带标注的帧和当前选框状态 (x,y,w,h)
        """
        display = frame.copy()
        
        if not self.active:
            return display, None, self.annotations

        # 绘制所有已确认的标注（带选中状态）
        for i, annotation in enumerate(self.annotations):
            bbox = annotation["bbox"]
            label = annotation["label"]
            if i == self.selected_annotation_index:
                # 选中的标注用红色显示
                color = (0, 0, 255)
                thickness = 3
                # 显示删除提示
                cv2.putText(display, "Press 'D' to DELETE", (bbox[0], bbox[1]-30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
            else:
                color = (0, 255, 255)
                thickness = 2
            self._draw_annotation(display, bbox, label, color, thickness)
            
        # 绘制当前选框（如果存在）
        if self.drawing and self.ix != -1 and self.iy != -1:
            cv2.rectangle(display, (self.ix, self.iy), (self.fx, self.fy), (0, 255, 0), 1)
            
        # 绘制提示文本
        # cv2.putText(display, f"ANNOTATION MODE (Current: {self.current_label or 'None'})", 
        #            (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        # cv2.putText(display, "Drag left mouse to select | ESC to cancel | ENTER to confirm", 
        #            (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
        # cv2.putText(display, f"Annotations: {len(self.annotations)} | Q to finish | D to delete", 
        #            (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)

        return display, self.current_bbox, self.annotations

    def _draw_annotation(self, frame, bbox, label, color=(0, 255, 255), thickness=2):
        """绘制单个已确认的标注"""
        x, y, w, h = bbox
        # print("Draw ",(x,y),(x+w,y+h),label,bbox)
        cv2.rectangle(frame, (x, y), (x+w, y+h), color, thickness)
        cv2.putText(frame, label, (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    def handle_mouse(self, event, x, y, flags):
        """处理鼠标事件（由主窗口调用）"""
        if not self.active:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            # 检查是否点击了现有标注
            clicked_index = self._get_clicked_annotation(x, y)
            if clicked_index >= 0:
                self.selected_annotation_index = clicked_index
                return
            
            # 否则开始新的标注
            self.drawing = True
            self.ix, self.iy = x, y
            self.fx, self.fy = x, y
            self.selected_annotation_index = -1  # 开始新标注时取消选中
            
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

    def _get_clicked_annotation(self, x, y):
        """检测是否点击了现有标注框"""
        for i, annotation in enumerate(self.annotations):
            bx, by, bw, bh = annotation["bbox"]
            if (bx <= x <= bx + bw) and (by <= y <= by + bh):
                return i
        return -1

    def delete_selected_annotation(self):
        """删除当前选中的标注"""
        if 0 <= self.selected_annotation_index < len(self.annotations):
            del self.annotations[self.selected_annotation_index]
            self.selected_annotation_index = -1
            return True
        return False

    def norm(self, img_w, img_h):
        x,y,w,h = self.current_bbox
        x=max(x,0)
        x=min(x,img_w)
        y=max(y,0)
        y=min(y,img_h)
        w=min(w,img_w-x)
        h=min(h,img_h-y)
        self.current_bbox = (x,y,w,h)

    def confirm_selection(self, img_w, img_h):
        """确认当前选框并保存为标注"""
        if not self.current_bbox or self.current_bbox[2] <= 5 or self.current_bbox[3] <= 5:
            return False
            
        # 显示选框预览
        print("Enter label for this object (leave empty to cancel): ")
        label = input().strip()
        
        if not label:
            self.reset_state()
            return False
            
        # 检查是否已存在相似对象
        if not self.validate_new_annotation(self.current_bbox, label):
            return False
            
        # 添加到标注列表
        self.norm(img_w, img_h)
        self.annotations.append({
            "bbox": self.current_bbox,
            "label": label,
        })
        
        self.current_label = label
        self.reset_state()
        return True

    def validate_new_annotation(self, bbox, label):
        """验证新标注是否有效且不重复"""
        x, y, w, h = bbox
        
        # 检查是否有重叠的现有标注
        for existing in self.annotations:
            ex, ey, ew, eh = existing["bbox"]
            # 简单的重叠检测
            if (x < ex + ew and x + w > ex and
                y < ey + eh and y + h > ey and
                existing["label"] == label):
                print(f"Warning: Overlapping annotation with same label '{label}' detected!")
                return False
                
        return True

    def finalize_annotations(self,full_image):
        """保存所有标注到文件"""
        if not self.annotations:
            return False
            
        # 生成唯一ID
        timestamp = int(time.time())
        img_path = os.path.join(Config.YOLO_DATA_DIR_REAL, "images", f"{timestamp}.png")
        cv2.imwrite(img_path, full_image)
        
        # 获取最后一帧（假设主程序会提供）
        # 需要从主窗口获取当前帧
        # cv2.imwrite(img_path, current_frame)
        
        # 保存YOLO格式标签
        img_h, img_w = full_image.shape[:2]
        self._save_yolo_labels(timestamp,img_w, img_h)
        
        # 重置状态
        self.annotations = []
        self.current_label = None
        self.selected_annotation_index = -1
        return True

    def _save_yolo_labels(self, timestamp, img_width, img_height):
        """保存所有当前标注为YOLO格式"""
        label_path = os.path.join(Config.YOLO_DATA_DIR_REAL, "labels", f"{timestamp}.txt")
        
        with open(label_path, 'w') as f:
            for annotation in self.annotations:
                bbox = annotation["bbox"]
                label = annotation["label"]
                
                try:
                    class_id = Config.query_class_id(label.lower())
                except ValueError:
                    class_id = 0
                
                x, y, w, h = bbox
                
                # 转换为中心点+宽高格式并归一化
                x_center = (x + w/2) / img_width
                y_center = (y + h/2) / img_height
                width_norm = w / img_width
                height_norm = h / img_height
                
                # 写入文件
                f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width_norm:.6f} {height_norm:.6f}\n")

    # 保留原有方法...
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
        class_counts = {name: 0 for name in Config.__CLASS_NAMES}
        for label_file in os.listdir(label_dir):
            with open(os.path.join(label_dir, label_file)) as f:
                for line in f:
                    class_id = int(line.split()[0])
                    class_counts[Config.query_class_name(class_id)] += 1
        
        print("\nClass Distribution:")
        for name, count in class_counts.items():
            print(f"- {name}: {count}")

    def start_training(self):
        """启动训练流程"""
        if not self.check_dataset_ready():
            print(f"Not enough samples (min {Config.MIN_SAMPLES} required)")
            return False
        
        # 清理并增强数据
        try:
            shutil.rmtree(os.path.join(Config.YOLO_DATA_DIR,"images"))
        except: pass
        try:
            shutil.rmtree(os.path.join(Config.YOLO_DATA_DIR,"labels"))
        except: pass
        
        # 数据增强
        augmenter = YOLOAugmenter(Config.YOLO_DATA_DIR, augment_factor=Config.AUGMENT_FACTOR)
        augmenter.process_dataset(Config.YOLO_DATA_DIR_REAL)

        print("Starting YOLO training...")
        trainer = YOLOTrainer()
        result = trainer.train()

        # 清理
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

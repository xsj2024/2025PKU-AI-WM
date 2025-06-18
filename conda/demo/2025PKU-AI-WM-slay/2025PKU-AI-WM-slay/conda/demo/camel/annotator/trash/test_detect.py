import cv2
import numpy as np
from model_manager import ModelManager
from overlay import Overlay
from config import Config

class DetectionTester:
    def __init__(self):
        self.model = ModelManager()
        self.overlay = Overlay(game_capture=None)  # 传入None因为我们不实际使用capture功能
        self.test_image_path = "yolo_dataset/images/1747237868.png"  # 替换为你的测试图片路径
    
    def load_test_image(self):
        """加载测试图片"""
        self.frame = cv2.imread(self.test_image_path)
        if self.frame is None:
            raise ValueError(f"无法加载图片: {self.test_image_path}")
        return self.frame.copy()
    
    def run_detection(self):
        """执行检测并显示结果"""
        # 1. 加载图片
        frame = self.load_test_image()
        
        # 2. 执行检测
        detections = self.model.detect_all(frame)
        print(f"检测到 {len(detections) if detections else 0} 个目标")
        
        # 3. 应用overlay
        overlay_input = [
            {"box": [x1, y1, x2, y2], "label": label}
            for (label, x1, y1, x2, y2) in detections
        ]
        overlay_frame = self.overlay.update_overlay(frame, overlay_input)
        
        # 4. 显示结果
        cv2.imshow("Detection Results", overlay_frame)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        
        # 5. 可选：保存结果
        # output_path = "detection_result.jpg"
        # cv2.imwrite(output_path, overlay_frame)
        # print(f"结果已保存到: {output_path}")

if __name__ == "__main__":
    tester = DetectionTester()
    tester.run_detection()

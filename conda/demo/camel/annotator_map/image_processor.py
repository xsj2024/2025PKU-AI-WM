import cv2
import numpy as np
from .config import Config

class ImageProcessor:
    @staticmethod
    def auto_pad(image: np.ndarray):
        """
        标准化返回:
        - processed: 填充后的图像
        - ratios: (w_ratio, h_ratio) 
        - pads: (top_pad, left_pad)
        """
        h, w = image.shape[:2]
        # new_w = max(32, (w + 31) // 32 * 32)  # 确保最小32像素
        # new_h = max(32, (h + 31) // 32 * 32)
        new_w,new_h = w, h
        w_ratio = new_w / w
        h_ratio = new_h / h
        
        # 计算对称填充
        pad_w = (new_w - w) / 2
        pad_h = (new_h - h) / 2
        
        processed = cv2.copyMakeBorder(
            image,
            top=int(pad_h),
            bottom=int(new_h - h - pad_h),
            left=int(pad_w),
            right=int(new_w - w - pad_w),
            borderType=cv2.BORDER_CONSTANT
        )
        return processed, (w_ratio, h_ratio), (pad_h, pad_w)
    @staticmethod
    def handle_ultra_long(image, max_ratio=3):
        """处理长宽比过大的图片（如手机截图）"""
        h, w = image.shape[:2]
        if max(h/w, w/h) > max_ratio:
            # 分段切割处理
            slices = []
            if w > h:
                step = int(w / (w//h + 1))
                for i in range(0, w, step):
                    slices.append(image[:, i:i+step])
            else:
                step = int(h / (h//w + 1))
                for i in range(0, h, step):
                    slices.append(image[i:i+step, :])
            return slices
        return [image]

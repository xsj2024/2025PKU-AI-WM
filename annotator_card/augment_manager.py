import os
import shutil
import cv2
import numpy as np
from .config import Config
from pathlib import Path
import albumentations as A

class YOLOAugmenter:
    def __init__(self, output_dir, augment_factor=5):
        """
        :param output_dir: 增强数据输出目录
        :param augment_factor: 每张图片生成的增强版本数量
        """
        self.output_dir = Path(output_dir)
        self.augment_factor = augment_factor
        
        # 创建输出目录
        (self.output_dir / "images").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "labels").mkdir(parents=True, exist_ok=True)
        
        # 定义YOLO格式兼容的增强管道
        self.transform = A.Compose([
            # # 颜色变换 (不影响bbox)
            # A.OneOf([
            #     A.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1, p=0.7),
            #     A.ChannelShuffle(p=0.3),
            # ], p=0.5),
            
            # 几何变换
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.3),
            A.RandomRotate90(p=0.5),
            
            # 模糊/噪声
            A.OneOf([
                A.GaussianBlur(blur_limit=(3, 7), p=0.5),
                A.GaussNoise(var_limit=(10, 50), p=0.5),
            ], p=0.3),
        ], bbox_params=A.BboxParams(format='yolo', min_visibility=0.4))
    
    def augment_image(self, args):
        """处理单张图片的增强"""
        img_path, label_path = args
        try:
            # 读取原始数据
            image = cv2.imread(str(img_path))
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            with open(label_path, 'r') as f:
                bboxes = [list(map(float, line.strip().split())) for line in f]
                if not bboxes:
                    return
                
            # 转换bbox格式为Albumentations需要的列表格式
            albu_bboxes = [bbox[1:] + [bbox[0]] for bbox in bboxes]  # [x,y,w,h,class_id]
            
            base_name = img_path.stem
            for i in range(self.augment_factor):
                # 执行增强
                transformed = self.transform(image=image, bboxes=albu_bboxes)
                aug_img = transformed['image']
                aug_bboxes = transformed['bboxes']
                
                # 跳过无效增强结果
                if not aug_bboxes:
                    continue
                
                # 保存增强后的图片
                aug_img_path = self.output_dir / "images" / f"{base_name}_aug{i}{img_path.suffix}"
                cv2.imwrite(str(aug_img_path), cv2.cvtColor(aug_img, cv2.COLOR_RGB2BGR))
                
                # 转换回YOLO格式并保存标签
                yolo_bboxes = []
                for bbox in aug_bboxes:
                    x, y, w, h, cls_id = bbox
                    yolo_bboxes.append(f"{int(cls_id)} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
                
                aug_label_path = self.output_dir / "labels" / f"{base_name}_aug{i}.txt"
                with open(aug_label_path, 'w') as f:
                    f.write("\n".join(yolo_bboxes))
                    
        except Exception as e:
            print(f"Error processing {img_path}: {str(e)}")

    def process_dataset(self, dataset_dir):
        """单进程版本处理"""
        dataset_dir = Path(dataset_dir)
        img_files = list((dataset_dir / "images").glob("*"))
        label_files = [dataset_dir / "labels" / f"{f.stem}.txt" for f in img_files]
        
        # 改为单进程处理
        for img_path, label_path in zip(img_files, label_files):
            self.augment_image((img_path, label_path))

# 使用示例
if __name__ == "__main__":
    augmenter = YOLOAugmenter("Test",augment_factor=50)
    augmenter.process_dataset("yolo_dataset/real")  # 替换为你的数据集路径

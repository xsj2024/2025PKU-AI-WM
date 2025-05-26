import os
import random
import cv2
import numpy as np
import json
from PIL import Image
from tqdm import tqdm

def create_composite_images(images_list, output_dir, num_composite=3, max_composite_size=(1300, 1229)):
    """
    创建包含随机排列遗物图片的合成大图，并生成YOLOv8格式标注
    
    参数:
        images_list: 遗物图片路径列表
        output_dir: 输出目录
        num_composite: 要生成的合成图数量
        max_composite_size: 合成图的最大尺寸(宽,高)
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. 创建遗物名称与固定ID的映射 (按初始文件名排序确保一致性)
    relic_info = sorted([
        (os.path.splitext(os.path.basename(p))[0], p) 
        for p in images_list
    ], key=lambda x: x[0])
    
    # 生成Python列表格式的遗物名称列表 (单行输出)
    relic_names = [name for name, _ in relic_info]
    with open(os.path.join(output_dir, 'relic_names.txt'), 'w', encoding='utf-8') as f:
        f.write(json.dumps(relic_names))  # 使用json保持Python列表格式
    
    # 创建ID到图片路径的映射 (固定ID: 0,1,2,...)
    id_to_imgpath = {idx: path for idx, (_, path) in enumerate(relic_info)}
    
    # 进度条: 生成指定数量的合成图
    for composite_idx in tqdm(range(1, num_composite + 1), desc="生成合成图"):
        # 2. 随机打乱ID顺序 (但不改变ID与图片的绑定)
        shuffled_ids = list(id_to_imgpath.keys())
        random.shuffle(shuffled_ids)
        
        # 初始化合成图和标注数据
        composite_img = np.zeros((max_composite_size[1], max_composite_size[0], 3), dtype=np.uint8)
        yolo_labels = []
        
        # 设置初始摆放位置
        x_offset, y_offset = 20, 20
        max_row_height = 0
        
        # 按照打乱后的ID顺序处理图片
        for relic_id in shuffled_ids:
            img_path = id_to_imgpath[relic_id]
            
            try:
                # 读取图片
                img = cv2.imread(img_path)
                if img is None:
                    raise ValueError(f"无法读取图片: {img_path}")
                
                h, w = img.shape[:2]
                
                # 检查是否有足够空间放置当前图片
                if x_offset + w > max_composite_size[0]:  # 换行
                    x_offset = 20
                    y_offset += max_row_height + 20
                    max_row_height = 0
                
                if y_offset + h > max_composite_size[1]:  # 超出最大高度
                    print(f"合成图 {composite_idx} 空间不足，已放置 {len(yolo_labels)} 个遗物")
                    break
                
                # 放置图片到合成图
                composite_img[y_offset:y_offset+h, x_offset:x_offset+w] = img
                
                # 计算YOLO格式标注(保持原始relic_id不变)
                x_center = (x_offset + w/2) / max_composite_size[0]
                y_center = (y_offset + h/2) / max_composite_size[1]
                width = w / max_composite_size[0]
                height = h / max_composite_size[1]
                
                yolo_labels.append(f"{relic_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
                
                # 更新偏移量
                x_offset += w + 20
                max_row_height = max(max_row_height, h)
                
            except Exception as e:
                print(f"处理 {img_path} 时出错: {str(e)}")
                continue
        
        # 裁剪多余空白
        composite_img = composite_img[:y_offset + max_row_height + 20, :max_composite_size[0]]
        
        # 保存合成图和标注
        composite_path = os.path.join(output_dir, f'composite_{composite_idx}.jpg')
        cv2.imwrite(composite_path, composite_img)
        
        label_path = os.path.join(output_dir, f'composite_{composite_idx}.txt')
        with open(label_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(sorted(yolo_labels, key=lambda x: int(x.split()[0]))))  # 按ID排序标注

# 使用示例
if __name__ == "__main__":
    # 1. 获取所有遗物图片路径
    relic_images_dir = "relic_images_v2"
    image_paths = [
        os.path.join(relic_images_dir, f) 
        for f in sorted(os.listdir(relic_images_dir))  # 按文件名排序确保ID一致性
        if f.lower().endswith(('.png', '.jpg', '.jpeg'))
    ]
    
    # 2. 创建输出目录
    output_dir = "composite_relics_output_advanced"
    create_composite_images(image_paths, output_dir, num_composite=3)

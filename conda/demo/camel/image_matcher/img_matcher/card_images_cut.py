import os
import cv2

# 输入和输出目录
input_dir = "images/card_images_whole"
output_dir = "images/card_images"

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 遍历输入目录中的所有文件
for filename in os.listdir(input_dir):
    # 检查是否为图片文件（扩展名为 jpg, png 等）
    if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp')):
        # 读取图片
        img_path = os.path.join(input_dir, filename)
        img = cv2.imread(img_path)
        
        if img is not None:
            # 计算裁剪高度，保留上半部分 60%
            h, w = img.shape[:2]
            cropped_img = img[int(h*0.17):int(h * 0.532), int(w*0.15):int(w*0.85)]  # 裁剪上半部分

            # 保存到输出目录，相同文件名
            output_path = os.path.join(output_dir, filename)
            cv2.imwrite(output_path, cropped_img)
            print(f"已处理: {filename} -> {output_path}")
        else:
            print(f"⚠ 读取失败: {filename}")
    else:
        print(f"⚠ 跳过非图片文件: {filename}")

print("✅ 所有图片处理完成！")

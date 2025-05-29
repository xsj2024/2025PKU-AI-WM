from PIL import Image, ImageDraw
import os
# 选择一张图像和对应的标签
img_path = "yolo_dataset/images/1747237868.png"
label_path = "yolo_dataset/labels/1747237868.txt"
img = Image.open(img_path)
draw = ImageDraw.Draw(img)
w, h = img.size
with open(label_path, "r") as f:
    for line in f.readlines():
        cls, x, y, w_norm, h_norm = map(float, line.split())
        # 转换归一化坐标→像素坐标
        x1 = (x - w_norm/2) * w
        y1 = (y - h_norm/2) * h
        x2 = (x + w_norm/2) * w
        y2 = (y + h_norm/2) * h
        draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
img.show()  # 确认标注框是否正确框住目标
import torch
from paddleocr import PaddleOCR
import time

# 初始化模型（默认启用中英文识别）
ocr = PaddleOCR(
    lang="en",                # 识别语言，如：'ch', 'en', 'fr'
    use_angle_cls=False,      # 禁用文字方向检测（对横排文本可以关闭）
    # det_db_score_mode="fast", # 使用快速 DB 检测（PaddleOCR > 2.4）
    enable_mkldnn=True,       # 启用 Intel MKL-DNN 加速（仅 Intel CPU 有效）
    use_tensorrt=True,       # 如有 NVIDIA GPU，可以启用 TensorRT（但要配置 CUDA）
    use_gpu=True,             # 使用 GPU（需安装 CUDA + cudnn + paddle-gpu）
    # 以下是精度-速度权衡选项：
    det_db_box_thresh=0.5,    # 检测框阈值（0-1，越高越少框）
    rec_algorithm='SVTR_LCNet',     # 换更快的识别算法（如 'SVTR_LCNet'）
    drop_score=0.5,           # 低于该分数的识别结果将被丢弃
)

def extract_ocr_text(result):
    texts = []
    for item in result:
        if isinstance(item, list):
            texts.extend(extract_ocr_text(item))
        # 如果当前元素是包含文字信息的元组（文本，置信度）
        elif isinstance(item, tuple) and len(item) >= 2:
            if isinstance(item[0], str):  # 确保第一个元素是文本
                texts.append(item[0])
        elif isinstance(item, list) and len(item) >= 2:
            if isinstance(item[1], tuple):
                texts.append(item[1][0])
    return texts

# OCR识别

bb = time.time()
result = ocr.ocr('Test/tttt.png', cls=True)
print(time.time()-bb)

# 提取并打印所有文本
all_texts = extract_ocr_text(result)
for text in all_texts:
    print(text)
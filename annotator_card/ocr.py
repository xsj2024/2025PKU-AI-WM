import os
import cv2
import numpy as np
from .config import Config
from paddleocr import PaddleOCR
import logging

# 初始化模型（默认启用中英文识别）
ocr_model = PaddleOCR(
    lang="en",                # 识别语言，如：'ch', 'en', 'fr'
    use_angle_cls=False,      # 禁用文字方向检测（对横排文本可以关闭）
    det_db_score_mode="fast", # 使用快速 DB 检测（PaddleOCR > 2.4）
    enable_mkldnn=True,       # 启用 Intel MKL-DNN 加速（仅 Intel CPU 有效）
    use_tensorrt=False,       # 如有 NVIDIA GPU，可以启用 TensorRT（但要配置 CUDA）
    use_gpu=True,             # 使用 GPU（需安装 CUDA + cudnn + paddle-gpu）
    # 以下是精度-速度权衡选项：
    det_db_box_thresh=0.6,    # 检测框阈值（0-1，越高越少框）
    rec_algorithm='CRNN',     # 换更快的识别算法（如 'SVTR_LCNet'）
    drop_score=0.5,           # 低于该分数的识别结果将被丢弃
)
logging.disable(logging.DEBUG)

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

def get_text(img):
    return extract_ocr_text(ocr_model.ocr(img, cls=True))
def extract_text_from_boxes(image, boxes):
    """
    从图片的指定检测框中提取文字
    :param image: 图片路径或 numpy 数组 (H, W, C)
    :param boxes: 检测框列表，格式 [[x1,y1,x2,y2], ...]
    :param ocr_model: 可选，预加载的 PaddleOCR 模型（避免重复初始化）
    :param lang: OCR 语言（默认中文 'ch'）
    :return: list[str] 每个框的文字识别结果
    """
    assert False
    # 1. 初始化OCR模型（如果未提供）
    
    # 2. 读取图片（如果是路径则用 OpenCV 加载）
    if isinstance(image, str):
        img = cv2.imread(image)
    else:
        img = image.copy()  # 避免修改原图
    
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # PaddleOCR 需要 RGB
    
    # 3. 遍历每个检测框（按顺序）
    results = []
    for box in boxes:
        x1, y1, x2, y2 = box
        
        # 确保坐标有效（防止越界）
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(img.shape[1], x2), min(img.shape[0], y2)
        
        # 提取ROI（框内区域）
        roi = img[y1:y2, x1:x2]
        
        # 4. 执行OCR识别（只进行 `rec` 文本识别）
        # print(get_text(roi),">>>")
        results.append(get_text(roi))
        # ocr_result = ocr_model.ocr(roi, det=False, cls=False)
        
        # # 提取文本框识别结果（合并多行文本）
        # if ocr_result and len(ocr_result) > 0:
        #     text = "\n".join([line[0] for line in ocr_result])
        #     results.append(text)
        # else:
        #     results.append("")  # 未检测到文本
    
    return results
if __name__ == '__main__':
    img = cv2.imread('Test/test.png')
    # OCR识别
    result = ocr_model.ocr(img, cls=True)

    # # 提取并打印所有文本
    all_texts = extract_ocr_text(result)
    for text in all_texts:
        print(text)
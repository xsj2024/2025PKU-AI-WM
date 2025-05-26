import numpy as np
import cv2
from ..image_processor import ImageProcessor
from ..config import Config
def test_various_sizes():
    test_sizes = [(1920, 1080), (720, 1280), (500, 500), (300, 1000)]
    dummy_img = np.zeros((100, 100, 3), dtype=np.uint8)  # 用随机生成代替实际图片
    
    for w, h in test_sizes:
        img = cv2.resize(dummy_img, (w, h))
        processed, _ = ImageProcessor.auto_pad(img)
        assert processed.shape == (Config.IMAGE_SIZE, Config.IMAGE_SIZE, 3)
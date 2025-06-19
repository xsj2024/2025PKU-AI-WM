import cv2
import numpy as np
from cnocr import CnOcr

predictor = CnOcr(det_model_name='ch_PP-OCRv3_det', rec_model_name='en_PP-OCRv4')
def ascii_ocr(image: 'np.ndarray', repeat: int = 1) -> str:
    # 只用原图识别，repeat=1，保留接口
    if image is None:
        raise ValueError("Input image is None. Please check the image path or file.")
    result = list(predictor.ocr(image))
    texts = [item['text'] for item in result if 'text' in item]
    print("ocr_result:", ' '.join(texts))
    return ' '.join(texts)

if __name__ == '__main__':
    import time
    image_path = 'text_reader//QQ_1749827308083.png'
    img = cv2.imread(image_path)
    
    if img is None:
        print(f"Failed to load image: {image_path}. Please check the file path.")
    else:
        N = 1
        start = time.time()
        for _ in range(N):
            text = ascii_ocr(img)
        end = time.time()
        print("识别结果：")
        print(text)
        print(f"Run {N} times, total time: {end - start:.3f}s, average: {(end - start)/N:.4f}s")
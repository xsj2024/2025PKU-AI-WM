import cv2
import string
import numpy as np
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=True, lang='en')

def ascii_ocr(image: np.ndarray) -> str:
    if image is None:
        raise ValueError("Input image is None. Please check the image path or file.")
    min_size = 300
    h, w = image.shape[:2]
    scale = max(min_size / h, min_size / w, 1)
    if scale > 1:
        image = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    img_rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    result = ocr.ocr(img_rgb)
    text = ''
    for line in result:
        if line is None or len(line) == 0:
            continue
        for box in line:
            txt = box[1][0]
            txt = ''.join([c for c in txt if c in string.printable and (c.isalnum() or c in '+-*/=.,:;!?()[]{}<>|\\@#$%^&*_~`\'\"')])
            if txt:
                text += txt + '\n'
    return text.strip()

if __name__ == '__main__':
    import time
    img = cv2.imread('text_reader//QQ_1748095382049.png')
    if img is None:
        print("Failed to load image: test.png. Please check the file path.")
    else:
        N = 10
        start = time.time()
        for _ in range(N):
            text = ascii_ocr(img)
        end = time.time()
        print(text)
        print(f"Run {N} times, total time: {end - start:.3f}s, average: {(end - start)/N:.4f}s")
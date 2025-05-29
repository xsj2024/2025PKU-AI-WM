import cv2
import string
import numpy as np
import easyocr

reader = easyocr.Reader(['en'], gpu=True)
def ascii_ocr(image: np.ndarray) -> str:
    if image is None:
        raise ValueError("Input image is None. Please check the image path or file.")
    # 图像预处理：放大
    upscale_factor = 5
    image = cv2.resize(image, (image.shape[1]*upscale_factor, image.shape[0]*upscale_factor), interpolation=cv2.INTER_CUBIC)
    # easyocr 需要RGB格式
    img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = reader.readtext(img_rgb, detail=1, decoder='beamsearch')
    # results: [(bbox, text, conf), ...]
    # 按 top(y) 坐标、再按 left(x) 坐标排序
    def get_box_pos(r):
        box = r[0]
        # 取左上角点的 y, x
        y = min(box[0][1], box[1][1], box[2][1], box[3][1])
        x = min(box[0][0], box[1][0], box[2][0], box[3][0])
        return (round(y//10), x)  # y 取整分组，避免微小抖动
    results_sorted = sorted(results, key=get_box_pos)
    text = ''
    for r in results_sorted:
        txt = r[1]
        if txt:
            text += txt + '\n'
    if not text:
        text = '[No text detected]'
    return text.strip()

if __name__ == '__main__':
    import time
    img = cv2.imread('text_reader//QQ_1748485534844.png')
    if img is None:
        print("Failed to load image: test.png. Please check the file path.")
    else:
        N = 1
        start = time.time()
        for _ in range(N):
            text = ascii_ocr(img)
        end = time.time()
        print(text)
        print(f"Run {N} times, total time: {end - start:.3f}s, average: {(end - start)/N:.4f}s")
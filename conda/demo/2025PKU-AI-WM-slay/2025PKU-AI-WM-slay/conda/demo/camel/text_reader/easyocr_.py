import cv2
import numpy as np
import easyocr
import functools
import time

reader = easyocr.Reader(['en'], gpu=False)
COLORS = [(99,248,99), (75,75,255), (255,255,255)]
def keep_similar_colors_white(image: np.ndarray, COLORS=COLORS, thresh=30) -> np.ndarray:
    """只保留与COLORS中颜色相近的像素为白色，其余为黑色"""
    img = image.copy()
    mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for color in COLORS:
        diff = np.linalg.norm(img.astype(np.int16) - np.array(color, dtype=np.int16), axis=2)
        mask = cv2.bitwise_or(mask, (diff < thresh).astype(np.uint8) * 255)
    result = np.zeros_like(img)
    result[mask == 255] = (255, 255, 255)
    return result
def keep_white_only(image: 'np.ndarray', min_area: int = 10) -> 'np.ndarray':
    """只保留连通块较大的白色区域，并裁剪到最小外接矩形"""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
    # 连通域分析
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    new_mask = np.zeros_like(mask)
    for i in range(1, num_labels):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            new_mask[labels == i] = 255
    # 找所有白色像素的最小外接矩形
    coords = cv2.findNonZero(new_mask)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        
        # 裁剪原图和mask
        cropped_img = image[y:y+h, x:x+w]
        cropped_mask = new_mask[y:y+h, x:x+w]
        # 只保留白色区域
        result = np.zeros_like(cropped_img)
        for c in range(3):
            result[:,:,c] = cv2.bitwise_and(cropped_img[:,:,c], cropped_mask)
        return result
    else:
        return image
def add_black_border(image: 'np.ndarray', border: int = 1) -> 'np.ndarray':
    """在图像四周扩充指定像素的黑色边框"""
    return cv2.copyMakeBorder(image, border, border, border, border, cv2.BORDER_CONSTANT, value=(0,0,0))
def ascii_ocr(image: np.ndarray) -> str:
    if image is None:
        raise ValueError("Input image is None. Please check the image path or file.")
    # 图像预处理：放大
    upscale_factor = 2
    image = keep_similar_colors_white(image)
    cv2.imwrite("SBSBSB.png",image)
    image = keep_white_only(image)
    image = add_black_border(image, border=1)
    cv2.imwrite("SBSBSB1.png",image)
    image = cv2.resize(image, (image.shape[1]*upscale_factor, image.shape[0]*upscale_factor), interpolation=cv2.INTER_CUBIC)
    results = reader.recognize(image, detail=0, batch_size=1, paragraph=True)
    # results: [(bbox, text, conf), ...]
    # print(results)
    text = ''.join(results)
    if not text:
        text = '[No text detected]'
    return text.strip()

if __name__ == '__main__':
    import threading
    img = cv2.imread('text_reader//SBSBSB1.png')
    if img is None:
        print("Failed to load image: test.png. Please check the file path.")
    else:
        N = 10
        # 单线程测试
        t1 = time.time()
        for _ in range(N):
            _ = ascii_ocr(img)
            print(_)
        t2 = time.time()
        print(f"[Single thread] Total time: {t2-t1:.4f}s, Avg: {(t2-t1)/N:.4f}s")

        # 多线程测试
        times = [0] * N
        def worker(idx):
            start = time.time()
            _ = ascii_ocr(img)
            end = time.time()
            times[idx] = end - start
        threads = []
        for i in range(N):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
        t3 = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        t4 = time.time()
        print(f"[Multi-thread] Each thread time: {times}")
        print(f"[Multi-thread] Total time: {t4-t3:.4f}s, Max: {max(times):.4f}s, Min: {min(times):.4f}s, Avg: {sum(times)/N:.4f}s")
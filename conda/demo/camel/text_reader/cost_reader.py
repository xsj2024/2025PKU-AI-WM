import cv2
import numpy as np
from cnocr import CnOcr

predictor = CnOcr(det_model_name='ch_PP-OCRv3_det', rec_model_name='en_PP-OCRv4')
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
def ascii_ocr(image: 'np.ndarray', repeat: int = 1) -> str:
    # 只用原图识别，repeat=1，保留接口
    if image is None:
        raise ValueError("Input image is None. Please check the image path or file.")
    upscale_factor = 2
    image = keep_white_only(image)
    image = add_black_border(image, border=1)
    cv2.imwrite("SBSBSB.png",image)
    image = cv2.resize(image, (image.shape[1]*upscale_factor, image.shape[0]*upscale_factor), interpolation=cv2.INTER_CUBIC)
    image = image[10:-10,10:-10]
    result = list(predictor.ocr(image))
    texts = [item['text'] for item in result if 'text' in item]
    print("ocr_result:", ' '.join(texts))
    return ' '.join(texts)

if __name__ == '__main__':
    import time
    image_path = 'text_reader//SBSBSB1.png'
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
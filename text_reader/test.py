import cv2
from paddleocr import PaddleOCR

# 初始化 PaddleOCR
ocr = PaddleOCR(lang='en')

# 读取图片
image_path = '19b0dc81-cddb-4864-816c-66e540ab32aa.png'
img = cv2.imread(image_path)
if img is None:
    print(f"Failed to load image: {image_path}")
else:
    # 识别图片（新版API）
    N = 100
    import time
    b = time.time()
    for i in range(N):
        result = ocr.predict(image_path)
    print((time.time()-b)/N)
    # 打印识别结果
    print("识别结果：")
    for idx, text in enumerate(result[0]['rec_texts']):
        print(f"第 {idx+1} 行: {text}")


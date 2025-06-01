import cv2
from paddleocr import PaddleOCR

ocr = PaddleOCR(use_angle_cls=False, lang='en')
def ascii_ocr(image_path: str) -> str:
    result = ocr.predict(image_path)
    if not result or 'rec_texts' not in result[0]:
        return '[No text detected]'
    return ' '.join(result[0]['rec_texts'])

if __name__ == '__main__':
    import time
    image_path = 'sbsbsb.png'
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load image: {image_path}. Please check the file path.")
    else:
        N = 100
        start = time.time()
        for _ in range(N):
            text = ascii_ocr(image_path)
        end = time.time()
        print("识别结果：")
        print(text)
        print(f"Run {N} times, total time: {end - start:.3f}s, average: {(end - start)/N:.4f}s")
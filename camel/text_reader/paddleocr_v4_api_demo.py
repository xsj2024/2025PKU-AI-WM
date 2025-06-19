import cv2
from cnocr import CnOcr

predictor = CnOcr(det_model_name='ch_PP-OCRv3_det', rec_model_name='en_PP-OCRv4')
def ascii_ocr(image_path: str) -> str:
    # 使用 paddlex.deploy.create_predictor 加载模型
    # 读取图片并推理
    img = cv2.imread(image_path)
    # paddlex predictor 返回的是生成器，需要转为list
    result = list(predictor.ocr(img))
    # print(f"识别结果: {result}")
    # result 是一个list，每个元素是dict，包含 rec_texts
    print(result)

    return ' '

if __name__ == '__main__':
    import time
    image_path = 'text_reader//QQ_1749823314727.png'
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load image: {image_path}. Please check the file path.")
    else:
        N = 1
        start = time.time()
        for _ in range(N):
            text = ascii_ocr(image_path)
        end = time.time()
        print("识别结果：")
        print(text)
        print(f"Run {N} times, total time: {end - start:.3f}s, average: {(end - start)/N:.4f}s")
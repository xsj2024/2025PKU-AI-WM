import cv2
from paddleocr import PaddleOCR
import paddle
predictor = PaddleOCR(lang='en')
def ascii_ocr(image_path: str) -> str:
    # 使用 paddlex.deploy.create_predictor 加载模型
    # 读取图片并推理
    img = cv2.imread(image_path)
    # paddlex predictor 返回的是生成器，需要转为list
    result = list(predictor.predict(img))
    # print(f"识别结果: {result}")
    # result 是一个list，每个元素是dict，包含 rec_texts
    if not result or not isinstance(result[0], dict) or 'rec_texts' not in result[0]:
        return '[No text detected]'
    return ' '.join(result[0]['rec_texts'])

if __name__ == '__main__':
    save_path = 'onnx.save/lenet' # 需要保存的路径
    x_spec = paddle.static.InputSpec([None, 1, 28, 28], 'float32', 'x') # 为模型指定输入的形状和数据类型，支持持 Tensor 或 InputSpec ，InputSpec 支持动态的 shape。
    paddle.onnx.export(predictor, save_path, input_spec=[x_spec], opset_version=11)
    import time
    image_path = 'text_reader//sbsbsb.png'
    img = cv2.imread(image_path)
    if img is None:
        print(f"Failed to load image: {image_path}. Please check the file path.")
    else:
        N = 10
        start = time.time()
        for _ in range(N):
            text = ascii_ocr(image_path)
        end = time.time()
        print("识别结果：")
        print(text)
        print(f"Run {N} times, total time: {end - start:.3f}s, average: {(end - start)/N:.4f}s")
paddle2onnx --model_dir C:/Users/admin/.paddlex/official_models/PP-OCRv5_mobile_rec  --model_filename inference.json  --params_filename inference.pdiparams  --save_file model.onnx

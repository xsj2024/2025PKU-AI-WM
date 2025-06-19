import cv2
import numpy as np
import onnxruntime as ort

# 1. 加载 ONNX 模型（假设模型文件名为 ppoocrv3_rec.onnx）
# 你需要下载官方 PP-OCRv3 的识别模型 ONNX 文件，并放在同目录下
rec_model_path = 'ppoocrv3_rec.onnx'  # 修改为你的模型路径
session = ort.InferenceSession(rec_model_path, providers=['CPUExecutionProvider'])

# 2. 字典文件（官方提供的 dict.txt，需与模型配套）
def load_dict(dict_path='en_dict.txt'):
    with open(dict_path, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f]
char_list = load_dict()  # 字符表

# 3. 图像预处理（以英文为例，PP-OCRv3 输入为 1x3x48x320）
def preprocess(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.resize(img, (320, 48))
    img = img.astype(np.float32) / 255.0
    img = (img - 0.5) / 0.5  # 归一化
    img = np.transpose(img, (2, 0, 1))  # HWC->CHW
    img = np.expand_dims(img, axis=0)  # batch
    return img

# 4. CTC 解码
def ctc_decode(preds, char_list):
    text = ''
    last_idx = -1
    for idx in preds:
        if idx != 0 and idx != last_idx:
            text += char_list[idx-1]
        last_idx = idx
    return text

# 5. 推理函数
def ppoocrv3_onnx_ocr(img):
    input_img = preprocess(img)
    ort_inputs = {session.get_inputs()[0].name: input_img}
    preds = session.run(None, ort_inputs)[0]  # shape: [1, seq_len, num_classes]
    preds_idx = np.argmax(preds, axis=2)[0]
    text = ctc_decode(preds_idx, char_list)
    return text

if __name__ == '__main__':
    img = cv2.imread('text_reader/sbsb(1).png')
    if img is None:
        print('Failed to load image!')
    else:
        text = ppoocrv3_onnx_ocr(img)
        print('识别结果:')
        print(text)

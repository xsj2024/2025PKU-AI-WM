# 识别单张图片

import cnocr

ocr = cnocr.CnOcr(det_model_name='db_resnet18', rec_model_name='densenet_lite_136-gru')
image_path = 'text_reader//QQ_1748484812659.png'
result = ocr.ocr(image_path)

# 打印识别结果
print("识别结果：")
for idx, line in enumerate(result):
    print(f"第 {idx+1} 行: {line['text']}")

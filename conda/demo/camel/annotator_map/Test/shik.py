import pytesseract
from PIL import Image

# 安装 tesseract 和 pytesseract 包，假设已经安装好

# 打开要识别的图片
image = Image.open('Test/dgagd.png')
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# 编码格式选择为 utf-8，即英文等编码方式
# 命令行方式使用 --psm 6 表示 "Assume a single uniform block of text."，以识别单行文本
config='-l eng --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+'
text = pytesseract.image_to_string(image, lang='eng', config=config)

print(text)

# 如果你的图片只包含英文字母和数字，但有干扰，你可以通过这种配置进一步优化识别效果：

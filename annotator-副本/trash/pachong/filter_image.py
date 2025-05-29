import os
from PIL import Image
def clean_small_images(folder_path, min_width=30, min_height=30):
    for filename in os.listdir(folder_path):
        filepath = os.path.join(folder_path, filename)
        try:
            o = 0
            with Image.open(filepath) as img:
                if img.width < min_width or img.height < min_height:
                    o = 1
            if o == 1:
                os.remove(filepath)
                print(f"🗑️ 删除小图片: {filename} ({img.width}x{img.height})")
        except Exception as e:
            print(f"⚠️ 处理失败 {filename}: {e}")
# 使用方法
clean_small_images("relic_images_v2")
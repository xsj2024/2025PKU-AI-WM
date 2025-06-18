import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import platform
import os

class AdvancedChineseRenderer:
    def __init__(self):
        self.font_cache = {}
        
    def get_proper_font(self, size):
        """获取完美支持中文的字体"""
        system = platform.system()
        
        # 专业级字体查找优先级
        font_paths = [
            # Windows
            "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
            "C:/Windows/Fonts/simhei.ttf",  # 黑体
            
            # macOS
            "/System/Library/Fonts/PingFang.ttc",
            "/System/Library/Fonts/STHeiti Medium.ttc",
            
            # Linux
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
            "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
            
            # 备用方案
            os.path.join(os.path.dirname(__file__), "fonts/NotoSansCJK.ttc")
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size, encoding="utf-8")
                except:
                    continue
        
        raise FileNotFoundError("未找到可用的中文字体")

    def draw_chinese(self, img, text, pos, color=(0, 255, 0), size=30):
        """完美解决文字显示不全的专业方法"""
        try:
            # 输入验证
            if img is None:
                raise ValueError("输入图像无效")
            
            # 自动处理不同格式的输入图像
            img_array = img if isinstance(img, np.ndarray) else np.array(img)
            if img_array.ndim == 2:
                pil_mode = "L"
                img_pil = Image.fromarray(img_array, mode=pil_mode).convert("RGB")
            elif img_array.ndim == 3:
                img_pil = Image.fromarray(cv2.cvtColor(img_array, cv2.COLOR_BGR2RGB))
            else:
                raise ValueError("不支持的图像格式")

            # 获取专业配置的字体
            font = self.get_proper_font(size)
            
            # 创建临时绘图对象计算精确位置
            temp_draw = ImageDraw.Draw(img_pil)
            text_bbox = temp_draw.textbbox((0, 0), text, font=font)
            
            # 核心修复：计算真实字体的视觉中线位置
            text_height = text_bbox[3] - text_bbox[1]
            baseline_offset = int(text_height * 0.15)  # 专业视觉调整参数
            
            # 创建透明层实现完美文字叠加
            text_layer = Image.new("RGBA", img_pil.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(text_layer)
            
            # 使用精确的字体定位
            draw.text(
                xy=(pos[0], pos[1] - baseline_offset),
                text=text,
                font=font,
                fill=(*color, 255),
                stroke_width=0,
                anchor="lt"  # left-top定位基准
            )
            
            # 专业图像合成
            result = Image.alpha_composite(
                img_pil.convert("RGBA"),
                text_layer
            ).convert("RGB")
            
            return cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
            
        except Exception as e:
            print(f"[专业级错误处理] 绘图异常: {str(e)}")
            # 应急显示方案
            cv2.putText(img, text, (pos[0], pos[1]+size), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            return img

# 使用示例
if __name__ == "__main__":
    renderer = AdvancedChineseRenderer()
    
    # 创建专业测试图
    img = np.zeros((400, 600, 3), dtype=np.uint8) + 255
    
    # 测试复杂中文排版
    test_cases = [
        ("常规显示", (50, 50), (255, 0, 0), 30),
        ("显示下半部分", (50, 120), (0, 150, 0), 40),
        ("专业排版效果", (50, 200), (0, 0, 200), 50),
        ("底部测试：中文、English、かな", (50, 300), (0, 0, 0), 35),
    ]
    
    for text, pos, color, size in test_cases:
        img = renderer.draw_chinese(img, text, pos)
    
    cv2.imwrite("professional_output.jpg", img)
    cv2.imshow("Professional Chinese Rendering", img)
    cv2.waitKey(0)

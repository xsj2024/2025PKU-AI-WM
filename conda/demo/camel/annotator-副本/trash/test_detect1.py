import cv2
import numpy as np
from model_manager import ModelManager
from datetime import datetime

def debug_detection(image_path="test.jpg", save_result=True):
    """增强版目标检测可视化工具
    
    Args:
        image_path (str): 输入图像路径
        save_result (bool): 是否自动保存可视化结果
    """
    # 1. 模型初始化（带错误处理）
    print("🔄 初始化模型...")
    try:
        model = ModelManager(model_path="./models/yolov8n.pt")
        if not hasattr(model, 'model'):
            raise RuntimeError("模型加载失败")
    except Exception as e:
        print(f"❌ 模型初始化错误: {str(e)}")
        return

    # 2. 图像加载（支持中文路径）
    print(f"\n🖼️ 加载测试图像: {image_path}")
    try:
        # 兼容中文路径和特殊字符
        img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("图像解码失败")
        h, w = img.shape[:2]
    except Exception as e:
        print(f"❌ 图像加载错误: {str(e)}")
        return

    # 3. 执行检测
    print("\n⚙️ 执行检测中...", end=' ')
    try:
        results = model.model.predict(img, verbose=False)
        print("✅ 完成")
    except Exception as e:
        print(f"❌ 检测失败: {str(e)}")
        return

    # 4. 结果解析
    if len(results[0].boxes) == 0:
        print("\n❌ 未检测到有效目标")
        return
    
    # 5. 增强可视化（替代原生plot方法）
    debug_img = img.copy()
    
    # 获取检测数据（兼容CUDA/CPU）
    boxes = results[0].boxes.xyxy.cpu().numpy()
    confs = results[0].boxes.conf.cpu().numpy()
    cls_ids = results[0].boxes.cls.cpu().numpy().astype(int)
    
    # 自定义颜色映射
    color_map = {
        0: (0, 255, 0),   # 人-绿色
        2: (255, 0, 0),   # 车-蓝色
        3: (0, 165, 255)  # 摩托车-橙色
    }
    
    for box, conf, cls_id in zip(boxes, confs, cls_ids):
        # 坐标安全转换（防止越界）
        x1, y1, x2, y2 = map(int, [
            max(0, box[0]),
            max(0, box[1]),
            min(w-1, box[2]),
            min(h-1, box[3])
        ])
        
        # 获取类别颜色（默认红色）
        color = color_map.get(cls_id, (0, 0, 255))
        
        # 绘制检测框（带优化厚度）
        cv2.rectangle(
            debug_img, 
            (x1, y1), (x2, y2),
            color, 2, cv2.LINE_AA
        )
        
        # 构建标签文本
        label = f"{results[0].names[cls_id]} {conf:.2f}"
        
        # 计算文本尺寸
        (text_w, text_h), _ = cv2.getTextSize(
            label, cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 1
        )
        
        # 绘制标签背景
        cv2.rectangle(
            debug_img,
            (x1, max(0, y1 - text_h - 5)),
            (x1 + text_w, y1),
            color, -1, cv2.LINE_AA
        )
        
        # 绘制标签文本
        cv2.putText(
            debug_img, label,
            (x1, max(text_h, y1 - 3)),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
            (255, 255, 255), 1, cv2.LINE_AA
        )

    # 6. 显示结果（自适应窗口）
    cv2.namedWindow("Detection Results", cv2.WINDOW_NORMAL)
    scale = min(1.0, 1280/w, 720/h)  # 保持宽高比
    cv2.resizeWindow("Detection Results", int(w*scale), int(h*scale))
    cv2.imshow("Detection Results", debug_img)
    
    # 7. 可选保存结果
    if save_result:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"detection_result_{timestamp}.jpg"
        cv2.imwrite(output_path, debug_img)
        print(f"\n💾 结果已保存至: {output_path}")

    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    debug_detection("yolo_dataset/images111/1747266536.png")

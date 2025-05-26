import cv2
import os
import numpy as np

class IconMatcher:
    def __init__(self, icon_dir: str = "relic_images/"):
        self.icon_db = {}
        # ORB参数调整：更多特征点用于小图标
        self.orb = cv2.ORB_create(
            nfeatures=200,  # 增加特征点数量
            scaleFactor=1.2,
            edgeThreshold=7,
            patchSize=20,
            fastThreshold=10,
            WTA_K=2
        )
        self.min_features = 90  # 特征点最小数量阈值
        self._load_icons(icon_dir)
    
    def _load_icons(self, icon_dir: str) -> None:
        """加载图标并提取特征，确保每个图标有足够特征点"""
        if not os.path.exists(icon_dir):
            raise FileNotFoundError(f"图标目录不存在: {icon_dir}")
        
        for img_file in os.listdir(icon_dir):
            if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(icon_dir, img_file)
                img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                
                if img is not None:
                    # 统一调整为60x60大小
                    img = cv2.resize(img, (60, 60))
                    
                    # 使用图像增强提高特征点数量
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    enhanced_img = clahe.apply(img)
                    
                    # 保证特征点足够多，最多尝试3次
                    for _ in range(3):
                        kp, des = self.orb.detectAndCompute(enhanced_img, None)
                        
                        # 特征点达到最小值且描述符有效
                        if des is not None and len(des) >= self.min_features:
                            self.icon_db[img_file] = des
                            # print(f"成功加载: {img_file} - 特征点: {len(des)}")
                            break
                        
                        # 如果不够，调整ORB参数重试
                        self.orb.setFastThreshold(max(5, self.orb.getFastThreshold() - 2))
                    else:
                        print(f"警告: 图标 {img_file} 特征点不足({len(kp) if 'kp' in locals() else 0})，已跳过")
                else:
                    print(f"警告: 无法读取图标 {img_file}")

    def match(self, query_img: np.ndarray, min_matches: int = 15) -> str:
        """
        匹配查询图像
        Args:
            query_img: 查询图像(BGR或灰度)
            min_matches: 需要的最小匹配数(默认15)
        Returns:
            匹配的图标文件名或"unknown"
        """
        # 预处理查询图像
        if len(query_img.shape) == 3:
            gray = cv2.cvtColor(query_img, cv2.COLOR_BGR2GRAY)
        else:
            gray = query_img
        
        gray = cv2.resize(gray, (60, 60))
        enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(gray)
        
        # 提取特征
        kp1, des1 = self.orb.detectAndCompute(enhanced, None)
        if des1 is None or len(des1) < 10:  # 查询图像至少需要10个特征点
            return "unknown"
        
        # 匹配数据库
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        best_match = "unknown"
        best_matches = 0
        
        for name, des2 in self.icon_db.items():
            if des2 is None or len(des2) < self.min_features:
                continue
            
            matches = bf.knnMatch(des1, des2, k=2)
            
            # 比率测试
            good = []
            try:
                for m, n in matches:
                    if m.distance < 0.75 * n.distance:
                        good.append(m)
            except ValueError:
                continue
            
            # 更新最佳匹配
            if len(good) > best_matches:
                best_matches = len(good)
                best_match = name
            
        print(best_matches)
        return best_match if best_matches >= min_matches else "unknown"

if __name__ == '__main__':
    # 使用示例
    matcher = IconMatcher("relic_images/")
    
    # 测试匹配
    test_img = cv2.imread("img_matcher/00c540c8-ae5d-4804-b7ab-c1d16f9d300b.png")
    if test_img is not None:
        result = matcher.match(test_img)
        print(f"匹配结果: {result}")
    else:
        print("错误: 无法读取测试图像")

import os
import cv2
import numpy as np
import pickle
import time
from tqdm import tqdm
def serialize_keypoint(keypoint):
    """将KeyPoint对象转换为可序列化的字典"""
    return {
        'pt': keypoint.pt,
        'size': keypoint.size,
        'angle': keypoint.angle,
        'response': keypoint.response,
        'octave': keypoint.octave,
        'class_id': keypoint.class_id
    }

def deserialize_keypoint(data):
    """从字典重建KeyPoint对象"""
    return cv2.KeyPoint(
        x=data['pt'][0], y=data['pt'][1],
        size=data['size'], angle=data['angle'],
        response=data['response'], octave=data['octave'],
        class_id=data['class_id']
    )
class ImageFeatureDatabase:
    def __init__(self, feature_dim=128, k_clusters=100):
        self.feature_dim = feature_dim
        self.k_clusters = k_clusters
        self.database = {}
        self.cluster_centers = None
        self.feature_weights = None
        
    def extract_features(self, image):
        """提取SIFT特征并筛选关键点"""
        if image is None:
            return None, None, None
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sift = cv2.SIFT_create()
        
        # 检测关键点和描述符
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        
        if descriptors is None or len(descriptors) < 10:
            return None, None, None
            
        return keypoints, descriptors, image.shape[:2]
    
    def build_database(self, image_dir, force_rebuild=False, data_file="img_matcher/data/features_db.pkl"):
        """构建特征数据库"""
        if not force_rebuild and os.path.exists(data_file):
            self._load_database(data_file)
            return
        
        print("Building new feature database...")
        
        # 第一阶段：收集所有原始特征
        all_features = []
        image_data = {}
        
        for img_file in tqdm(os.listdir(image_dir)):
            if img_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                img_path = os.path.join(image_dir, img_file)
                img = cv2.imread(img_path)
                kp, desc, shape = self.extract_features(img)
                if desc is not None:
                    all_features.append(desc)
                    image_data[img_path] = {
                        'keypoints': kp,
                        'descriptors': desc,
                        'shape': shape
                    }
        
        if not image_data:
            raise ValueError("No valid images found in directory")
        
        # 第二阶段：特征聚类分析
        print("Analyzing feature clusters...")
        all_descriptors = np.vstack(all_features)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, self.cluster_centers = cv2.kmeans(
            all_descriptors.astype(np.float32),
            self.k_clusters,
            None,
            criteria,
            10,
            cv2.KMEANS_RANDOM_CENTERS
        )
        
        # 第三阶段：计算特征权重（TF-IDF风格）
        print("Calculating feature weights...")
        doc_freq = np.zeros(self.k_clusters)  # 包含该特征的图片数量
        total_images = len(image_data)
        
        for img_path, data in image_data.items():
            desc = data['descriptors']
            distances = np.linalg.norm(desc[:, np.newaxis] - self.cluster_centers, axis=2)
            closest_clusters = np.argmin(distances, axis=1)
            unique_clusters = np.unique(closest_clusters)
            doc_freq[unique_clusters] += 1
        
        # 避免除以零
        doc_freq[doc_freq == 0] = 1
        self.feature_weights = np.log(total_images / doc_freq)
        
        # 第四阶段：筛选每张图片的关键特征
        print("Selecting representative features...")
        for img_path, data in tqdm(image_data.items()):
            keypoints = data['keypoints']
            descriptors = data['descriptors']
            shape = data['shape']
            
            # 计算每个特征的权重分数
            distances = np.linalg.norm(descriptors[:, np.newaxis] - self.cluster_centers, axis=2)
            closest_clusters = np.argmin(distances, axis=1)
            feature_scores = self.feature_weights[closest_clusters] * [kp.response for kp in keypoints]
            
            # 选择得分最高的特征
            top_indices = np.argsort(feature_scores)[-100:]  # 取前100个最显著特征
            if len(top_indices) < 10:  # 最少保留10个特征
                top_indices = np.argsort(feature_scores)[-10:]
            
            # 存储优化后的特征
            self.database[img_path] = {
                'keypoints': [keypoints[i] for i in top_indices],
                'descriptors': descriptors[top_indices],
                'shape': shape,
                'feature_scores': feature_scores[top_indices]
            }
        
        self._save_database(data_file)
        print(f"Database built with {len(self.database)} images")
    
    def _load_database(self, filename):
        """从文件加载数据库"""
        print("加载已有数据", filename)

        with open(filename, 'rb') as f:
            loaded_data = pickle.load(f)
            
            # 如果是新版数据格式（应该包含database和cluster_centers）
            self.database = loaded_data['database']
            self.cluster_centers = loaded_data['cluster_centers']
            self.feature_weights = loaded_data['feature_weights']

        # 确保关键点是KeyPoint对象
        for img_path in self.database:
            if isinstance(self.database[img_path]["keypoints"][0], dict):
                self.database[img_path]["keypoints"] = [
                    deserialize_keypoint(kp) for kp in self.database[img_path]["keypoints"]
                ]
                
    def _compute_cluster_centers(self):
        """从现有数据库计算聚类中心"""
        print("重新计算聚类中心...")
        all_descriptors = []
        for img_path in self.database:
            all_descriptors.append(self.database[img_path]['descriptors'])
        
        all_descriptors = np.vstack(all_descriptors)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, _, self.cluster_centers = cv2.kmeans(
            all_descriptors.astype(np.float32),
            self.k_clusters,
            None,
            criteria,
            10,
            cv2.KMEANS_RANDOM_CENTERS
        )
        
        # 重新计算特征权重
        self._compute_feature_weights()

    def _compute_feature_weights(self):
        """计算特征权重"""
        print("计算特征权重...")
        doc_freq = np.zeros(self.k_clusters)
        total_images = len(self.database)
        
        for img_path, data in self.database.items():
            desc = data['descriptors']
            distances = np.linalg.norm(desc[:, np.newaxis] - self.cluster_centers, axis=2)
            closest_clusters = np.argmin(distances, axis=1)
            unique_clusters = np.unique(closest_clusters)
            doc_freq[unique_clusters] += 1
        
        doc_freq[doc_freq == 0] = 1
        self.feature_weights = np.log(total_images / doc_freq)

    def _save_database(self, filename):
        """保存数据库到文件"""
        temp_db = {}
        for img_path in self.database:
            temp_db[img_path] = {
                "keypoints": [serialize_keypoint(kp) for kp in self.database[img_path]["keypoints"]],
                "descriptors": self.database[img_path]["descriptors"],
                "shape": self.database[img_path]["shape"],
                "feature_scores": self.database[img_path]["feature_scores"]
            }
        
        # 保存完整数据（包括聚类中心和权重）
        full_data = {
            'database': temp_db,
            'cluster_centers': self.cluster_centers,
            'feature_weights': self.feature_weights
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            pickle.dump(full_data, f)


    
    def match_image(self, query_image, top_n=1):
        """匹配查询图像"""
        # 提取查询图像特征
        kp, desc, _ = self.extract_features(query_image)
        if desc is None:
            return []
        
        # 计算查询特征的cluster分布
        distances = np.linalg.norm(desc[:, np.newaxis] - self.cluster_centers, axis=2)
        query_clusters = np.argmin(distances, axis=1)
        
        # 使用FLANN匹配器
        flann = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 5}, {'checks': 50})
        match_scores = []

        tt = 0
        for img_path, data in self.database.items():
            db_desc = data['descriptors']
            
            oo = time.time()
            # 预过滤：检查是否有共享的cluster
            db_distances = np.linalg.norm(db_desc[:, np.newaxis] - self.cluster_centers, axis=2)
            db_clusters = np.argmin(db_distances, axis=1)
            common_clusters = set(query_clusters) & set(db_clusters)
            if not common_clusters:
                continue
            tt += time.time()-oo
                
            # 执行匹配
            matches = flann.knnMatch(desc, db_desc, k=2)
            
            # 应用比率测试
            good_matches = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good_matches.append(m)
            
            # 计算匹配分数（考虑特征权重）
            if len(good_matches) >= 4:
                match_score = sum(data['feature_scores'][m.trainIdx] for m in good_matches)
                match_scores.append((img_path, len(good_matches), match_score))

        print(tt)
        
        # 返回最佳匹配
        match_scores.sort(key=lambda x: (-x[1], -x[2]))
        return [x[0] for x in match_scores[:top_n]]


db = ImageFeatureDatabase(k_clusters=150)

# 构建/加载数据库
db.build_database("images/card_images")
# 使用示例
if __name__ == "__main__":
    # 初始化数据库
    # 查询测试
    query_image = "img_matcher/41dd7a6a-4c8d-4e4b-8003-6826805ee903.png"
    image = cv2.imread(query_image)
    tt = time.time()
    matches = db.match_image(image)
    print(time.time()-tt)
    
    print("\nTop matches:")
    for i, match in enumerate(matches, 1):
        print(f"{i}. {match}")

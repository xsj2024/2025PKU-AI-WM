import os
import cv2
import numpy as np
import pickle
import time
from tqdm import tqdm
from collections import defaultdict
from scipy.spatial import cKDTree  # 新增KDTree导入

def serialize_keypoint(keypoint):
    """保持原有序列化方法不变"""
    return {
        'pt': keypoint.pt,
        'size': keypoint.size,
        'angle': keypoint.angle,
        'response': keypoint.response,
        'octave': keypoint.octave,
        'class_id': keypoint.class_id
    }

def deserialize_keypoint(data):
    """保持原有反序列化方法不变"""
    return cv2.KeyPoint(
        x=data['pt'][0], y=data['pt'][1],
        size=data['size'], angle=data['angle'],
        response=data['response'], octave=data['octave'],
        class_id=data['class_id']
    )

def rootsift(descriptors):
    """对SIFT描述子做L1归一化和开方（RootSIFT）"""
    if descriptors is None:
        return None
    eps = 1e-7
    descriptors = descriptors / (np.linalg.norm(descriptors, ord=1, axis=1, keepdims=True) + eps)
    descriptors = np.sqrt(descriptors)
    return descriptors

class ImageFeatureDatabase:
    def __init__(self, feature_dim=128, k_clusters=100):
        self.feature_dim = feature_dim
        self.k_clusters = k_clusters
        self.database = {}
        self.cluster_centers = None
        self.feature_weights = None
        self.kdtree = None
        self.desc_cache = []
        self.img_indices = []
        self.cluster_to_indices = defaultdict(list)
        self.cluster_dists = None  # 新增

    def extract_features(self, image):
        """集成RootSIFT特征提取"""
        if image is None:
            return None, None, None
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        sift = cv2.SIFT_create()
        keypoints, descriptors = sift.detectAndCompute(gray, None)
        if descriptors is None or len(descriptors) < 10:
            return None, None, None
        descriptors = rootsift(descriptors)
        return keypoints, descriptors, image.shape[:2]
    
    def build_database(self, image_dir, force_rebuild=False, data_file="image_matcher/img_matcher/data/features_db.pkl"):
        if not force_rebuild and os.path.exists(data_file):
            self._load_database(data_file)
            return

        print("Building feature database...")
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
            raise ValueError("No valid images found")

        print("Clustering features...")
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

        self.kdtree = cKDTree(self.cluster_centers)

        print("Calculating weights...")
        self._compute_feature_weights(image_data)

        print("Building accelerated index...")
        self.desc_cache = []
        self.img_indices = []
        img_paths = list(image_data.keys())

        for img_idx, img_path in enumerate(img_paths):
            data = image_data[img_path]
            kp = data['keypoints']
            desc = data['descriptors']
            shape = data['shape']

            distances = np.linalg.norm(desc[:, np.newaxis] - self.cluster_centers, axis=2)
            closest_clusters = np.argmin(distances, axis=1)
            feature_scores = self.feature_weights[closest_clusters] * [kp[i].response for i in range(len(kp))]

            top_indices = np.argsort(feature_scores)[-100:] if len(feature_scores) > 100 else np.arange(len(feature_scores))

            self.database[img_path] = {
                'keypoints': [kp[i] for i in top_indices],
                'descriptors': desc[top_indices],
                'shape': shape,
                'feature_scores': feature_scores[top_indices],
                'cache_range': (len(self.desc_cache), len(self.desc_cache) + len(top_indices))
            }

            self.desc_cache.extend(desc[top_indices])
            self.img_indices.extend([img_idx] * len(top_indices))

        print("Building cluster index...")
        all_desc = np.array(self.desc_cache)
        cluster_dists = np.linalg.norm(all_desc[:, np.newaxis] - self.cluster_centers, axis=2)
        np.save("image_matcher/img_matcher/data/cluster_dists.npy", cluster_dists)  # 保存
        closest_clusters = np.argmin(cluster_dists, axis=1)

        for feat_idx, cluster in enumerate(closest_clusters):
            self.cluster_to_indices[cluster].append(feat_idx)

        self._save_database(data_file)
    
    def _compute_feature_weights(self, image_data):
        """保持原有权重计算逻辑"""
        doc_freq = np.zeros(self.k_clusters)
        total_images = len(image_data)
        
        for img_path, data in image_data.items():
            desc = data['descriptors']
            distances = np.linalg.norm(desc[:, np.newaxis] - self.cluster_centers, axis=2)
            closest_clusters = np.argmin(distances, axis=1)
            unique_clusters = np.unique(closest_clusters)
            doc_freq[unique_clusters] += 1
        
        doc_freq[doc_freq == 0] = 1
        self.feature_weights = np.log(total_images / doc_freq)
    
    def _load_database(self, filename):
        print(f"Loading database from {filename}...")
        with open(filename, 'rb') as f:
            loaded_data = pickle.load(f)
            self.database = {}
            for img_path, data in loaded_data['database'].items():
                self.database[img_path] = {
                    'keypoints': [deserialize_keypoint(kp) for kp in data['keypoints']],
                    'descriptors': data['descriptors'],
                    'shape': data['shape'],
                    'feature_scores': data['feature_scores'],
                    'cache_range': data.get('cache_range', (0, len(data['descriptors'])))
                }
            self.cluster_centers = loaded_data['cluster_centers']
            self.feature_weights = loaded_data['feature_weights']

        self.desc_cache = []
        self.img_indices = []
        img_paths = list(self.database.keys())

        for img_idx, img_path in enumerate(img_paths):
            data = self.database[img_path]
            self.desc_cache.extend(data['descriptors'])
            self.img_indices.extend([img_idx] * len(data['descriptors']))

        self.kdtree = cKDTree(self.cluster_centers)
        self.cluster_to_indices = defaultdict(list)

        self.cluster_dists = np.load("image_matcher/img_matcher/data/cluster_dists.npy")  # 加载
        closest_clusters = np.argmin(self.cluster_dists, axis=1)
        for feat_idx, cluster in enumerate(closest_clusters):
            self.cluster_to_indices[cluster].append(feat_idx)
    
    def _save_database(self, filename):
        """保持原有保存逻辑不变"""
        temp_db = {}
        for img_path in self.database:
            temp_db[img_path] = {
                "keypoints": [serialize_keypoint(kp) for kp in self.database[img_path]["keypoints"]],
                "descriptors": self.database[img_path]["descriptors"],
                "shape": self.database[img_path]["shape"],
                "feature_scores": self.database[img_path]["feature_scores"],
                "cache_range": self.database[img_path]["cache_range"]
            }
        
        full_data = {
            'database': temp_db,
            'cluster_centers': self.cluster_centers,
            'feature_weights': self.feature_weights
        }
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            pickle.dump(full_data, f)
    
    def match_image(self, query_image, top_n=1):
        """优化后的匹配方法（接口不变）"""
        kp, desc, _ = self.extract_features(query_image)
        if desc is None:
            return []
        
        # 步骤1：使用KDTree定位相关聚类
        _, query_clusters = self.kdtree.query(desc, k=2)  # 查询最近的2个聚类
        unique_clusters = np.unique(query_clusters.flatten())
        
        # 步骤2：获取候选特征索引
        candidate_indices = []
        for cluster in unique_clusters:
            candidate_indices.extend(self.cluster_to_indices[cluster])
        candidate_indices = np.unique(candidate_indices)
        
        # 步骤3：执行受限的FLANN匹配
        flann = cv2.FlannBasedMatcher({'algorithm': 1, 'trees': 5}, {'checks': 50})
        matches = flann.knnMatch(
            desc, 
            np.array([self.desc_cache[i] for i in candidate_indices]), 
            k=2
        )
        
        # 步骤4：评分（保持原有逻辑）
        match_scores = defaultdict(lambda: [0, 0.0])  # {img_idx: [match_count, total_score]}
        img_paths = list(self.database.keys())
        
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                matched_idx = candidate_indices[m.trainIdx]
                img_idx = self.img_indices[matched_idx]
                img_path = img_paths[img_idx]
                
                # 找到原始特征在图片中的位置
                local_idx = matched_idx - self.database[img_path]['cache_range'][0]
                match_scores[img_path][0] += 1
                match_scores[img_path][1] += self.database[img_path]['feature_scores'][local_idx]
        
        # 筛选并排序结果
        valid_matches = [(k, v[0], v[1]) for k, v in match_scores.items()]
        valid_matches.sort(key=lambda x: (-x[1], -x[2]))
        return [os.path.basename(x[0])[:-4] for x in valid_matches[:top_n]]

db = ImageFeatureDatabase(k_clusters=100)
db.build_database("image_matcher/images/card_images")

def get_card(img):
    res = db.match_image(img, top_n=1)
    if len(res) == 0:
        return "Unknown"
    return res[0]

# 使用示例保持不变
if __name__ == "__main__":
    
    import time
    tt = time.time()
    query_img = cv2.imread("image_matcher/img_matcher/QQ_1749824634776.png")
    matches = db.match_image(query_img, top_n=1)

    print(time.time()-tt)
    
    print("\nTop matches:")
    for vv in matches:
        print(vv)

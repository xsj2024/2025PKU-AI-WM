import cv2
import numpy as np
import os
import pickle


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
def extract_features(image_path):
    """从单张图片提取特征并返回"""
    image = cv2.imread(image_path)
    if image is None:
        return None, None, None
    
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    sift = cv2.SIFT_create()
    keypoints, descriptors = sift.detectAndCompute(gray, None)
    return keypoints, descriptors, image.shape[:2]

def build_or_load_database(image_dir, features_file="img_matcher\\data\\card_features.pkl"):
    """构建或加载图像特征数据库"""
    if os.path.exists(features_file):
        # 如果特征文件存在，直接加载
        with open(features_file, 'rb') as f:
            database = pickle.load(f)
            # 需要将字典转换回KeyPoint对象
            for img_path in database:
                database[img_path]['keypoints'] = [
                    deserialize_keypoint(kp) for kp in database[img_path]['keypoints']
                ]
    else:
        # 否则从图像构建数据库
        database = {}
        for filename in os.listdir(image_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                img_path = os.path.join(image_dir, filename)
                kp, desc, shape = extract_features(img_path)
                if kp is not None and desc is not None:
                    # 将KeyPoint转换为可序列化的字典
                    serialized_kp = [serialize_keypoint(p) for p in kp]
                    database[img_path] = {
                        "keypoints": serialized_kp,
                        "descriptors": desc,
                        "image_shape": shape
                    }
        
        # 保存特征到文件
        with open(features_file, 'wb') as f:
            pickle.dump(database, f)
    
    return database

def match_image(query_path, database, min_matches=10):
    """在数据库中匹配查询图像"""
    query_kp, query_desc, _ = extract_features(query_path)
    if query_kp is None or query_desc is None:
        return None, 0
    
    best_match = None
    best_inliers = 0
    matcher = cv2.BFMatcher()
    
    for db_path, db_data in database.items():
        matches = matcher.knnMatch(query_desc, db_data["descriptors"], k=2)
        
        # 应用ratio test过滤
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)
        
        if len(good_matches) > min_matches:
            src_pts = np.float32([query_kp[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
            dst_pts = np.float32([db_data["keypoints"][m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)
            
            # 寻找变换矩阵
            _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
            
            inliers = np.sum(mask)
            if inliers > best_inliers:
                best_inliers = inliers
                best_match = db_path
    
    return best_match, best_inliers

# 使用示例
image_dir = "images/card_images"  # 替换为你的图像目录
query_image = "img_matcher/171e9455-1c47-4206-8760-491ef6c69338(1).png"     # 替换为查询图像路径

# 构建或加载数据库
database = build_or_load_database(image_dir)

# 匹配查询图像
best_match, confidence = match_image(query_image, database)

if best_match:
    print(f"最佳匹配: {best_match} (置信度: {confidence})")
else:
    print("未找到匹配的图像")

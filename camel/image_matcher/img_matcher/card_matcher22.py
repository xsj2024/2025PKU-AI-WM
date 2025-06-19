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

def load_database(features_file):
    """从文件加载数据库并确保正确反序列化KeyPoints"""
    with open(features_file, 'rb') as f:
        database = pickle.load(f)
        # 正确转换关键点
        for img_path in database:
            # 确保关键点是KeyPoint对象
            if isinstance(database[img_path]["keypoints"][0], dict):
                database[img_path]["keypoints"] = [
                    deserialize_keypoint(kp) for kp in database[img_path]["keypoints"]
                ]
    return database

def save_database(database, features_file):
    """保存数据库到文件"""
    # 临时转换关键点为可序列化的字典
    temp_db = {}
    for img_path in database:
        temp_db[img_path] = {
            "keypoints": [serialize_keypoint(kp) for kp in database[img_path]["keypoints"]],
            "descriptors": database[img_path]["descriptors"],
            "image_shape": database[img_path]["image_shape"]
        }
    
    with open(features_file, 'wb') as f:
        pickle.dump(temp_db, f)

def build_or_load_database(image_dir, features_file="img_matcher\\data\\card_features.pkl"):
    """构建或加载图像特征数据库"""
    if os.path.exists(features_file):
        # 如果特征文件存在，直接加载
        return load_database(features_file)
    else:
        # 否则从图像构建数据库
        database = {}
        for filename in os.listdir(image_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                img_path = os.path.join(image_dir, filename)
                kp, desc, shape = extract_features(img_path)
                if kp is not None and desc is not None:
                    database[img_path] = {
                        "keypoints": kp,  # 保持为原始KeyPoint对象
                        "descriptors": desc,
                        "image_shape": shape
                    }
        
        # 保存特征到文件
        save_database(database, features_file)
        return database

def match_image(query_path, database, min_matches=10):
    """在数据库中匹配查询图像，改进部分图像匹配能力"""
    query_kp, query_desc, _ = extract_features(query_path)
    if query_kp is None or query_desc is None:
        return None, 0
    
    best_match = None
    best_inliers = 0
    matcher = cv2.BFMatcher()
    
    for db_path, db_data in database.items():
        matches = matcher.knnMatch(query_desc, db_data["descriptors"], k=2)
        
        # 应用更宽松的ratio test以提高部分匹配的容错率
        good_matches = []
        for m, n in matches:
            if m.distance < 0.8 * n.distance:  # 从0.75放宽到0.8
                good_matches.append(m)
        
        if len(good_matches) >= min_matches:  # 使用>=而不是>以允许刚好满足最小匹配数的情况
            try:
                src_pts = np.float32([query_kp[m.queryIdx].pt for m in good_matches]).reshape(-1,1,2)
                dst_pts = np.float32([db_data["keypoints"][m.trainIdx].pt for m in good_matches]).reshape(-1,1,2)
                
                # 使用更宽松的RANSAC参数
                _, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 10.0)  # RANSAC阈值从5.0增加到10.0
                
                inliers = np.sum(mask)
                
                # 考虑匹配点数与特征点总数的比例
                match_ratio = inliers / len(query_kp)
                
                # 综合inliers数量和比例来确定最佳匹配
                if inliers > best_inliers or (inliers == best_inliers and match_ratio > best_inliers/len(query_kp)):
                    best_inliers = inliers
                    best_match = db_path
            except Exception as e:
                print(f"处理图像 {db_path} 时出错: {e}")
                continue
    
    return best_match, best_inliers


if __name__ == "__main__":
    # 使用示例
    image_dir = "images/card_images"  # 替换为你的图像目录
    query_image = "img_matcher/171e9455-1c47-4206-8760-491ef6c69338.png"     # 替换为查询图像路径

    # 构建或加载数据库
    database = build_or_load_database(image_dir)

    # 匹配查询图像
    best_match, confidence = match_image(query_image, database)

    if best_match:
        print(f"最佳匹配: {best_match} (置信度: {confidence})")
    else:
        print("未找到匹配的图像")


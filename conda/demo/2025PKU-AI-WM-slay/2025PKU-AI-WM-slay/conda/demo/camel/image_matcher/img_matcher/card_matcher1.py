import os
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from sklearn.metrics.pairwise import cosine_similarity
import cv2

# 增强的预处理流程
def get_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.RandomAffine(  # 添加更全面的空间变换增强
            degrees=30,  # 旋转范围
            translate=(0.2, 0.2),  # 平移范围
            shear=15,  # 剪切变换
            scale=(0.8, 1.2)  # 缩放范围
        ),
        transforms.ColorJitter(  # 颜色增强
            brightness=0.2,
            contrast=0.2,
            saturation=0.2
        ),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                          std=[0.229, 0.224, 0.225]),
    ])

# 使用更轻量且鲁棒的MobileNetV3
def load_model():
    model = models.vgg16(pretrained=True)
    model.classifier = nn.Identity()  # 去掉分类头
    model.eval()
    return model

# 优化的特征提取
def get_feature_vector(image, model):
    if isinstance(image, np.ndarray):
        image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    
    # 创建多个视角提升鲁棒性
    augmented_images = [
        image,  # 原始
        image.rotate(10),  # +10度
        image.rotate(-10),  # -10度
        image.crop((0.1*image.width, 0.1*image.height, 0.9*image.width, 0.9*image.height)).resize(image.size)  # 中心90%区域
    ]
    
    features = []
    transform = get_transform()
    for img in augmented_images:
        with torch.no_grad():
            tensor = transform(img).unsqueeze(0)
            features.append(model(tensor).squeeze().numpy())
    
    return np.mean(features, axis=0)  # 多视角特征平均

# 初始化
model = load_model()

# 特征数据库（建议预计算存储）
def build_feature_database(image_dir):
    database = {}
    for img_name in os.listdir(image_dir):
        img_path = os.path.join(image_dir, img_name)
        image = Image.open(img_path).convert('RGB')
        feature = get_feature_vector(np.array(image), model)
        database[img_name[:-4]] = feature
    return database

# 查询函数
def query_card(query_image, database):
    query_feature = get_feature_vector(query_image, model)
    
    results = []
    for name, feature in database.items():
        sim = cosine_similarity([query_feature], [feature])[0][0]
        results.append((name, sim))
    
    # 返回按相似度排序的结果
    return sorted(results, key=lambda x: -x[1])

class FeatureDatabase:
    def __init__(self, db_path="img_matcher/data/card.npz"):
        self.db_path = db_path
        self.database = None  # {'card1': feature_vec, ...}
        self.model = None
        self.init_model()
    
    def init_model(self):
        if not self.model:
            self.model = models.mobilenet_v3_large(pretrained=True)
            self.model.classifier = nn.Identity()
            self.model.eval()
    
    def build_from_images(self, image_dir):
        self.database = {}
        
        for img_name in os.listdir(image_dir):
            if not img_name.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            img_path = os.path.join(image_dir, img_name)
            image = Image.open(img_path).convert('RGB')
            feature = get_feature_vector(np.array(image), self.model)
            card_name = os.path.splitext(img_name)[0]
            self.database[card_name] = feature
        
        self._save_to_disk()
    
    def _save_to_disk(self):
        np.savez(
            self.db_path,
            names=np.array(list(self.database.keys())),
            features=np.array(list(self.database.values()))
        )
    
    def load_from_disk(self):
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"特征数据库 {self.db_path} 不存在")
            
        data = np.load(self.db_path, allow_pickle=True)
        self.database = dict(zip(data['names'], data['features']))
    
    def query(self, query_image, top_k=5):
        if not self.database:
            self.load_from_disk()
            
        query_feat = get_feature_vector(query_image, self.model)
        results = []
        
        for name, feat in self.database.items():
            sim = cosine_similarity([query_feat], [feat])[0][0]
            results.append((name, sim))
        
        return sorted(results, key=lambda x: -x[1])[:top_k]
db = FeatureDatabase()

# 首次运行需要构建数据库（后续会自动加载）
if not os.path.exists(db.db_path):
    print("构建特征数据库...")
    db.build_from_images("images/card_images")
else:
    print("加载已存在的数据库...")
    db.load_from_disk()

# 使用示例
if __name__ == '__main__':
    # 查询图像
    query_img = cv2.imread("img_matcher/19da8835-4946-4978-b79b-c202618b6894.png")
    matches = db.query(query_img)
    
    print("Top 5匹配结果:")
    for name, score in matches[:5]:
        print(f"{name}: {score:.4f}")

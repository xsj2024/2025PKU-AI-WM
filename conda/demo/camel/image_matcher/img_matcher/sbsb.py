import os
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from sklearn.metrics.pairwise import cosine_similarity

class RelicMatcher:
    database_vectors, images_paths = None, None
    def __init__(self, images_dir="relic_images", features_dir="img_matcher/data"):
        """
        初始化文物匹配器
        
        参数:
            images_dir: 文物图片目录路径
            features_dir: 特征存储目录路径
        """
        self.images_dir = images_dir
        self.features_dir = features_dir
        self.features_file = os.path.join(features_dir, "database_features.npy")
        self.paths_file = os.path.join(features_dir, "image_paths.npy")
        
        # 确保特征目录存在
        os.makedirs(features_dir, exist_ok=True)
        
        # 初始化模型
        self.model = self._load_model()
        self.transform = self._get_preprocess_transform()
        
        # 加载数据库特征
        RelicMatcher.database_vectors, RelicMatcher.images_paths = self._load_or_extract_features()

    def _load_model(self):
        """加载预训练的ResNet50模型(去除全连接层)"""
        model = models.resnet50(pretrained=True)
        modules = list(model.children())[:-1]  # 去掉全连接层
        model = nn.Sequential(*modules)
        model.eval()
        return model

    def _get_preprocess_transform(self):
        """获取图像预处理转换"""
        return transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                                std=[0.229, 0.224, 0.225]),
        ])

    def get_feature_vector(self, image):
        """获取图像特征向量"""
        image = self.transform(image).unsqueeze(0)
        with torch.no_grad():
            feature_vector = self.model(image)
            return feature_vector.squeeze().numpy()

    def _load_or_extract_features(self):
        """加载或提取数据库图片特征"""
        if os.path.exists(self.features_file) and os.path.exists(self.paths_file):
            # 如果特征文件存在，直接加载
            database_vectors = np.load(self.features_file)
            images_paths = np.load(self.paths_file)
            print("从文件加载存储的图像特征")
        else:
            # 否则提取特征并保存
            print("提取图像特征并保存...")
            images_paths = [os.path.join(self.images_dir, img_name) 
                          for img_name in os.listdir(self.images_dir)]
            database_vectors = []
            
            for img_path in images_paths:
                try:
                    image = Image.open(img_path).convert('RGB')
                    feature_vector = self.get_feature_vector(image)
                    database_vectors.append(feature_vector)
                except Exception as e:
                    print(f"处理图片 {img_path} 时出错: {e}")
                    continue
            
            database_vectors = np.array(database_vectors)
            np.save(self.features_file, database_vectors)
            np.save(self.paths_file, images_paths)
            print("图像特征已保存")
        
        return database_vectors, images_paths

    def match_image(self, img):
        """
        匹配查询图片与数据库中最相似的图片
        
        参数:
            query_image_path: 查询图片路径
            top_k: 返回最相似的k个结果
            
        返回:
            包含匹配结果的字典列表，按相似度降序排列
        """
        # 提取查询图片特征
        query_image = Image.open(query_image_path).convert('RGB')
        query_vector = self.get_feature_vector(query_image)
        
        # 计算相似度
        similarities = cosine_similarity([query_vector], RelicMatcher.database_vectors)[0]
        most_similar_index = similarities.argmax()
        max_similarity = similarities[most_similar_index]
        
        return {"image_path" : RelicMatcher.images_paths[most_similar_index], "similarity" : max_similarity}

if __name__ == '__main__':
    import time
    matcher = RelicMatcher(
        images_dir="relic_images",
        features_dir="img_matcher/data"
    )
    
    # 查询图片路径
    query_image_path = "img_matcher/a2da66d8-b248-44cc-a3ff-afb99191f513.png"
    
    # 进行匹配
    start_time = time.time()
    
    # 测试100次匹配性能
    for i in range(100):
        result = matcher.match_image(query_image_path)
        
    elapsed_time = time.time() - start_time
    
    # 输出结果
    print(f"最相似的图片路径: {result['image_path']}")
    print(f"相似度: {result['similarity']:.4f}")
    
    # 性能统计
    print(f"\n总计算时间: {elapsed_time:.4f}秒")
    print(f"每次查询平均时间: {elapsed_time/100:.4f}秒")
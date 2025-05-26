import os
import numpy as np
from PIL import Image
import torch
import torch.nn as nn
import torchvision.models as models
import torchvision.transforms as transforms
from sklearn.metrics.pairwise import cosine_similarity
import time
import cv2

# 模型预处理
transform = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# 使用预训练的ResNet50模型去除全连接层
def load_model():
    model = models.resnet50(pretrained=True)
    modules = list(model.children())[:-1]  # 去掉全连接层
    model = nn.Sequential(*modules)
    model.eval()
    return model

# 获取图像特征向量
def get_feature_vector(image):
    if isinstance(image, np.ndarray):  # OpenCV 图像
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  # BGR→RGB
        image = Image.fromarray(image)  # numpy→PIL
    elif not isinstance(image, Image.Image):  # 非PIL图像时报错
        raise ValueError("输入必须是OpenCV(numpy)或PIL图像")
    image = transform(image).unsqueeze(0)
    with torch.no_grad():
        feature_vector = model(image)
        return feature_vector.squeeze().numpy()

# 图片集路径和查询图片路径
images_dir = "images/relic_images"
features_file = "img_matcher/data/relic_features.npy"
names_file = "img_matcher/data/relic_names.npy"

# 加载模型
model = load_model()

# 加载或提取数据库图片特征
if os.path.exists(features_file) and os.path.exists(names_file):
    # 如果特征文件存在，直接加载
    database_vectors = np.load(features_file)
    relic_names = np.load(names_file)
    print("从文件加载存储的图像特征")
else:
    # 否则提取特征并保存
    print("提取图像特征并保存...")
    relic_names = []
    database_vectors = []
    for img_name in os.listdir(images_dir):
        img_path = os.path.join(images_dir, img_name)
        image = Image.open(img_path).convert('RGB')
        feature_vector = get_feature_vector(image)
        database_vectors.append(feature_vector)
        relic_names.append(img_name[:-4])
    
    database_vectors = np.array(database_vectors)
    np.save(features_file, database_vectors)
    np.save(names_file, relic_names)
    print("图像特征已保存")

def get_relic(query_image):
    query_vector = get_feature_vector(query_image)
    similarities = cosine_similarity([query_vector], database_vectors)[0]
    most_similar_index = similarities.argmax()
    max_similarity = similarities[most_similar_index]
    
    return {"name":relic_names[most_similar_index], "similarity":max_similarity}
if __name__ == '__main__':
    # 提取查询图片特征(每次都重新提取)
    query_image_path = "img_matcher/692e6f2f-cb3e-470b-bfa6-832752a55314.png"
    # query_image = Image.open(query_image_path).convert('RGB')
    query_image = cv2.imread(query_image_path)

    # 计算相似度
    start_time = time.time()
    tt = 1
    for i in range(tt):
        res = get_relic(query_image)

        # 输出最相似的图片信息
        print(f"最相似的图片：{res['name']}")
        print(f"相似度：{res['similarity']}")

    elapsed_time = time.time() - start_time
    print(f"总计算时间: {elapsed_time}秒")
    print(f"每次查询平均时间: {elapsed_time/tt}秒")

import cv2

img = cv2.imread("img_matcher/oddlysmoothstone.png")  # 替换为你的图片路径
# 初始化 ORB（调整参数重点提取）
orb = cv2.ORB_create(
    nfeatures=50,           # 提取的最大特征点数
    scaleFactor=1.2,        # 降低金字塔缩放比（小图不需要多尺度）
    edgeThreshold=3,        # 减少边缘过滤（小图边缘更敏感）
    patchSize=15            # 描述子生成区域大小（适配小图）
)

# 检测与匹配
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
kp, des = orb.detectAndCompute(gray, None)
print("ORB Features:", len(kp))  # 通常能提取 10~50 个点

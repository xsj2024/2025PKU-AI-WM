import cv2
img = cv2.imread("img_matcher/oddlysmoothstone.png")  # 替换为你的图片路径
print("Image shape:", img.shape)  # 确认尺寸和通道数 (H,W,3)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
sift = cv2.SIFT_create()
kp, des = sift.detectAndCompute(gray, None)

print("Number of SIFT features:", len(kp))
cv2.imwrite("img_matcher/sbsbsb.png", gray)  # 保存灰度图检查是否异常

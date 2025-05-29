import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urljoin

URL = "https://slay-the-spire.fandom.com/wiki/Relics"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SAVE_DIR = "relic_images_v2"

def download_relic_images():
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    response = requests.get(URL, headers=HEADERS)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    # 匹配两种结构的父级元素
    containers = soup.find_all(lambda tag: 
        tag.name in ["figure", "span"] and (
            "thumb" in tag.get("class", []) or 
            tag.get("typeof") == "mw:File"
        )
    )

    for container in containers:
        # 统一提取逻辑：优先获取有效img标签
        img_tag = container.find("img", {
            "data-src": True, 
            "data-image-name": True
        })
        
        if not img_tag:
            continue

        # 提取遗物名称（优先级：data-image-name > alt > 父级a的title）
        relic_name = (
            img_tag.get("data-image-name", "").replace(".png", "") or
            img_tag.get("alt", "") or
            container.find("a").get("title", "").replace(" ", "_")
        ).lower()

        # 提取真实图片URL（处理三种可能情况）
        img_url = (
            img_tag.get("data-src") or          # 延迟加载
            img_tag.get("src") or               # 常规情况
            container.find("noscript").find("img").get("src")  # 降级方案
        ).split("?")[0]                        # 移除URL参数

        # 补全相对路径
        if not img_url.startswith(("http", "//")):
            img_url = urljoin("https://static.wikia.nocookie.net/", img_url)

        # 下载保存
        try:
            response = requests.get(img_url, headers=HEADERS)
            response.raise_for_status()
            with open(os.path.join(SAVE_DIR, f"{relic_name}.png"), "wb") as f:
                f.write(response.content)
            print(f"✅ 下载成功: {relic_name}.png")
        except Exception as e:
            
            print(f"❌ 失败 {relic_name}: {str(e)[:50]}...")

if __name__ == "__main__":
    download_relic_images()

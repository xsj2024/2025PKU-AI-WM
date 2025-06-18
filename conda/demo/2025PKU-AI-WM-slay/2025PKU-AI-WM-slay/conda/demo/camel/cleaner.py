import re
import json
from difflib import get_close_matches
from typing import List, Dict, Tuple, Optional

class Cleaner:
    def __init__(self, card_info_paths: List[str]):
        """初始化支持多卡牌数据库"""
        self.card_info = []
        self.card_names = []
        
        # 加载所有卡牌数据库
        for path in card_info_paths:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.card_info.extend(data)
                self.card_names.extend([card["name"] for card in data])
        # 预处理OCR文本的正则表达式
        self.item_pattern = re.compile(
            r"(?P<index>\d+)\.\s*\[(?P<category>\w+)\](?P<metadata>.*?)- Price: (?P<price>[\w\s]+)$",
            re.MULTILINE | re.DOTALL
        )
        self.sale_tag_pattern = re.compile(r"SALE|sale|促销|特价")
        self.newline_clean_pattern = re.compile(r"[\n_]\s*")
        
        # 特殊错误映射表
        self.special_mapping = {
            "slai": "Slam",
            "nladk": "Attack",
            "panacea": "Panacea",
            "aladk": "Attack"
        }
        
        # 为卡牌名称构建更高效的查找结构
        self.name_lookup = {name.lower(): name for name in self.card_names}
    
    def clean_ocr_text(self, raw_text: str) -> List[Dict]:
        """主清洗函数"""
        # 分割原始文本为各个商品条目
        print(raw_text)
        
        items = [
            m.groupdict() 
            for m in self.item_pattern.finditer(raw_text)
        ]
        
        cleaned_items = []
        for item in items:
            cleaned = self._clean_single_item(item)
            if cleaned:
                cleaned_items.append(cleaned)
        return cleaned_items
    def _process_card_remove(self, index,metadata: str, price: int) -> Dict:
        return {
            "index":index,
            "type": "card_removal_service",
            "name": "card_removal_service",
            "price": price,
        }
    def _process_leave(self, index,metadata: str) -> Dict:
        return {
            "index":index,
            "type": "leave",
            "name": "leave",
            "price": 0,
        }
    def _clean_single_item(self, item: Dict) -> Optional[Dict]:
        """处理单个商品条目"""
        print(item)
        index = item["index"]
        category = item["category"].lower()
        metadata = self._preprocess_metadata(item["metadata"])
        price = self._clean_price(item["price"])
        if category == "card":
            return self._process_card(index,metadata, price)
        
        if category == "card_removal_service":
            return self._process_card_remove(index,metadata, price)
        
        if category == "leave":
            return self._process_leave(index,metadata)
        #elif category == "potion":
        #    return self._process_potion(metadata, price)
        #elif category == "relic":
        #    return self._process_relic(metadata, price)
        return None
    
    def _preprocess_metadata(self, text: str) -> str:
        """清洗元数据文本"""
        # 合并换行和下划线
        text = self.newline_clean_pattern.sub(" ", text)
        # 移除特殊字符
        text = re.sub(r"[^a-zA-Z0-9\s]", "", text)
        return text.strip()
    
    def _clean_price(self, price_text: str) -> int:
        """提取价格数字"""
        price_digits = re.sub(r"[^\d]", "", price_text)
        return int(price_digits) if price_digits else 0
    
    def _process_card(self,index, metadata: str, price: int) -> Dict:
        """处理卡牌类型的商品"""
        # 分割元数据组件
        parts = [p for p in metadata.split() if p]
        is_on_sale = any(self.sale_tag_pattern.search(p) for p in parts)
        
        # 提取可能的费用 (数字开头部分)
        cost = next((p for p in parts if p.isdigit()), "?")
        
        # 查找最匹配的卡牌名称
        name_candidates = " ".join(parts[1:])  # 跳过第一部分(通常是费用)
        matched_name = self._find_closest_card_name(name_candidates)
        
        # 获取卡牌完整信息
        card_info = next(
            (c for c in self.card_info if c["name"] == matched_name),
            {"name": matched_name, "description": "Unknown card"}
        )
        return {
            "index":index,
            "type": "card",
            "name": card_info["name"],
            "cost": cost,
            "original_cost": card_info.get("cost", "?"),
            "price": price,
            "rarity": card_info.get("rarity", "Unknown"),
            "description": card_info["description"],
            "on_sale": is_on_sale
        }
    
    def _process_potion(self, metadata: str, price: int) -> Dict:
        """处理药水类型的商品"""
        common_potions = {
            "attack": "Attack Potion",
            "power": "Power Potion",
            "skill": "Skill Potion",
            "strength": "Strength Potion",
            "block": "Block Potion"
        }
        
        # 查找最接近的药水名称
        potion_text = metadata.lower()
        best_match = get_close_matches(
            potion_text,
            common_potions.values(),
            n=1,
            cutoff=0.4
        )
        
        name = best_match[0] if best_match else "Mystery Potion"
        return {
            "type": "potion",
            "name": name,
            "price": price
        }
    
    def _process_relic(self, metadata: str, price: int) -> Dict:
        """处理遗物类型的商品"""
        common_relics = [
            "Blood Vial", "Strength", "Weakness",
            "Burning Blood", "Molten Egg"
        ]
        
        relic_text = metadata.lower()
        best_match = get_close_matches(
            relic_text,
            common_relics,
            n=1,
            cutoff=0.4
        )
        
        name = best_match[0] if best_match else "Mystery Relic"
        return {
            "type": "relic",
            "name": name,
            "price": price
        }
    def filter_leading_number(self,text: str):
        """过滤掉字符串开头的数字及其后的空格
        
        Args:
            text (str): 输入字符串，例如 "1 Body Slai Aladk Deal damage equal to your Block"
        
        Returns:
            str: 去掉开头的数字后的字符串，例如 "Body Slai Aladk Deal damage equal to your Block"
        """
        # 使用正则表达式匹配开头的数字及可能的空格，并替换为空
        return re.sub(r'^\d+\s*', '', text)
    def _find_closest_card_name(self, text: str) -> str:
        """增强版卡牌名称匹配"""
        # 0. 预处理输入文本
        text=self.filter_leading_number(text)
        clean_text = self._preprocess_text(text)
        if not clean_text:
            return "Unknown_EmptyInput"
        
        # 2. 尝试精确小写匹配
        lower_text = clean_text.lower()
        if lower_text in self.name_lookup:
            return self.name_lookup[lower_text]
        
        # 3. 尝试模糊匹配（多阶段）
        words = clean_text.split()
        phrases = [' '.join(words[:i]) for i in range(len(words), 0, -1)]
        # 2. 对每个短语尝试模糊匹配（阈值从高到低）
        thresholds = [0.9, 0.8, 0.7]  # 逐步放宽
        for phrase in phrases:
            for threshold in thresholds:
                matches = get_close_matches(
                    phrase,
                    self.card_names,
                    n=1,
                    cutoff=threshold
                )
                if matches:
                    return matches[0]
        
        # 最终回退
        return f"Unknown_{clean_text[:15].strip('_')}"
    
    def _preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 替换已知OCR错误
        for wrong, correct in self.special_mapping.items():
            text = text.replace(wrong, correct)
        
        # 清理特殊字符
        text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
        
        # 合并空格并去除首尾空白
        return " ".join(text.split()).strip()
    def clean_and_match_cards(self, raw_text: str) -> List[Tuple[str, str]]:
        """
        将原始文本分割成 (idx, content) 的列表
        """
        # 支持行首有空白
        pattern = r'(?m)^\s*(\d+):\s*([\s\S]*?)(?=^\s*\d+:|\Z)'
        matches = re.findall(pattern, raw_text)
        result = [(idx, self._find_closest_card_name(content.strip())) for idx, content in matches]
        
        return result
    def parse_shop_text_to_json(self,items):
        """将商店文本转换成 shop.json 格式"""
        shop_data = {
            "cards": [],
            "relics": [],
            "potions": [],
            "remove_cost": ["0",100000]  # 默认值
        }
        # 正则匹配模式（匹配卡牌 / 遗物 / 药水 / 移除服务）
        print(items)
        for item in items:
            item_type = item['type']  
            name = item['name']
            price= item['price']
            index = item['index']
            if item_type == "card":
                shop_data["cards"].append([index,name, price])
            elif item_type == "relic":
                shop_data["relics"].append([index,name, price])
            elif item_type == "potion":
                shop_data["potions"].append([index,name, price])
            elif item_type == "card_removal_service":
                shop_data["remove_cost"] = [index,price]
            elif item_type == "leave":
                shop_data["leave"] = [index]
        return shop_data
    def clean_and_save(self,raw_ocr_text):
        cleaned_items = self.clean_ocr_text(raw_ocr_text)
        shop_data = self.parse_shop_text_to_json(cleaned_items)
        with open("D:/conda/camel/game_data/shop.json", "w", encoding="utf-8") as f:
            json.dump(shop_data, f, indent=2, ensure_ascii=False)
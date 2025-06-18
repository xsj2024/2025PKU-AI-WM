import os
import re
import json
import sys
import math
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType


# File path constants
DATA_DIR = "D:\\conda\\camel\\game_data"
STATUS_FILE = f"{DATA_DIR}/status.json"
CARD_KB_FILE = f"./game_info/card_info.json"
SHOP_FILE = f"{DATA_DIR}/shop.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"
class Rest:
    def __init__(self,manager):
        self.manager=manager
    def _format_card_description(self, card_info: Dict) -> str:
        """格式化卡牌描述供AI使用（支持多种升级数值格式）"""
        desc = card_info["description"]
        
        # 改进正则表达式，处理以下几种情况：
        # 1. "Deal 8(10) damage" → "Deal 8(10 after upgrading) damage"
        # 2. "Apply 2(3)Vulnerable" → "Apply 2(3 after upgrading)Vulnerable"
        # 3. "Gain 5(8)Block" → "Gain 5(8 after upgrading)Block"
        desc = re.sub(r'(\d+)\((\d+)\)', r'\1(\2 after upgrading)', desc)
        
        # 处理特殊效果描述（如多次升级数值）
        if "Apply" in desc and "Vulnerable" in desc:
            desc = desc.replace("Apply", "施加")
        if "Gain" in desc and "Block" in desc:
            desc = desc.replace("Gain", "获得").replace("Block", "格挡")
        
        return (f"『{card_info['name']}』\n"
                f"类型:{card_info['type']}({card_info['rarity']})\n"
                f"能耗:{card_info['cost']}\n"
                f"效果:{desc}")
    def _get_upgrade_comparison(self, card_info: Dict) -> str:
        """生成卡牌升级前后对比信息"""
        desc = card_info["description"]
        
        # 提取所有升级数值变化
        upgrades = re.findall(r'(\d+)\((\d+)\)', desc)
        comparison = []
        
        for original, upgraded in upgrades:
            diff = int(upgraded) - int(original)
            comparison.append(f"{original}→{upgraded}(+{diff})")
        
        return (f"{card_info['name']} - {card_info['type']} "
                f"[能耗:{card_info['cost']}]:\n"
                f"当前: {desc}\n"
                f"升级增强: {', '.join(comparison)}\n"
                f"类型: {card_info['rarity']}级{card_info['type']}")
    def handle(self, args: List[str]) -> None:
        """基于CAMEL-AI的休息决策（直接修改status）"""
        # 获取可升级卡牌列表
        card_kb = self.manager.card_knowledge
        upgradable_cards = []
        upgradable_cards_name =[]
        for card_name, is_upgraded in self.manager.data["deck"]:
            if not is_upgraded and card_name in card_kb:
                card_info = card_kb[card_name]
                print(card_name)
                # 获取详细的升级前后对比
                upgradable_cards_name.append(card_name)
                upgrade_analysis = self._get_upgrade_comparison(card_info)
                upgradable_cards.append((card_name, upgrade_analysis))
        # 构建更清晰的提示信息
        prompt_upgrade_options = "\n".join(
            f"{idx+1}. {details}" 
            for idx, (name, details) in enumerate(upgradable_cards)
        )
        # ===== 构建决策Prompt =====
        sys_prompt = """作为《杀戮尖塔》休息策略AI，请严格返回JSON：
    {
        "choice": "heal/upgrade",
        "target": "卡牌名字（仅升级时需要）", 
        "reasons": ["理由1", "理由2"]
        "extra": "如果没有可升级的卡牌，必须选择 heal"
    }"""
        
        prompt = {
            "system": f"{sys_prompt}",
            "status": {
                "health": f"{self.manager.data['health']}/{self.manager.data['max_health']}",
                "health_ratio": self.manager.data["health"] / self.manager.data["max_health"],
                "upgradable_cards": prompt_upgrade_options,
                "has_coffee_dripper": "Coffee Dripper" in self.manager.data["relics"]
            
            },
            "rules": [
                "在知识库文件中,a(b) 表示升级前数值是 a升级后是 b，"
                "默认治疗恢复30%最大生命（向上取整）",
                "Coffee Dripper遗物禁用治疗",
                "如果选择upgrade给出升级后的效果以及为什么优先级高，并给出你从知识库的第几行读取到的信息",
                "你必须去知识库里寻找每一张卡牌升级后的效果以此来判断"
            ]
        }

        # ===== 获取AI决策 =====
        response = self.manager.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
        raw_text = response.msg.content
        json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]  # Extract possible JSON portion
        decision = json.loads(json_str)
        print(raw_text)
        # ===== 执行操作 =====
        if decision["choice"] == "heal":
            if "Coffee Dripper" in self.manager.data["relics"]:
                raise ValueError("Coffee Dripper遗物禁用治疗")
                
            heal_amount = math.ceil(self.manager.data["max_health"] * 0.3)
            new_health = min(self.manager.data["health"] + heal_amount, self.manager.data["max_health"])
            self.manager.set_hp([str(new_health)])
            
        elif decision["choice"] == "upgrade":
            if decision["target"] not in upgradable_cards_name:
                raise ValueError(f"无法升级未持有卡牌: {decision['target']}")
            self.manager.handle_deck(["upgrade", decision["target"]])
        
        # ===== 打印决策结果 =====
        action = "治疗+30%" if decision["choice"] == "heal" else f"升级[{decision['target']}]"
        print(f"\n🔥 执行休息决策: {action}")
        print("📝 决策理由:")
        for i, reason in enumerate(decision["reasons"], 1):
            print(f" {i}. {reason}")
        print("✅ 状态更新完成")
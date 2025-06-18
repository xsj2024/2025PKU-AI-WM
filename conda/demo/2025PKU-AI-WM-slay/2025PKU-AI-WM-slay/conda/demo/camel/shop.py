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
class Shop:
    def __init__(self,manager):
        self.manager=manager
    def handle(self, args: List[str]) -> None:
        """基于CAMEL-AI的商店决策"""
        self.manager.data=self.manager.load_data()
        for _ in range(5):

            with open(SHOP_FILE, "r") as f:
                shop_data = json.load(f)
            sys_prompt = """作为《杀戮尖塔》购物顾问，请严格遵循：
            1. 必须返回如下JSON格式：
            {
                "choice": 1,2,…… ，按照 "index" 来返回
                "action": "buy/remove/skip",
                "item_type": "cards/relics/potions/none",
                "item_name": "物品名",
                "cost": 金额,
                "reasons": ["理由1", "理由2"], 
                "priority": "high/medium/low"
            }
            2. 请基于玩家的金币、遗物和卡组状况给出建议，别忘了你购买的金额要小于现有金额，并且从长远角度考虑不要把钱花光，当然如果有性价比极高的物品例外"""
        
        # 动态构建商品列表
            products = {
                "cards": [{"index":i[0],"name": i[1], "cost": i[2]} for i in shop_data.get("cards")],
                "relics": [{"index":i[0],"name": i[1], "cost": i[2]} for i in shop_data.get("relics")],
                "potions": [{"index":i[0],"name": i[1], "cost": i[2]} for i in shop_data.get("potions")],
                "remove_cost": {"index":shop_data["remove_cost"][0], "cost": shop_data["remove_cost"][1]},
                "leave": {"index":shop_data["leave"][0]}  
            }
            print(self.manager.data["gold"])
            prompt = {
                "system": sys_prompt,
                "player_status": {
                    "gold": self.manager.data["gold"],
                    "health": f"{self.manager.data['health']}/{self.manager.data['max_health']}",
                    "relics": self.manager.data["relics"],
                    "deck": [f"{c[0]}{'+' if c[1] else ''}" for c in self.manager.data["deck"]]
                },
                "shop_items": products,
                "strategic_rules": [
                    "优先购买能弥补当前卡组短板的卡牌",
                    "金币>250时考虑购买遗物", 
                    "血量危险时优先购买药水"
                ]
            }
            # ===== 调用CAMEL-AI模型 =====
            response = self.manager.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
            raw_text = response.msg.content
            
            json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
            decision = json.loads(json_str)
            # ===== 验证决策有效性 =====
            valid_actions = {"buy", "remove", "skip"}
            action=decision["action"]
            item_type=decision["item_type"]
            item_name=decision["item_name"]
            self.manager.data["gold"]=self.manager.data["gold"]-decision["cost"]
            if action not in valid_actions:
                raise ValueError(f"非法动作类型: {decision['action']}")
            self._print_shop_decision(
                action=decision["action"],
                item_type=decision["item_type"],
                item_name=decision.get("item_name"),
                cost=decision.get("cost", 0),
                reasons=decision["reasons"],
                priority=decision["priority"]
            )  
            if action=="skip": return decision["choice"]
            elif action=="buy" :
                with open(SHOP_FILE, "w") as f:
                    json.dump(shop_data, f, indent=2)
                if item_type=="cards" : 
                    self.manager.add_deck(item_name,"false")
                elif item_type=="relics" : 
                    self.manager.data["relics"].append(item_name)
                elif item_type=="potions" : 
                    self.manager.data["potions"].append(item_name)
            else: self.manager.del_deck(item_name)
            return decision["choice"]
            # ===== 专业输出面板 =====
    def remove(self, card_list: List[Tuple[str, str]]) -> str:
        """
        基于CAMEL-AI的删牌决策，输入为[(index, card_name), ...]，返回要删除的index（字符串）
        """
        # 构建删牌选项
        options = [
            {"index": idx, "name": name}
            for idx, name in card_list
        ]
        sys_prompt = """作为《杀戮尖塔》删牌顾问，请严格返回如下JSON格式：
        {
            "choice": "index",  // 你建议删除的卡牌的index
            "card_name": "卡牌名",
            "reasons": ["理由1", "理由2"]
        }
        你必须综合考虑卡组结构、卡牌强度和后续发展，优先删除负面或冗余卡牌。"""
        prompt = {
            "system": sys_prompt,
            "deck_cards": options,
            "strategic_rules": [
                "优先删除基础Strike/Defend等低价值卡",
                "避免删去关键combo卡",
                "如有负面卡优先删除"
            ]
        }
        response = self.manager.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
        raw_text = response.msg.content
        json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
        decision = json.loads(json_str)
        self._print_remove_decision(decision)
        return decision["choice"]

    def _print_remove_decision(self, decision: dict):
        print("\n✂️ 删牌决策 ".ljust(40, '='))
        print(f"建议删除: {decision['card_name']} (index: {decision['choice']})")
        print("理由：")
        for i, reason in enumerate(decision["reasons"], 1):
            print(f" {i}. {reason}")
        print("=" * 40)
    def _print_shop_decision(self, action: str, item_type: str, item_name: str, 
                            cost: int, reasons: list, priority: str):
        """商店决策可视化输出"""
        action_icon = {
            "buy": "🛍️", 
            "remove": "✂️",
            "skip": "🚶"
        }.get(action, "❓")
        
        print(f"\n{action_icon} 商店决策 ".ljust(40, '='))
        print(f"建议操作: {action.upper()} {item_name or '无'}")
        print(f"类型: {item_type.upper()} | 花费: {cost}金币 | 优先级: {priority.upper()}")
        print("\n决策依据:")
        for i, reason in enumerate(reasons[:3], 1):
            print(f" {i}. {reason}")
        print("=" * 40)
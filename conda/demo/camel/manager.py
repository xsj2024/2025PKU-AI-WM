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
INFO_DIR = "D:\\conda\\camel\\game_info"
STATUS_FILE = f"{DATA_DIR}/status.json"
CARD_KB_FILE = f"{INFO_DIR}/card_info.json"
SHOP_FILE = f"{DATA_DIR}/shop.json"
HISTORY_FILE = f"{DATA_DIR}/history.json"
class Manager:
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)

        self.model = self.initialize_model()
        self.data = self.load_data()
        self.sys_prompt = """You are an AI that analyzes the entire game of "Slay the Spire". Please provide movement, card selection, rest, and shop suggestions based on the following structured data:
        1. Must return JSON format
        2. Analysis factors should include: player health, relic effects, target node type priority
        3. Risk alerts need to be specifically explained"""
        self.agent = ChatAgent(
            system_message=self.sys_prompt,
            model=self.model,  # Use the model initialized during setup
            output_language="en"
        )
        with open(HISTORY_FILE, "w") as f:
            json.dump([], f)
        self.card_knowledge = self.load_card_knowledge()
        
    def initialize_model(self):
        """Initialize CAMEL-AI model"""
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type="deepseek-ai/DeepSeek-V3",
            url="https://api.siliconflow.cn/v1",
            model_config_dict={"max_tokens": 5000, "temperature": 0.2},
            api_key="sk-eieolvuyjgclelvomvzicesknimiywsdmdpksaalfxntcamc"
        )
    def load_card_knowledge(self) -> Dict[str, Dict]:
        """加载卡牌知识库，返回以卡牌名为键的字典"""
        if not os.path.exists(CARD_KB_FILE):
            return {}
        
        try:
            with open(CARD_KB_FILE, "r", encoding="utf-8") as f:
                cards = json.load(f)
                # 将数组转换为{name: card}的字典形式
                return {card["name"]: card for card in cards}
        except Exception as e:
            print(f"加载卡牌知识库失败: {str(e)}")
            return {}
    def load_data(self) -> Dict:
        """Load game data"""
        with open(STATUS_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    
    def save_data(self) -> None:
        """Save game data"""
        try:
            with open(STATUS_FILE, "w") as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"Failed to save data: {str(e)}")

    # === Basic operation methods ===
    def set_current(self, args: List[str]) -> None:
        """Set current node"""
        if len(args) < 1:
            print("Node ID required")
            return
            
        node = str(args[0])
        if node not in self.data["map"]:
            print(f"Invalid node ID: {node}")
            return
            
        self.data["current_node"] = node
        self.save_data()
        print(f"Current node set to: {node}")

    def set_hp(self, args: List[str]) -> None:
        """Set health value"""
        if len(args) < 1:
            print("Health value required")
            return
            
        try:
            value = int(args[0])
            max_hp = self.data["max_health"]
            
            if value < 0 or value > max_hp:
                print(f"Health must be between 0-{max_hp}")
                return
                
            self.data["health"] = value
            self.save_data()
            print(f"Health set to: {value}/{max_hp}")
        except ValueError:
            print("Please enter a valid integer")

    def set_maxhp(self, args: List[str]) -> None:
        if len(args) < 1:
            print("Maximum health value required")
            return
            
        try:
            value = int(args[0])
            if value <= 0:
                print("Maximum health must be positive")
                return
                
            # Automatically adjust current health cap
            self.data["health"] = min(self.data["health"], value)
            self.data["max_health"] = value
            self.save_data()
            print(f"Maximum health set to: {value} (current: {self.data['health']}/{value})")
        except ValueError:
            print("Please enter a valid integer")

    def set_gold(self, args: List[str]) -> None:
        if len(args) < 1:
            print("Gold amount required")
            return
            
        try:
            value = int(args[0])
            if value < 0:
                print("Gold amount cannot be negative")
                return
                
            self.data["gold"] = value
            self.save_data()
            print(f"Gold set to: {value}")
        except ValueError:
            print("Please enter a valid integer")
    def handle_deck(self, args: List[str]) -> None:
        """Handle card operations"""
        if len(args) < 2:
            print("Insufficient card operation parameters")
            return
            
        operation = args[0].lower()
        card_name = args[1]
        original_deck = [c[0] for c in self.data["deck"]]
        
        if operation == "add":
            self.add_deck(card_name, args[2])
        elif operation == "del":
            self.del_deck(card_name)
        elif operation == "upgrade":
            self.upgrade_deck(card_name)
        else:
            print("Invalid card operation type")
        self.record_history(
            action=f"deck_{operation}",
            item=card_name,
            details={"upgraded": args[2] if operation == "add" else None},
            before_state={"deck": original_deck},
            after_state={"deck": [c[0] for c in self.data["deck"]]}
        )

    def add_deck(self, card_name: str, if_upgraded :str) -> None:
        upgraded = if_upgraded.lower() == "true"
        self.data["deck"].append([card_name, upgraded])
        self.save_data()
        print(f"Added card: {card_name} (upgraded: {upgraded})")

    def del_deck(self, card_name: str) -> None:
        self.data["deck"] = [c for c in self.data["deck"] if c[0] != card_name]
        self.save_data()
        print(f"Removed card: {card_name}")

    def upgrade_deck(self, card_name: str) -> None:
        for card in self.data["deck"]:
            if card[0] == card_name:
                card[1] = True
                self.save_data()
                print(f"Upgraded card: {card_name}")
                return
        print(f"Card not found: {card_name}")
    def record_history(self, action: str, item: str, 
                    details: Dict, before_state: Dict, after_state: Dict) -> None:
        """记录操作历史"""
        try:
            with open(HISTORY_FILE, "r+", encoding="utf-8") as f:
                history = json.load(f)
                history.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": action,
                    "item": item,
                    "details": details,
                    "before": before_state,
                    "after": after_state,
                    "game_state": {
                        "current_node": self.data["current_node"],
                        "hp": f"{self.data['health']}/{self.data['max_health']}",
                        "gold": self.data["gold"]
                    }
                })
                f.seek(0)
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"记录历史失败: {str(e)}")
    def handle_relics(self, args: List[str]) -> None:
        if len(args) < 2:
            print("Insufficient relic operation parameters")
            return
            
        operation = args[0].lower()
        relic_name = args[1]
        before_relics = self.data["relics"].copy()
        if operation == "add":
            self.add_relics(relic_name)
        elif operation == "del":
            self.del_relics(relic_name)
        else:
            print("Invalid relic operation type")
        self.record_history(
            action=f"relic_{operation}",
            item=relic_name,
            details={},
            before_state={"relics": before_relics},
            after_state={"relics": self.data["relics"].copy()}
        )

    def add_relics(self, relic_name: str) -> None:
        if relic_name not in self.data["relics"]:
            self.data["relics"].append(relic_name)
            self.save_data()
            print(f"Added relic: {relic_name}")
        else:
            print(f"Relic already exists: {relic_name}")

    def del_relics(self, relic_name: str) -> None:
        if relic_name in self.data["relics"]:
            self.data["relics"].remove(relic_name)
            self.save_data()
            print(f"Removed relic: {relic_name}")
        else:
            print(f"Relic not found: {relic_name}")

    def handle_potions(self, args: List[str]) -> None:
        """Handle potion operations"""
        if len(args) < 2:
            print("Insufficient potion operation parameters")
            return
        operation = args[0].lower()
        potion_name = args[1]
        before_potions = self.data["potions"].copy()
        if operation == "add":
            self.add_potion(potion_name)
        elif operation == "del":
            self.del_potion(potion_name)
        else:
            print("Invalid potion operation type")
        self.record_history(
            action=f"potion_{operation}",
            item=potion_name,
            details={},
            before_state={"potions": before_potions},
            after_state={"potions": self.data["potions"].copy()}
        )

    def add_potions(self, potion_name: str) -> None:
        if potion_name not in self.data["potions"]:
            self.data["potions"].append(potion_name)
            self.save_data()
            print(f"Added potion: {potion_name}")
        else:
            print(f"Potion already exists: {potion_name}")

    def del_potions(self, potion_name: str) -> None:
        if potion_name in self.data["potions"]:
            self.data["potions"].remove(potion_name)
            self.save_data()
            print(f"Removed potion: {potion_name}")
        else:
            print(f"Potion not found: {potion_name}")

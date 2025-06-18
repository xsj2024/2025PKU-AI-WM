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
class GameManager:
    def __init__(self):
        # Ensure data directory exists
        os.makedirs(DATA_DIR, exist_ok=True)

        self.model = self.initialize_model()
        self.data = self.load_data()
        self.command_map = {
            # Existing manual commands
            "node": self._set_current_node,
            "health": self._set_health,
            "maxhp": self._set_max_health,
            "gold": self._set_gold,
            "card": self._handle_card_operation,
            "relic": self._handle_relic_operation,
            "potion": self._handle_potion_operation,
            # New AI commands
            "move": self._ai_move_decision,
            "shop": self._ai_shop_decision,
            "rest": self._ai_rest_decision,
            "chat": self._chat_with_ai,
            "exit": self._exit_game
        }        
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
    def _set_current_node(self, args: List[str]) -> None:
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

    def _set_health(self, args: List[str]) -> None:
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

    def _set_max_health(self, args: List[str]) -> None:
        """Set maximum health value"""
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

    def _set_gold(self, args: List[str]) -> None:
        """Set gold amount"""
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
    def _handle_card_operation(self, args: List[str]) -> None:
        """Handle card operations"""
        if len(args) < 2:
            print("Insufficient card operation parameters")
            return
            
        operation = args[0].lower()
        card_name = args[1]
        original_deck = [c[0] for c in self.data["deck"]]
        
        if operation == "add":
            self._handle_card_add_operation(card_name, args[2])
        elif operation == "del":
            self._handle_card_del_operation(card_name)
        elif operation == "upgrade":
            self._handle_card_upgrade_operation(card_name)
        else:
            print("Invalid card operation type")
        self._record_history(
            action=f"card_{operation}",
            item=card_name,
            details={"upgraded": args[2] if operation == "add" else None},
            before_state={"deck": original_deck},
            after_state={"deck": [c[0] for c in self.data["deck"]]}
        )

    def _handle_card_add_operation(self, card_name: str, if_upgraded :str) -> None:
        """Handle card add operation"""          
        upgraded = if_upgraded.lower() == "true"
        self.data["deck"].append([card_name, upgraded])
        self.save_data()
        print(f"Added card: {card_name} (upgraded: {upgraded})")

    def _handle_card_del_operation(self, card_name: str) -> None:
        """Handle card delete operation"""
        self.data["deck"] = [c for c in self.data["deck"] if c[0] != card_name]
        self.save_data()
        print(f"Removed card: {card_name}")

    def _handle_card_upgrade_operation(self, card_name: str) -> None:
        """Handle card upgrade operation"""
        for card in self.data["deck"]:
            if card[0] == card_name:
                card[1] = True
                self.save_data()
                print(f"Upgraded card: {card_name}")
                return
        print(f"Card not found: {card_name}")
    def _record_history(self, action: str, item: str, 
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
    def _handle_relic_operation(self, args: List[str]) -> None:
        """Handle relic operations"""
        if len(args) < 2:
            print("Insufficient relic operation parameters")
            return
            
        operation = args[0].lower()
        relic_name = args[1]
        before_relics = self.data["relics"].copy()
        if operation == "add":
            self._handle_relic_add_operation(relic_name)
        elif operation == "del":
            self._handle_relic_del_operation(relic_name)
        else:
            print("Invalid relic operation type")
        self._record_history(
            action=f"relic_{operation}",
            item=relic_name,
            details={},
            before_state={"relics": before_relics},
            after_state={"relics": self.data["relics"].copy()}
        )

    def _handle_relic_add_operation(self, relic_name: str) -> None:
        """Handle relic add operation"""
        if relic_name not in self.data["relics"]:
            self.data["relics"].append(relic_name)
            self.save_data()
            print(f"Added relic: {relic_name}")
        else:
            print(f"Relic already exists: {relic_name}")

    def _handle_relic_del_operation(self, relic_name: str) -> None:
        """Handle relic delete operation"""
        if relic_name in self.data["relics"]:
            self.data["relics"].remove(relic_name)
            self.save_data()
            print(f"Removed relic: {relic_name}")
        else:
            print(f"Relic not found: {relic_name}")

    def _handle_potion_operation(self, args: List[str]) -> None:
        """Handle potion operations"""
        if len(args) < 2:
            print("Insufficient potion operation parameters")
            return
            
        operation = args[0].lower()
        potion_name = args[1]
        before_potions = self.data["potions"].copy()
        if operation == "add":
            self._handle_potion_add_operation(potion_name)
        elif operation == "del":
            self._handle_potion_del_operation(potion_name)
        else:
            print("Invalid potion operation type")
        self._record_history(
            action=f"potion_{operation}",
            item=potion_name,
            details={},
            before_state={"potions": before_potions},
            after_state={"potions": self.data["potions"].copy()}
        )

    def _handle_potion_add_operation(self, potion_name: str) -> None:
        """Handle potion add operation"""
        if potion_name not in self.data["potions"]:
            self.data["potions"].append(potion_name)
            self.save_data()
            print(f"Added potion: {potion_name}")
        else:
            print(f"Potion already exists: {potion_name}")

    def _handle_potion_del_operation(self, potion_name: str) -> None:
        """Handle potion delete operation"""
        if potion_name in self.data["potions"]:
            self.data["potions"].remove(potion_name)
            self.save_data()
            print(f"Removed potion: {potion_name}")
        else:
            print(f"Potion not found: {potion_name}")


    # === AI decision methods ===
    def _ai_move_decision(self, args: List[str]) -> None:
        """CAMEL-AI based movement decision"""
        current_node = self.data["current_node"]
        available_nodes = self.data["map"][current_node]["next"]  # Use next field
        
        # ===== Build CAMEL-AI specific Prompt =====

        player_status = {
            "health": f"{self.data['health']}/{self.data['max_health']}",
            "gold": self.data["gold"],
            "relics": self.data["relics"],
            "potions": self.data["potions"]
        }
        
        # Dynamically build path options description
        path_options = []
        for node_id in available_nodes:
            node_data = self.data["map"][node_id]
            path_options.append({
                "node": node_id,
                "type": node_data["type"],
                "data": node_data.get("data", {})
            })
        
        prompt = {
            "system": self.sys_prompt,
            "task": "Choose optimal movement path",
            "input": {
                "current_node": current_node,
                "player_status": player_status,
                "path_options": path_options
            },
            "output_requirements": {
                "format": """{
                    "target": "node ID", 
                    "reasons": ["strategy reason 1", "strategy reason 2"],
                    "risk_assessment": "potential risk explanation"
                }""",
                "rules": [
                    "Prioritize rest nodes when health below 50%",
                    "Favor combat when having 'Burning Blood' relic",
                    "Prioritize shop when gold exceeds 200"
                ]
            }
        }

            # ===== Call CAMEL-AI model =====
        response = self.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
        raw_text = response.msg.content
        json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]  # Extract possible JSON portion
        decision = json.loads(json_str)
        print(response.msg.content)
        # ===== Visual output =====
        self._print_decision_panel(
            title="Path Decision",
            target=decision["target"],
            reasons=decision["reasons"],
            warning=decision.get("risk_assessment", "No significant risk")
        )
        
        # Automatically execute movement
        self._set_current_node([decision["target"]])

    def _print_decision_panel(self, title: str, target: str, reasons: list, warning: str):
        """Professional decision panel output"""
        border = "╔" + "═"*(len(title)+6) + "╗"
        print(f"\n{border}")
        print(f"║  {title.upper():^{len(title)+2}}  ║")
        print("╠" + "═"*(len(title)+6) + "╣")
        
        max_len = max(len(border), 40)  # Minimum width 40
        print(f"║ Target node: {target.ljust(max_len-15)} ║")
        print("╠" + "─"*(max_len-2) + "╣")
        
        for i, reason in enumerate(reasons[:3], 1):
            print(f"║ {i}. {reason.ljust(max_len-6)} ║")
        
        print("╠" + "─"*(max_len-2) + "╣")
        print(f"║ ! Risk warning: {warning.ljust(max_len-13)} ║")
        print("╚" + "═"*(max_len-2) + "╝")

    def _ai_shop_decision(self, args: List[str]) -> None:
        """基于CAMEL-AI的商店决策"""
        for _ in range(5):

            with open(SHOP_FILE, "r") as f:
                shop_data = json.load(f)
            sys_prompt = """作为《杀戮尖塔》购物顾问，请严格遵循：
            1. 必须返回如下JSON格式：
            {
                "action": "buy/remove/skip",
                "item_type": "cards/relics/potions/none",
                "item_name": "物品名",
                "cost": 金额,
                "reasons": ["理由1", "理由2"], 
                "priority": "high/medium/low"
            }
            2. 请基于玩家的金币、遗物和卡组状况给出建议"""
        
        # 动态构建商品列表
            products = {
                "cards": [{"name": i[0], "cost": i[1]} for i in shop_data.get("cards")],
                "relics": [{"name": i[0], "cost": i[1]} for i in shop_data.get("relics")],
                "potions": [{"name": i[0], "cost": i[1]} for i in shop_data.get("potions")],
                "remove_cost": shop_data.get("remove_cost")
            }
            prompt = {
                "system": sys_prompt,
                "player_status": {
                    "gold": self.data["gold"],
                    "health": f"{self.data['health']}/{self.data['max_health']}",
                    "relics": self.data["relics"],
                    "deck": [f"{c[0]}{'+' if c[1] else ''}" for c in self.data["deck"]]
                },
                "shop_items": products,
                "strategic_rules": [
                    "优先购买能弥补当前卡组短板的卡牌",
                    "金币>250时考虑购买遗物", 
                    "血量危险时优先购买药水"
                ]
            }
            # ===== 调用CAMEL-AI模型 =====
            response = self.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
            raw_text = response.msg.content
            
            json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
            decision = json.loads(json_str)
            # ===== 验证决策有效性 =====
            valid_actions = {"buy", "remove", "skip"}
            action=decision["action"]
            item_type=decision["item_type"]
            item_name=decision["item_name"]
            self.data["gold"]=self.data["gold"]-decision["cost"]
            if action not in valid_actions:
                raise ValueError(f"非法动作类型: {decision['action']}")
            if action=="skip": break
            elif action=="buy" :
                shop_data[item_type] = [c for c in shop_data[item_type] if c[0] != item_name]
                with open(SHOP_FILE, "w") as f:
                    json.dump(shop_data, f, indent=2)
                if item_type=="cards" : 
                    self._handle_card_add_operation(item_name,"false")
                elif item_type=="relics" : self.data["relics"].append(item_name)
                elif item_type=="potions" : self.data["potions"].append(item_name)
            else: self._handle_card_del_operation(item_name)
            self.save_data()
            # ===== 专业输出面板 =====
            self._print_shop_decision(
                action=decision["action"],
                item_type=decision["item_type"],
                item_name=decision.get("item_name"),
                cost=decision.get("cost", 0),
                reasons=decision["reasons"],
                priority=decision["priority"]
            )
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
    def _ai_rest_decision(self, args: List[str]) -> None:
        """基于CAMEL-AI的休息决策（直接修改status）"""
        # 获取可升级卡牌列表
        card_kb = self.card_knowledge
        upgradable_cards = []
        upgradable_cards_name =[]
        for card_name, is_upgraded in self.data["deck"]:
            if not is_upgraded and card_name in card_kb:
                card_info = card_kb[card_name]
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
        "extra": "你是否查阅了知识库文件，并输出升级的卡牌的升级后的费用和效果"
    }"""
        
        prompt = {
            "system": f"{sys_prompt}",
            "status": {
                "health": f"{self.data['health']}/{self.data['max_health']}",
                "health_ratio": self.data["health"] / self.data["max_health"],
                "upgradable_cards": prompt_upgrade_options,
                "has_coffee_dripper": "Coffee Dripper" in self.data["relics"]
            
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
        response = self.agent.step(json.dumps(prompt, indent=2, ensure_ascii=False))
        raw_text = response.msg.content
        json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]  # Extract possible JSON portion
        decision = json.loads(json_str)
        print(raw_text)
        # ===== 执行操作 =====
        if decision["choice"] == "heal":
            if "Coffee Dripper" in self.data["relics"]:
                raise ValueError("Coffee Dripper遗物禁用治疗")
                
            heal_amount = math.ceil(self.data["max_health"] * 0.3)
            new_health = min(self.data["health"] + heal_amount, self.data["max_health"])
            self._set_health([str(new_health)])
            
        elif decision["choice"] == "upgrade":
            if decision["target"] not in upgradable_cards_name:
                raise ValueError(f"无法升级未持有卡牌: {decision['target']}")
            self._handle_card_operation(["upgrade", decision["target"]])
        
        # ===== 打印决策结果 =====
        action = "治疗+30%" if decision["choice"] == "heal" else f"升级[{decision['target']}]"
        print(f"\n🔥 执行休息决策: {action}")
        print("📝 决策理由:")
        for i, reason in enumerate(decision["reasons"], 1):
            print(f" {i}. {reason}")
        print("✅ 状态更新完成")


    def _print_rest_decision(self, choice: str, target: str, reasons: list, advice: str):
        """休息决策可视化输出"""
        icon = "❤️" if choice == "heal" else "🔧"
        title = f" 休息决策: {choice.upper()} {target} "
        
        print(f"\n{icon}{title}".ljust(40, '-'))
        print("决策因素:")
        for i, reason in enumerate(reasons[:2], 1):
            print(f" {i}. {reason}")
        print(f"\n建议: {advice or '无特别建议'}")
        print("-" * 40)

    def _exit_game(self, args: List[str]) -> None:
        """Exit game"""
        self.save_data()
        print("Game data saved, goodbye!")
        sys.exit(0)

    def show_help(self) -> None:
        """Show help information"""
        help_text = """
        █ Command Manual █████████████████████████████
        
        [Basic commands]
          node <id>        - Set current node
          health <value>   - Set health value (0-MAX)
          maxhp <value>    - Set maximum health value
          gold <value>     - Set gold amount
        
        [Card management]
          card ins <name> <true/false> - Add card
          card del <name>             - Delete card
          card upgrade <name>         - Upgrade card
        
        [Relic/Potion]
          relic add <name> - Add relic
          relic del <name> - Delete relic
          potion add <name> - Add potion
          potion del <name> - Delete potion
        
        [AI Decisions]
          move  - Recommended movement path
          shop  - Shop purchase suggestions
          rest  - Rest strategy  
          chat  - 与AI进行策略对话
        
        exit   - Save and exit game
        ████████████████████████████████████
        """
        print(help_text)
    def _chat_with_ai(self, args: List[str] = None) -> None:
        """与游戏AI进行自由对话 (输入'chat'指令触发)"""
        # 初始化对话系统
        chat_agent = ChatAgent(
            system_message="""你作为《杀戮尖塔》游戏AI助手，需同时具备：
    1. 游戏策略顾问功能（根据当前游戏数据给出建议）
    2. 自然对话能力（回答玩家各类问题）
    当前游戏状态：
    - 楼层：{floor}
    - 血量：{health}
    - 金币：{gold}
    - 遗物：{relics}
    - 卡组：{deck_size}张卡牌
    """.format(
                floor=self.data.get("current_floor", "未知"),
                health=f"{self.data['health']}/{self.data['max_health']}",
                gold=self.data["gold"],
                relics=", ".join(self.data["relics"]) or "无",
                deck_size=len(self.data["deck"])
            ),
            model=self.model,
            output_language="en"
        )
        
        print("\n💬 进入对话模式（输入'exit'退出）".center(50, '='))
        while True:
            try:
                user_input = input("\n[玩家] > ").strip()
                if user_input.lower() in ('exit', '退出', 'q'):
                    break
                    
                # 智能判断输入类型
                if any(keyword in user_input for keyword in ["建议", "怎么办", "策略"]):
                    response = chat_agent.step(
                        f"玩家请求策略建议，请根据当前游戏状态分析。玩家问题：{user_input}"
                    )
                else:
                    response = chat_agent.step(user_input)
                    
                # 美化AI回复
                self._format_ai_response(response.msg.content)
                
            except KeyboardInterrupt:
                print("\n⚠️ 中断对话")
                break
            except Exception as e:
                print(f"\n⚠️ 对话出错: {str(e)}")
    def _format_ai_response(self, raw_text: str) -> None:
        """美化AI回复的显示格式"""
        # 提取可能存在的JSON建议部分
        if "{" in raw_text and "}" in raw_text:
            json_str = raw_text[raw_text.find("{"):raw_text.rfind("}")+1]
            try:
                advice = json.loads(json_str)
                print("\n🔍 策略分析结果：")
                for k, v in advice.items():
                    print(f"  {k}: {v}")
                return
            except:
                pass
        
        # 普通对话处理
        lines = raw_text.split('\n')
        print('\n[AI] ' + '\n     '.join(lines))
    def main(self) -> None:
        """Main loop"""
        print("=== Spire Climb Decision System ===")
        
        while True:
            try:
                # Show current status
                status = self.data
                print(f"\nCurrent position: Node {status['current_node']} | Health: {status['health']}/{status['max_health']} | Gold: {status['gold']}")
                print(f"Relics: {', '.join(status['relics']) or 'None'}")
                print(f"Potions: {', '.join(status['potions']) or 'None'}")
                print(f"Deck: {', '.join(c[0] + ('+' if c[1] else '') for c in status['deck']) or 'None'}")
                
                # Get input
                cmd_input = input("\n▶ Enter command (help for manual): ").strip().split()
                if not cmd_input:
                    continue
                    
                cmd = cmd_input[0].lower()
                args = cmd_input[1:]
                
                if cmd == "help":
                    self.show_help()
                elif cmd in self.command_map:
                    self.command_map[cmd](args)
                else:
                    print("Invalid command! Enter 'help' for manual")
                    
            except KeyboardInterrupt:
                self._exit_game([])
            except Exception as e:
               

                print(f"错误: {str(e)}")


if __name__ == "__main__":
    GameManager().main()

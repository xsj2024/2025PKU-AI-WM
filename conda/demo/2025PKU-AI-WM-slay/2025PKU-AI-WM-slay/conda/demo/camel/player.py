import os
import re
import json
import sys
from typing import Dict, List, Set, Optional
from enum import Enum
from datetime import datetime
from dotenv import load_dotenv
from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType


# 文件路径常量
STATUS_FILE = "./game_data/status.json"
SHOP_FILE = "./game_data/status.json"

class GameManager:
    def __init__(self):
        self.model = self.initialize_model()
        self.data = self.load_data()
        self.command_map = {
            # 原有手动指令
            "node": self._set_current_node,
            "health": self._set_health,
            "maxhp": self._set_max_health,
            "gold": self._set_gold,
            "card": self._handle_card_operation,
            "relic": self._handle_relic_operation,
            "potion": self._handle_potion_operation,
            # 新增AI指令
            "move": self._ai_move_decision,
            "shop": self._ai_shop_decision,
            "rest": self._ai_rest_decision,
            "exit": self._exit_game
        }
        
    def initialize_model(self):
        """初始化CAMEL-AI模型"""
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type="deepseek-ai/DeepSeek-V3",
            url="https://api.siliconflow.cn/v1",
            model_config_dict={"max_tokens": 5000, "temperature": 0.2},
            api_key="sk-eieolvuyjgclelvomvzicesknimiywsdmdpksaalfxntcamc"
        )
    
    def load_data(self):
        """加载游戏数据"""
        try:
            with open(STATUS_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "current_node": "1",
                "health": 72,
                "max_health": 80,
                "gold": 120,
                "relics": ["Burning Blood", "Tiny Chest"],
                "potions": ["Fire Potion"],
                "deck": [["Strike", False], ["Defend", False]],
                "map": {
                    "1": {"edges": ["2", "3"], "type": "monster"},
                    "2": {"edges": ["4"], "type": "shop"},
                    "3": {"edges": ["4"], "type": "rest"},
                    "4": {"edges": [], "type": "elite"}
                }
            }
    
    def save_data(self):
        """保存游戏数据"""
        with open(STATUS_FILE, "w") as f:
            json.dump(self.data, f, indent=2)
            
    # --- 基础操作方法 ---
    def _set_current_node(node):
        """修改 current_node"""
        data = load_data()
        data["current_node"] = str(node)  # 强制转换为字符串
        save_data(data)
        print(f"Set current_node: {node}")
    def _set_health(value):
        """修改 health（范围 0~max_health）"""
        data = load_data()
        value = int(value)
        max_hp = data["max_health"]
        if value < 0 or value > max_hp:
            print(f"Health must be between 0 and {max_hp}")
            return
        data["health"] = value
        save_data(data)
        print(f"Set health: {value}/{max_hp}")
    def _set_max_health(value):
        """修改 max_health（同步调整 health 上限）"""
        data = load_data()
        value = int(value)
        if value <= 0:
            print("Max health must be positive")
            return
        # 如果当前 health 超过新 max_health，则截断
        data["health"] = min(data["health"], value)
        data["max_health"] = value
        save_data(data)
        print(f"Set max_health: {value} (health now {data['health']}/{value})")
    def _set_gold(value):
        """修改 gold（不允许负数）"""
        data = load_data()
        value = int(value)
        if value < 0:
            print("Gold cannot be negative")
            return
        data["gold"] = value
        save_data(data)
        print(f"Set gold: {value}")
    
    def _upgrade_card(self, name):
        for card in self.data["deck"]:
            if card[0] == name and not card[1]:
                card[1] = True
                self.save_data()
                return True
        return False
    
    def _add_relic(self, name):
        if name not in self.data["relics"]:
            self.data["relics"].append(name)
            self.save_data()
            return True
        return False
    
    def _heal(self, amount):
        max_hp = self.data["max_health"]
        self.data["health"] = min(max_hp, self.data["health"] + amount)
        self.save_data()
    
    # --- AI决策方法 ---
    def move_decision(self):
        """增强版移动决策-带详细理由"""
        current = self.data["current_node"]
        available_nodes = self.data["map"][current]["edges"]
        
        prompt = f"""
        ██ 移动决策 ███████████████████████████████
        当前节点：{current}（{self.data['map'][current]['type']}）
        可用路径：{', '.join(f'{n}[{self.data["map"][n]["type"]}]' for n in available_nodes)}
        
        玩家状态：
        - 生命：{self.data['health']}/{self.data['max_health']}
        - 金币：{self.data['gold']}
        - 遗物：{', '.join(self.data['relics']) or '无'}
        - 卡组强度：{len(self.data['deck'])}张卡
        
        决策要求：
        1. 评估当前状态是否适合挑战精英/商店
        2. 若生命值低优先选择休息点
        3. 根据卡组强度判断是否需要商店
        
        请按以下JSON格式回应：
        {{
            "target_node": "选择的目标节点ID",
            "reason": [
                "当前生命值较低(72/80)，需要治疗",
                "卡组缺少AOE能力，需要商店补充",
                "2号节点是安全路线"
            ],
            "danger_warning": "可能遇到的危险提示"
        }}
        """
        
        response = self.model.run(prompt)
        decision = json.loads(response)
        
        # 格式化输出决策理由
        print("\n╔══════ AI移动决策 ══════╗")
        print(f"║ 目标: 节点 {decision['target_node']} ({self.data['map'][decision['target_node']]['type']})")
        print("╠══════ 决策理由 ══════╣")
        for i, reason in enumerate(decision["reason"], 1):
            print(f"║ {i}. {reason}")
        print(f"╠══════ 警告 ═════════╣")
        print(f"║ ! {decision['danger_warning']}")
        print("╚═══════════════════════╝")
        
        self._set_current_node(decision["target_node"])

    def shop_decision(self):
        """增强版商店决策-带购物分析"""
        with open(SHOP_FILE, "r") as f:
            shop_data = json.load(f)
        
        prompt = f"""
        ██ 商店决策 ███████████████████████████████
        可用金币：{self.data['gold']}
        
        商品清单：
        [卡牌] {', '.join(f"{n}({p})" for n,p in shop_data['cards'])}
        [遗物] {', '.join(f"{n}({p})" for n,p in shop_data['relics'])}
        [药水] {', '.join(f"{n}({p})" for n,p in shop_data['potions'])}
        [删卡] 费用：{shop_data['remove_card_cost']}
        
        当前卡组：{', '.join(c[0]+('+' if c[1] else '') for c in self.data['deck'])}
        
        决策要求：
        1. 优先补足卡组短板（防御/攻击）
        2. 高价值遗物优先考虑
        3. 剩余金币保留给后续关卡
        
        请按以下JSON格式回应：
        {{
            "action": "buy/remove/leave",
            "type": "card/relic/potion/none",
            "item": "物品名称",
            "cost": 花费金额,
            "analysis": [
                "当前卡组攻击卡占比60%",
                "火焰遗物与燃烧血协同性好",
                "删卡费用过高(75)，性价比低"
            ],
            "final_reason": "综合上述因素的最终决策依据"
        }}
        """
        
        response = self.model.run(prompt)
        decision = json.loads(response)
        
        # 彩色终端输出
        COLORS = {"buy": "\033[92m", "remove": "\033[93m", "leave": "\033[91m"}
        print(f"\n{COLORS[decision['action']]}🛒 商店决策报告 🛒")
        print(f"▶ 最终动作: {decision['action'].upper()} {decision.get('item','')}")
        print(f"▶ 花费: {decision.get('cost',0)}金币")
        print("🔍 决策分析:")
        for point in decision["analysis"]:
            print(f"  • {point}")
        print(f"📌 结论: {decision['final_reason']}\033[0m")
        
        # 实际执行操作
        if decision["action"] == "buy" and decision["cost"] <= self.data["gold"]:
            self._set_gold(self.data["gold"] - decision["cost"])
            # ...执行购买操作
    def show_help(self):
        """显示完整指令帮助（包含新旧指令）"""
        print("\n█ 指令手册 █████████████████████████████")
        print("\n[手动操作指令]")
        print("  node <id>                - 设置当前节点")
        print("  health <value>           - 设置生命值")
        print("  maxhp <value>            - 设置最大生命值")
        print("  gold <value>             - 设置金币")
        print("  card ins <name> <true/false> - 添加卡牌")
        print("  card del <name> <true/false> - 删除卡牌")
        print("  card upgrade <name>      - 升级卡牌")
        print("  relic add <name>         - 添加遗物")
        print("  relic del <name>         - 删除遗物")
        print("  potion add <name>        - 添加药水")
        print("  potion del <name>        - 删除药水")
        
        print("\n[AI决策指令]")
        print("  move                     - AI推荐移动路线")
        print("  shop                     - AI商店购物建议")
        print("  rest                     - AI休息点策略")
        print("  exit                     - 退出系统")
        print("█ 注意：AI指令会显示详细决策过程 █")
    def rest_decision(self):
        """增强版休息决策-带恢复策略"""
        heal_amount = int(self.data["max_health"] * 0.3)
        upgradable = [c[0] for c in self.data["deck"] if not c[1]]
        
        prompt = f"""
        ██ 休息决策 ███████████████████████████████
        当前生命：{self.data['health']}/{self.data['max_health']}
        可恢复量：+{heal_amount}
        可升级卡：{', '.join(upgradable) or '无'}
        
        决策矩阵：
        - 生命<50% → 强制休息
        - 有关键卡可升级 → 优先升级
        - 准备精英战 → 保持满血
        
        请按以下JSON格式回应：
        {{
            "action": "rest/upgrade",
            "target": "卡牌名称或治疗量",
            "priority_factors": {{
                "health_priority": "低/中/高",
                "upgrade_value": "卡牌升级价值评估",
                "next_node_type": "下个节点类型影响"
            }},
            "step_by_step_reasoning": [
                "首先评估生命值(72/80)处于安全范围",
                "防御+卡牌可以降低精英战伤害20%",
                "下一节点是商店无需保留金币"
            ]
        }}
        """
        
        response = self.model.run(prompt)
        decision = json.loads(response)
        
        # 表格化输出
        print("\n🏥 休息点决策分析".center(40, '='))
        print(f"| {'因素':<15} | {'评估':<20} |")
        print("|-----------------|----------------------|")
        print(f"| 生命状态       | {decision['priority_factors']['health_priority']:<20} |")
        print(f"| 升级价值       | {decision['priority_factors']['upgrade_value']:<20} |")
        print(f"| 下一节点       | {decision['priority_factors']['next_node_type']:<20} |")
        print("="*40)
        print("\n推理过程：")
        for step in decision["step_by_step_reasoning"]:
            print(f"→ {step}")
        print(f"\n最终选择：{decision['action']} -> {decision['target']}")
    def main(self):
        self.show_help()
        while True:
            try:
                cmd = input("\n▶ 输入指令: ").strip().split()
                if not cmd:
                    continue
                    
                # 处理特殊指令
                if cmd[0] == "help":
                    self.show_help()
                    continue
                    
                # 执行映射指令
                if cmd[0] in self.command_map:
                    self.command_map[cmd[0]](cmd[1:])
                else:
                    print(f"无效指令！输入 'help' 查看可用指令")
                    
            except Exception as e:
                print(f"执行错误: {str(e)}")


if __name__ == "__main__":
    game = GameManager()
    game.main()

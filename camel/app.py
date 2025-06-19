from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from dotenv import load_dotenv
import json
import os
import re
import time
import random
import sys
import asyncio
import threading

# ===== 打字机效果函数 =====
def typewriter_print(text, delay=0.03):
    """以打字机效果打印文本"""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        # 对中文和标点使用更短延迟
        if char in ['，', '。', '！', '？', '：', '；', '「', '」']:
            time.sleep(delay * 0.7)
        elif '\u4e00' <= char <= '\u9fff':  # 中文字符范围
            time.sleep(delay * 0.8)
        else:
            time.sleep(delay)
    print()

# ===== 初始化配置 =====
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))
typewriter_print(f"✅ Python版本: {sys.version}")
typewriter_print(f"✅ 工作目录: {current_dir}")

# 检查环境变量
if not os.getenv("SILICONFLOW_API_KEY"):
    typewriter_print("❌ 错误: 环境变量 SILICONFLOW_API_KEY 未配置")
    sys.exit(1)

# ===== 模型初始化 =====
def initialize_model():
    try:
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type="deepseek-ai/DeepSeek-V3",
            url="https://api.siliconflow.cn/v1",
            model_config_dict={"max_tokens": 5000, "temperature": 0.1},
            api_key=os.getenv("SILICONFLOW_API_KEY")
        )
    except Exception as e:
        typewriter_print(f"🚨 模型启动失败: {e}")
        sys.exit(1)

battle_model = initialize_model()
typewriter_print("✅ AI模型已初始化")

# ===== 知识库加载 =====
KNOWLEDGE_FILE = os.path.join("game_data", "knowledge.txt")

def load_strategy_knowledge() -> str:
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return "\n".join([line.strip() for line in f.readlines()])
    except FileNotFoundError:
        typewriter_print(f"⚠️ 知识库文件 {KNOWLEDGE_FILE} 未找到，加载默认策略")
        return "优先攻击血量最低且有易伤状态的敌人"

# ===== 游戏状态加载 =====
STATUS_FILE = os.path.join("game_data", "status.json")

def load_game_status() -> dict:
    default = {
        "player_status": {
            "energy": "3/3",
            "health": "68/75", 
            "block": 12,
            "statuses": {"Weak": 0, "Vulnerable": 0},
            "hand": [
                {"name": "Strike", "type": "Attack", "cost": 1, "effect": "造成6点伤害"},
                {"name": "Defend", "type": "Skill", "cost": 1, "effect": "获得5点格挡"}
            ]
        },
        "enemies": [
            {"name": "敌兵A", "health": "25/30", "block": 0, "intent": "攻击", "statuses": {}}
        ]
    }
    
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        typewriter_print(f"⚠️ 状态文件 {STATUS_FILE} 未找到，创建默认状态")
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default, f, indent=2)
        return default
    except Exception as e:
        typewriter_print(f"⚠️ 加载状态失败: {str(e)}, 使用默认状态")
        return default

class GameSession:
    """管理整个游戏会话的持久化记忆"""
    
    def __init__(self):
        # 加载并嵌入知识库到系统提示
        self.knowledge = load_strategy_knowledge()
        system_prompt = (
            f"作为《Slay the Spire》指令生成器，严格遵守：\n"
            f"1. 输出格式：〖卡牌名称 -> 目标〗或〖卡牌名称〗\n"
            f"2. 括号内说明原因（原因：...）\n"
            f"3. 优先考虑能量消耗\n"
            f"4. 攻击卡必须指定目标\n\n"
            f"【战略知识库】\n{self.knowledge}"
        )
        
        # 创建持久化的ChatAgent
        self.agent = ChatAgent(
            system_message=system_prompt,
            model=battle_model,
            output_language="zh"
        )
        
        # 记忆状态
        self.round_count = 0
        self.decision_history = []  # 存储历史决策
        typewriter_print("✅ 游戏会话初始化 (持久化记忆)")
        typewriter_print(f"• 知识库加载: {len(self.knowledge)}字符")

    def add_decision_history(self, command: str, reasoning: str):
        """添加历史决策到记忆"""
        self.round_count += 1
        self.decision_history.append({
            "round": self.round_count,
            "command": command,
            "reasoning": reasoning
        })
        # 只保留最近3条历史记录
        if len(self.decision_history) > 3:
            self.decision_history.pop(0)

    def build_current_prompt(self, game_state: dict) -> str:
        """构建包含记忆的当前回合提示"""
        # 玩家状态
        player = game_state["player_status"]
        player_info = (
            f"【玩家状态】\n"
            f"- 生命: {player['health']} | 能量: {player['energy']}\n"
            f"- 格挡: {player['block']} | 状态: {player['statuses']}\n"
            f"- 手牌:\n"
        )
        for i, card in enumerate(player["hand"], 1):
            player_info += f"  {i}. {card['name']} ({card['type']}, 消耗:{card['cost']})"
            if 'effect' in card:
                player_info += f" - {card['effect']}"
            player_info += "\n"
        
        # 敌人状态
        enemies_info = "\n【敌人状态】"
        for i, enemy in enumerate(game_state["enemies"]):
            enemies_info += (
                f"\n{i+1}. {enemy['name']}:\n"
                f"  - 生命: {enemy['health']}, 格挡: {enemy['block']}\n"
                f"  - 意图: {enemy['intent']}, 状态: {enemy['statuses']}\n"
            )
        
        # 历史记忆
        history_section = ""
        if self.decision_history:
            history_section = "\n【历史决策】"
            for decision in self.decision_history:
                history_section += f"\n回合 {decision['round']}: {decision['command']}"
                history_section += f"\n  原因: {decision['reasoning']}"
        
        return (
            f"=== 回合 #{self.round_count+1} ===\n"
            f"{player_info}"
            f"{enemies_info}"
            f"{history_section}"
            "\n\n请生成当前回合的最佳指令！"
        )
# ===== 使用 ChatAgent 实现决策逻辑 =====
class BattleCommander:
    SYSTEM_PROMPT = """作为《Slay the Spire》指令生成器，严格遵守：
1. 输出格式必须是：〖卡牌名称 -> 目标〗或者〖卡牌名称〗
2. 必须在括号内说明选择原因（原因：...）
3. 必须考虑卡牌消耗不能超过当前能量
4. 攻击卡牌必须指定目标"""

    def __init__(self):
        # 创建游戏会话（包含持久化ChatAgent）
        self.session = GameSession()
        typewriter_print("✅ 战斗指挥官初始化 (带记忆功能)")

    def _current_energy(self, status: dict) -> int:
        energy_str = status["player_status"]["energy"]
        return int(energy_str.split('/')[0]) if isinstance(energy_str, str) else energy_str
    
    def _build_user_prompt(self, status: dict) -> str:
        player = status["player_status"]
        enemies = status["enemies"]
        
        # 构建玩家状态描述
        player_desc = (
            f"【玩家状态】\n"
            f"- 生命值: {player['health']}\n"
            f"- 格挡值: {player['block']}\n"
            f"- 可用能量: {player['energy']}\n"
        )
        
        # 添加状态效果
        if 'statuses' in player:
            player_desc += f"- 状态效果: "
            effects = []
            for effect, value in player['statuses'].items():
                effects.append(f"{effect}({value})")
            player_desc += ", ".join(effects) + "\n"
            
        # 添加手牌信息
        player_desc += f"- 手牌:\n"
        for i, card in enumerate(player["hand"], 1):
            player_desc += f"  {i}. {card['name']} - 类型: {card['type']}, 消耗: {card['cost']}点"
            if 'effect' in card:
                player_desc += f", 效果: {card['effect']}"
            player_desc += "\n"
        
        # 构建敌人状态描述
        enemies_desc = "\n【敌人状态】"
        for i, enemy in enumerate(enemies, 1):
            enemies_desc += (
                f"\n敌人{i} - {enemy.get('name', f'敌兵{i}')}:\n"
                f"- 生命值: {enemy['health']}\n"
                f"- 格挡值: {enemy['block']}\n"
                f"- 意图: {enemy['intent']}\n"
            )
            if 'statuses' in enemy:
                enemies_desc += f"- 状态效果: "
                effects = []
                for effect, value in enemy['statuses'].items():
                    effects.append(f"{effect}({value})")
                enemies_desc += ", ".join(effects) + "\n"
        
        # 构建完整提示
        prompt = (
            f"{player_desc}\n"
            f"{enemies_desc}\n\n"
            f"【战略知识库】\n{self.knowledge}\n\n"
            f"当前可用能量: {self._current_energy(status)}点\n\n"
            "请生成最佳指令！"
        )
        
        return prompt

    def generate_command(self) -> str:
        """生成基于记忆的指令"""
        # 加载当前状态
        game_state = load_game_status()
        typewriter_print(f"🔁 回合 #{self.session.round_count+1} 状态已加载")
        
        # 特殊情况处理：无敌人或能量不足
        if not game_state["enemies"]:
            typewriter_print("🛑 战场无敌人，结束回合")
            return "〖结束回合〗"
        
        # 构建用户提示（包含历史记忆）
        user_prompt = self.session.build_current_prompt(game_state)
        typewriter_print(f"📝 提示已构建 ({len(user_prompt)}字符)")
        
        # 创建用户消息
        user_msg = BaseMessage.make_user_message(
            role_name="玩家", content=user_prompt)
        
        # 添加思考动画
        stop_animation = False
        animation_thread = threading.Thread(
            target=self._show_thinking_animation, 
            args=("AI思考中...", lambda: stop_animation)
        )
        animation_thread.daemon = True
        animation_thread.start()
        
        # 发送请求
        start_time = time.time()
        try:
            agent_response = self.session.agent.step(user_msg)
            stop_animation = True
            animation_thread.join()
            
            ai_content = agent_response.msgs[0].content
            response_time = time.time() - start_time
            
            typewriter_print(f"\033[36m🤖 AI响应 (耗时{response_time:.1f}s)\033[0m")
            return self._process_response(ai_content, game_state)
                
        except Exception as e:
            stop_animation = True
            animation_thread.join()
            typewriter_print(f"🔥 请求失败: {str(e)}")
            return self.fallback_command(game_state)
    
    def _process_response(self, response: str, game_state: dict) -> str:
        """处理AI响应并添加到记忆"""
        # 提取指令
        pattern = r"〖([^〗]+?)(?:\s*->\s*([^〗]+?))?〗"
        if match := re.search(pattern, response):
            card_name = match.group(1).strip()
            target = match.group(2).strip() if match.group(2) else None
            
            # 提取原因
            reasoning = "未说明原因"
            if reason_match := re.search(r"原因[:：]\s*(.+)", response):
                reasoning = reason_match.group(1).strip()
            
            # 添加到历史记忆
            command = f"〖{card_name}->{target}〗" if target else f"〖{card_name}〗"
            self.session.add_decision_history(command, reasoning)
            
            typewriter_print(f"\033[33m📝 新记忆: 回合 {self.session.round_count} - {command}\033[0m")
            typewriter_print(f"\033[33m  原因: {reasoning}\033[0m")
            return command
        
        typewriter_print("⚠️ 未检测到有效指令格式，使用回退策略")
        return self.fallback_command(game_state)
    
    def _show_thinking_animation(self, message, stop_flag):
        """显示思考动画"""
        symbols = ['●', '◇', '◆', '■', '□', '▲', '△', '▽', '▼']
        i = 0
        while not stop_flag():
            sys.stdout.write(f"\r{message} {symbols[i % len(symbols)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write("\r" + " " * 50 + "\r")  # 清理动画行

    # === 结果验证与处理 ===
    def _validate_response(self, text: str, status: dict) -> str:
        typewriter_print("\n🔍 验证AI响应...")
        
        # 获取所有敌人的真实名称列表
        enemy_names = [e.get("name", f"敌兵{i+1}") for i, e in enumerate(status["enemies"])]
        
        # 尝试不同的指令格式匹配模式
        patterns = [
            # 格式1: 〖卡牌名称 -> 目标〗 (原因: ...)
            r"〖([^〗]+?)\s*->\s*([^〗]+?)〗\s*(?:（|$)\s*原因：(.+?)\s*(?:）|$)",
            # 格式2: 〖卡牌名称〗 (原因: ...)
            r"〖([^〗]+?)〗\s*(?:（|$)\s*原因：(.+?)\s*(?:）|$)",
            # 格式3: 简化的指令格式
            r"〖([^〗]+?)(?:\s*->\s*([^〗]+?))?〗"
        ]
        
        for pattern in patterns:
            if match := re.search(pattern, text, re.DOTALL | re.IGNORECASE):
                card_name = match.group(1).strip()
                # 提取目标字符串
                target_str = match.group(2).strip() if len(match.groups()) > 2 and match.group(2) else None
                reasoning = match.group(3).strip() if len(match.groups()) > 3 and match.group(3) else ""
                
                # 处理目标映射逻辑
                target = None
                if target_str:
                    # 情况1: 目标直接是敌人的名称 (如 "Maw Worm")
                    if target_str in enemy_names:
                        target = target_str
                    # 情况2: 目标使用索引形式 (如 "敌人1"、"敌兵2")
                    elif re.match(r'^敌(人|兵)\d+$', target_str):
                        try:
                            # 提取数字索引
                            index = int(re.search(r'\d+', target_str).group()) - 1
                            if 0 <= index < len(enemy_names):
                                target = enemy_names[index]
                        except Exception:
                            pass
                
                if reasoning:
                    typewriter_print(f"\033[33m🧠 模型决策逻辑：{reasoning}\033[0m")
                
                # 检查卡牌是否存在于手牌中
                current_energy = self._current_energy(status)
                available_cards = [card["name"] for card in status["player_status"]["hand"]]
                
                if card_name not in available_cards:
                    typewriter_print(f"⚠️ 无效卡牌 '{card_name}'，可用卡牌: {', '.join(available_cards)}")
                    break  # 退出模式匹配循环
                
                # 获取卡牌信息
                card_info = next(card for card in status["player_status"]["hand"] if card["name"] == card_name)
                
                # 检查能量是否足够
                if card_info["cost"] > current_energy:
                    typewriter_print(f"⚠️ 能量不足: {card_name}需要{card_info['cost']}点能量, 当前仅{current_energy}点")
                    break
                
                # 如果是攻击牌，检查目标是否有效
                if "Attack" in card_info.get("type", "") and not target and enemy_names:
                    target = enemy_names[0]
                    typewriter_print(f"⚠️ 攻击卡需要指定目标，将使用默认目标: {target}")
                elif "Attack" in card_info.get("type", "") and not enemy_names:
                    typewriter_print("⚠️ 攻击卡需要指定目标，但战场无敌人")
                
                # 如果是攻击牌且有目标，验证目标是否存在
                if target and "Attack" in card_info.get("type", ""):
                    if target not in enemy_names:
                        typewriter_print(f"⚠️ 无效目标 '{target}'，有效目标: {', '.join(enemy_names)}")
                        if enemy_names:
                            target = enemy_names[0]
                            typewriter_print(f"    使用默认目标: {target}")
                        else:
                            target = None
                
                # 构建指令
                if target:
                    command = f"〖{card_name}->{target}〗"
                else:
                    command = f"〖{card_name}〗"
                
                typewriter_print(f"\033[32m✅ 验证通过: {command}\033[0m")
                return command
        
        typewriter_print(f"⚠️ 无法识别响应格式：{text[:100]}...")
        return self.fallback_command(status)

    def fallback_command(self, status: dict) -> str:
        typewriter_print("⚠️ 使用回退策略选择卡片")
        player_status = status["player_status"]
        enemies = status["enemies"]
        
        current_energy = self._current_energy(status)
        available_cards = player_status["hand"]
        
        # 如果当前有防御卡可用，优先使用
        defend_cards = [card for card in available_cards if 
                        ("Skill" in card.get("type", "") or "Defend" in card.get("name", "") or "block" in card.get("effect", "").lower()) and 
                        card["cost"] <= current_energy]
        
        if defend_cards and player_status.get("block", 0) < 10:
            card = defend_cards[0]
            return f"〖{card['name']}〗"
            
        # 如果有可用的攻击卡
        attack_cards = [card for card in available_cards if 
                        "Attack" in card.get("type", "") and 
                        card["cost"] <= current_energy]
        
        if attack_cards and enemies:
            # 尝试攻击生命值最低的敌人
            min_health = float('inf')
            target_name = None
            
            for idx, enemy in enumerate(enemies):
                health_str = enemy["health"]
                
                # 处理生命值字段
                if isinstance(health_str, str) and '/' in health_str:
                    current_health = int(health_str.split('/')[0])
                else:
                    try:
                        current_health = int(health_str)
                    except:
                        current_health = 10  # 默认值
                        
                if current_health < min_health:
                    min_health = current_health
                    target_name = enemy.get("name", f"敌兵{idx+1}")
            
            card = attack_cards[0]
            return f"〖{card['name']}->{target_name}〗"
            
        # 如果有其他可用卡牌
        other_cards = [card for card in available_cards if card["cost"] <= current_energy]
        if other_cards:
            card = other_cards[0]
            return f"〖{card['name']}〗"
            
        # 如果无卡可用
        typewriter_print("💤 结束回合（原因：无可用卡牌或能量不足）")
        return "〖结束回合〗"

# ===== 主执行逻辑 =====
if __name__ == "__main__":
    typewriter_print("=== AI战术引擎启动 (持久化记忆版) ===")
    
    commander = BattleCommander()
    
    while True:
        try:
            command = commander.generate_command()
            typewriter_print(f"\n\033[1;35m🔥 战术指令: {command}\033[0m")
            
            # 等待用户输入继续
            user_input = input("继续下一回合? (y/n): ").strip().lower()
            if user_input != 'y':
                break
                
        except KeyboardInterrupt:
            typewriter_print("\n⏹ 用户中断操作")
            break
        except Exception as e:
            typewriter_print(f"\n🔥 严重错误: {str(e)}")
            break
    
    typewriter_print("🛑 战术引擎已停止")
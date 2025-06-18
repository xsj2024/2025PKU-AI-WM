from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType
from dotenv import load_dotenv
from typing import Optional  # ✅ 新增此行
import json
import os
import re

# ===== 初始化配置 =====
current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

# ===== 模型初始化 =====
def initialize_model():
    try:
        return ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type="deepseek-ai/DeepSeek-V3",  # ✅ 平台文档确认的名称
            url="https://api.siliconflow.cn/v1",  # ✅ 包含/v1路径
            model_config_dict={"max_tokens": 5000,"temperature": 0.2},
            api_key="sk-eieolvuyjgclelvomvzicesknimiywsdmdpksaalfxntcamc"
        )
    except Exception as e:
        print(f"🚨 模型启动失败: {e}")
        exit(1)

battle_model = initialize_model()

# ===== 知识库加载 =====
KNOWLEDGE_FILE = os.path.join("game_data", "knowledge.txt")

def load_strategy_knowledge() -> str:
    try:
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return "\n".join([line.strip() for line in f.readlines()])
    except FileNotFoundError:
        print(f"⚠️ 知识库文件 {KNOWLEDGE_FILE} 未找到")
        return "优先攻击血量最低且有易伤状态的敌人"

# ===== 游戏状态加载 =====
STATUS_FILE = os.path.join("game_data", "status.json")

def load_game_status() -> dict:
    default = {
        "玩家状态": {
            "能量": "3/3", 
            "血量": "68/75",
            "格挡": 12,
            "状态": {"虚弱": 0, "易伤": 0},
            "手牌": [
                {"名称": "打击", "作用": "基础攻击", "类型": "攻击", "耗能": 1},  # 新增字段
                {"名称": "防御", "作用": "基础防御", "类型": "技能", "耗能": 1}
            ]
        },
        "敌方状态": []
    }
    
    try:
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for card in data.get("玩家状态", {}).get("手牌", []):
                card.setdefault("耗能", 0)
            return {
                "玩家状态": {**default["玩家状态"], **data.get("玩家状态", {})},
                "敌方状态": [{
                    **e,
                    "名称": e.get("名称", f"敌方{idx+1}"),  # ⚡关键防御
                    "格挡": e.get("格挡", 0),
                    "状态": {**default["玩家状态"]["状态"], **e.get("状态",{})}
                } for idx, e in enumerate(data.get("敌方状态", []))]  # ⚡ 添加 enumerate
            }
    except Exception as e:
        print(f"⚠️ 状态加载失败: {str(e)}")
        return default

# ===== 强化版指令生成 =====
class BattleCommander:
    SYSTEM_PROMPT = """作为《杀戮尖塔》指令格式转换器，严格遵循：
1. 输出格式：
   - 有目标：〖卡牌名 -> 目标〗（原因：详细说明）
   - 无目标：〖卡牌名〗（原因：详细说明）
2. 必须满足：
   - 原因写在括号中，以「原因：」开头
   - 卡牌耗能不能超过当前能量"""  # [MODIFIED]

    def __init__(self):
        self.agent = ChatAgent(
            system_message=self.SYSTEM_PROMPT,
            model=battle_model,
            output_language="zh"
        )
        self.knowledge = load_strategy_knowledge()

    def _current_energy(self) -> int:
        """解析当前可用能量，格式如 '3/3' 返回3"""
        energy_str = self.current_status["玩家状态"]["能量"]
        return int(energy_str.split('/')[0])
    
    def _build_prompt(self, status: dict) -> str:
        player = status["玩家状态"]
        enemies = status["敌方状态"]
        
        raw_hand = player.get("手牌", [])
        processed_hand = [
            c if isinstance(c, dict) else {"名称": c, "作用": "效果未知"}
            for c in raw_hand
        ]

        # 构建动态描述
        hand_desc = "\n".join([
            f"〖{card['名称']}〗→ 耗能:{card['耗能']} 效果：{card['作用']}"  # 新增能耗显示
            for card in processed_hand
        ])

        # 修改prompt构建部分
        player_desc = (
            f"🛡️格挡:{player['格挡']} ❤️血量:{player['血量']} "
            f"🔋能量:{player['能量']}\n当前手牌:\n{hand_desc}"
        )
        
        # 构建敌人状态描述
        enemies_desc = []
        enemy_labels = []  # 存储目标标识符
        for e in enemies:  # 移除索引遍历
            label = e.get("名称", "未知敌人")  # ✅ 直接使用名称字段
            enemy_labels.append(label)
            # 直接显示名称不重复展示字段
            buffs = ''.join(
                [f"{k}{v}" for k,v in e.get("状态", {}).items() if v>0]
            )
            enemies_desc.append(  
                f"{label}: 💀{e['血量']} 🛡️{e['格挡']} 🌀{buffs or '无'} ⚡意图:{e['意图']}"
            )

        # 添加目标选择指引 [MODIFIED]
        target_rules = "\n".join([
            "- 卡牌耗能不能超过当前能量（当前能量:[玩家状态]中的🔋值）",
            "- 若所有卡牌耗能不够用则输出〖跳过〗",
            "- 攻击类卡牌必须附加箭头选择目标",
            f"- 可用目标标识符：{', '.join(enemy_labels) or '无'}",
            "- 治疗/防御类卡牌直接写卡牌名"
        ])
        
        return f"""
        === 战略知识库 ===
        {self.knowledge}  # 现在所有策略规则在此体现
        
        === 战场快照 ===
        [玩家状态] {player_desc}
        [敌人列表] {enemies_desc}
        
        === 格式规则 ===
        {target_rules}
        
        请综合以上信息输出决策命令：
        """

    def generate_command(self) -> str:
        status = load_game_status()
        self.current_status = status

        # === 新增前置条件检查 ===
        # 条件1：敌人数为0时直接结束回合
        if not status["敌方状态"]:
            print("🛑 战场无敌人，自动结束回合")
            return "〖跳过〗"
        
        # 条件2：无可用卡牌时结束回合（包含能量不足情况）
        current_energy = self._current_energy()
        playable = any(c["耗能"] <= current_energy 
                    for c in status["玩家状态"]["手牌"])
        if not playable:
            print("🔋 能量不足无法出牌，结束回合")
            return "〖跳过〗"
        
        # === 原执行流程 ===
        try:
            response = self.agent.step(self._build_prompt(status))
            return self._validate_response(response.msgs[0].content)
        except Exception as e:
            print(f"⚠️ 决策失败: {str(e)}")
            return self._fallback_command()

    def _validate_response(self, text: str) -> str:
        pattern = r"〖([^〗]+?)(\s*->\s*([^〗()]+?))?〗\s*（原因：\s*(.+?)\s*）"
        if match := re.search(pattern, text):
            card_name = match.group(1).strip()
            target = match.group(3).strip() if match.group(3) else None
            reasoning = match.group(4).strip()
        
        # 打印决策依据
            print(f"\033[1;34m🧠 模型决策逻辑：{reasoning}\033[0m")  # 蓝色高亮
            
            # 有效性检查：名称+能耗
            valid_cards = []
            for c in self.current_status["玩家状态"]["手牌"]:
                if c["名称"] == card_name and c["耗能"] <= self._current_energy():
                    valid_cards.append(c["名称"])
            
            if not valid_cards:
                print(f"⚠️ 无效卡牌或耗能不足：{card_name}")
                return self._fallback_command()
            target = match.group(3).strip() if match.group(3) else None
            
            # 卡牌有效性检查
            valid_cards = [c["名称"] for c in self.current_status["玩家状态"]["手牌"]]
            if card_name not in valid_cards:
                print(f"⚠️ 非法卡牌：{card_name}，合法选项：{valid_cards}")
                return self._fallback_command(valid_cards)

            # 目标必要性检查
            current_card = next(c for c in self.current_status["玩家状态"]["手牌"] 
                              if c["名称"] == card_name)
            if "攻击" in current_card.get("类型", ""):  # 根据卡牌类型判断
                enemies = [e["名称"] for e in self.current_status["敌方状态"]]
                if not target or target not in enemies:
                    print(f"⚠️ 攻击卡需指定有效目标，当前：{target}")
                    return f"〖{card_name} -> {enemies[0]}〗"  # 默认选择首个目标
            
            return self._process_valid_command(card_name, target)
        base_pattern = r"〖(.+?)(\s*->\s*(.+?))?〗"
        if base_match := re.search(base_pattern, text):
            print("⚠️ 未检测到原因说明，请检查输出格式")
            return self._process_valid_command(base_match.group(1), base_match.group(3))
        
        return self._fallback_command()
        
    def _process_valid_command(self, card_name: str, target: Optional[str]) -> str:
        """统一处理有效指令的组装"""
        cmd = f"〖{card_name}〗"
        if target:
            cmd = f"〖{card_name} -> {target}〗"
            
        # 二次能耗验证（防御模型幻觉）
        current_energy = self._current_energy()
        card_data = next(c for c in self.current_status["玩家状态"]["手牌"] 
                        if c["名称"] == card_name)
        if card_data["耗能"] > current_energy:
            print(f"⛔ 能耗校验未通过：{card_name} 需要{card_data['耗能']}能量")
            return self._fallback_command()
        
        return cmd

    # ===== 在回退指令中添加原因标注 =====
    def _fallback_command(self):
        current_energy = self._current_energy()
        playable_cards = [
            c["名称"] for c in self.current_status["玩家状态"]["手牌"]
            if c["耗能"] <= current_energy
        ]
        
        if playable_cards:
            selected = playable_cards[0]
            print(f"\033[1;33m🛡️ 系统回退选择：{selected}（原因：模型无有效响应）\033[0m")  # 黄色警示
            return f"〖{selected}〗"
        else:
            print("💤 结束回合（原因：无可用卡牌）")
            return "〖跳过〗"
def load_and_update(type):
    file_path = os.path.join("game_data", "status.json")
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
if __name__ == "__main__":
    load_dotenv()
        
    print("=== 战术引擎启动 ===")
    
    commander = BattleCommander()
    command = commander.generate_command()
    
    print(f"\033[1;32m🛡️ 指令生成完毕：{command}\033[0m")  # 绿色高亮显示
    
    # 保持窗口等待（仅Windows需要）
    if os.name == 'nt':
        os.system("pause")
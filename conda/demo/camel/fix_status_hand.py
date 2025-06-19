import json
import re
from difflib import get_close_matches
import os

# 修改为正确的 card_info 路径
CARD_INFO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fight', 'card.json'))

def load_card_db(path):
    card_info = []
    card_names = []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        card_info.extend(data)
        # 只收集有name字段的卡牌
        card_names.extend([card["name"] for card in data if "name" in card])
    name_lookup = {name.lower(): name for name in card_names}
    return card_info, card_names, name_lookup

def filter_leading_number(text: str):
    return re.sub(r'^\d+\s*', '', text)

def preprocess_text(text: str) -> str:
    # 只做基础清理，不做特殊映射
    text = re.sub(r"[^a-zA-Z0-9\s]", " ", text)
    return " ".join(text.split()).strip()

def find_closest_card_name(text: str, card_names, name_lookup) -> str:
    text = filter_leading_number(text)
    clean_text = preprocess_text(text)
    if not clean_text:
        return "Unknown_EmptyInput"
    lower_text = clean_text.lower()
    if lower_text in name_lookup:
        return name_lookup[lower_text]
    words = clean_text.split()
    phrases = [' '.join(words[:i]) for i in range(len(words), 0, -1)]
    thresholds = [0.9, 0.8, 0.7]
    for phrase in phrases:
        for threshold in thresholds:
            matches = get_close_matches(phrase, card_names, n=1, cutoff=threshold)
            if matches:
                return matches[0]
    return f"Unknown_{clean_text[:15].strip('_')}"

def parse_effect_with_upgrade(description, upgraded):
    """
    将 description 形如 'Deal 8(10) damage. Apply 2(3)Vulnerable.'
    解析为升级前/后效果，返回升级前或升级后效果字符串
    """
    def repl(m):
        a, b = m.group(1), m.group(2)
        return b if upgraded else a
    # 替换所有 a(b) 为 b 或 a
    return re.sub(r'(\d+)\((\d+)\)', repl, description)

def parse_hand_card(card_str, card_names, name_lookup, card_info):
    # 例: "1 Red Strike"、"1 Red Defend"、"1 Enlightenment"、"1 Bash+"
    m = re.match(r"(\d+)\s+(.+)", card_str)
    if not m:
        return {"name": card_str, "type": "", "cost": 1, "effect": card_str}
    cost = int(m.group(1))
    rest = m.group(2).strip()
    parts = rest.split()
    # 只有 Strike 和 Defend 才有颜色前缀，且直接跳过颜色
    if len(parts) >= 2 and parts[1] in ["Strike", "Defend"] and parts[0] in ["Red", "Green", "Blue", "Purple"]:
        card_name = parts[1]
        name_start = 2
    else:
        card_name = parts[0]
        name_start = 1
    # 检查是否升级
    upgraded = False
    if card_name.endswith('+'):
        upgraded = True
        card_name = card_name[:-1]
    # 1. 按前缀递减做模糊匹配，找到最长能匹配的卡牌名
    match_name = None
    match_len = 0
    for i in range(len(parts)-name_start+1, 0, -1):
        prefix = ' '.join([card_name] + parts[name_start:name_start+i])
        name = find_closest_card_name(prefix, card_names, name_lookup)
        if not name.startswith('Unknown_'):
            match_name = name
            match_len = i
            break
    if match_name:
        card_db = next((c for c in card_info if c.get("name") == match_name), None)
        card_type = card_db.get("type", "") if card_db else ""
        description = card_db.get("description", "") if card_db else ""
        effect = parse_effect_with_upgrade(description, upgraded)
        return {
            "name": match_name + ('+' if upgraded else ''),
            "type": card_type,
            "cost": cost,
            "effect": effect
        }
    else:
        # 没有匹配到名字，type=unknown，effect=Not playable
        return {
            "name": card_name + ('+' if upgraded else ''),
            "type": "unknown",
            "cost": cost,
            "effect": "Not playable"
        }

def fix_status_hand(path, out_path=None):
    card_info, card_names, name_lookup = load_card_db(CARD_INFO_PATH)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    hand = data.get('player_status', {}).get('hand', [])
    # 兼容字符串和 dict 两种 hand
    new_hand = []
    for card in hand:
        if isinstance(card, str):
            card_obj = parse_hand_card(card, card_names, name_lookup, card_info)
        else:
            print(f"处理手牌: {card}")
            # 兼容升级卡牌：如果名字以+结尾，匹配时去掉+
            card_obj = card.copy()
            card_name = card_obj.get("name", "")
            upgraded = False
            if card_name.endswith('+'):
                upgraded = True
                base_name = card_name[:-1]
            else:
                base_name = card_name
            match = next((c for c in card_info if c.get("name") == base_name), None)
            if match:
                card_obj.setdefault("type", match.get("type", ""))
                description = match.get("description", "")
                # effect 字段根据升级与否替换 a(b)
                def repl(m):
                    a, b = m.group(1), m.group(2)
                    return b if upgraded else a
                effect = re.sub(r'(\d+)\((\d+)\)', repl, description)
                card_obj.setdefault("effect", effect)
            else:
                card_obj["type"] = "unknown"
                card_obj["effect"] = "Not playable"
            new_hand.append(card_obj)
    data['player_status']['hand'] = new_hand
    # === 新增：整理enemies的intent ===
    for enemy in data.get('enemies', []):
        statuses = enemy.get('statuses', {})
        if statuses and isinstance(statuses, dict):
            intent = ""
            new_statuses = {}
            for k, v in statuses.items():
                if isinstance(v, str) and 'intends to' in v:
                    intent = v
                else:
                    new_statuses[k] = v
            if intent:
                enemy['intent'] = intent
            enemy['statuses'] = new_statuses
    out_path = out_path or path
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已修正 hand 字段和intent，写回 {out_path}")

if __name__ == '__main__':
    fix_status_hand('fight/status.json', 'fight/status_fixed.json')

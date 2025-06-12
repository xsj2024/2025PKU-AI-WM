import json
import re
from difflib import get_close_matches
import os

# 你可以根据实际路径调整
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

def parse_hand_card(card_str, card_names, name_lookup, card_info):
    # 例: "1 Entrench S Double your Block" 或 "1 Feel No Pain Poi Whenever ..."
    m = re.match(r"(\d+)\s+(.+)", card_str)
    if not m:
        return {"name": card_str, "type": "", "cost": 1, "effect": card_str}
    cost = int(m.group(1))
    rest = m.group(2).strip()
    parts = rest.split()
    # 1. 按前缀递减做模糊匹配，找到最长能匹配的卡牌名
    match_name = None
    match_len = 0
    for i in range(len(parts), 0, -1):
        prefix = ' '.join(parts[:i])
        name = find_closest_card_name(prefix, card_names, name_lookup)
        # 只接受非Unknown匹配
        if not name.startswith('Unknown_'):
            match_name = name
            match_len = i
            break
    if match_name:
        # 直接查数据库
        card_db = next((c for c in card_info if c.get("name") == match_name), None)
        card_type = card_db.get("type", "") if card_db else ""
        effect = card_db.get("description", "") if card_db else ""
        return {
            "name": match_name,
            "type": card_type,
            "cost": cost,
            "effect": effect
        }
    else:
        # fallback: 只用第一个单词为名
        name_raw = parts[0]
        match_name = find_closest_card_name(name_raw, card_names, name_lookup)
        card_db = next((c for c in card_info if c.get("name") == match_name), None)
        card_type = card_db.get("type", "") if card_db else ""
        effect = card_db.get("description", "") if card_db else ""
        return {
            "name": match_name,
            "type": card_type,
            "cost": cost,
            "effect": effect
        }

def fix_status_hand(path, out_path=None):
    card_info, card_names, name_lookup = load_card_db(CARD_INFO_PATH)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    hand = data.get('player_status', {}).get('hand', [])
    if hand and isinstance(hand[0], str):
        new_hand = [parse_hand_card(card, card_names, name_lookup, card_info) for card in hand]
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

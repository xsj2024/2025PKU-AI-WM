import json
import os

# 需要合并的文件路径
files = [
    '../game_info/card_info.json',
    '../game_info/card_info_Colorless_Cards.json',
    '../game_info/card_info_Defect_Cards.json',
    '../game_info/card_info_Silent_Cards.json',
    '../game_info/card_info_Watcher_Cards.json',
]

all_cards = []
for f in files:
    path = os.path.join(os.path.dirname(__file__), f)
    with open(path, 'r', encoding='utf-8') as fin:
        data = json.load(fin)
        all_cards.extend(data)

with open(os.path.join(os.path.dirname(__file__), 'card.json'), 'w', encoding='utf-8') as fout:
    json.dump(all_cards, fout, ensure_ascii=False, indent=2)

print(f"合并完成，共 {len(all_cards)} 张卡牌，已写入 card.json")

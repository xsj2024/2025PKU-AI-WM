import time
import pyautogui
pyautogui.FAILSAFE = False
from info_reader import hand_card_reader, unit_status_reader, deck_card_reader
from annotator import game_capture
from annotator.config import Config
from text_reader.ascii_ocr import ascii_ocr
from game.phase_common import card_selection_phase, choose_loot_phase
from annotator.game_capture import activate_game_window
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from fight import BattleCommander

class BattleHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label, bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label
        self.bot = bot
        self.history_lines = []  # 新增历史上下文链
        self.commander = BattleCommander()  # 集成AI战术指挥官

    def handle_battle(self, frame, detections):
        while True:
            stable_frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(stable_frame)
            labels = [d[0] for d in detections]
            has_prompt = 'prompt' in labels
            has_card = 'card' in labels
            has_button = 'button' in labels
            has_loot = 'loot' in labels
            if has_loot:
                print('Loot selection phase.')
                choose_loot_phase(self, stable_frame, detections)
                return
            if has_card and has_prompt:
                print('Card selection phase.')
                card_selection_phase(self, stable_frame, detections)
                continue
            if has_prompt:
                print('Hand selection phase.')
                self.hand_selection_phase(stable_frame, detections)
                continue
            if has_button:
                print('Play phase.')
                # --- 新增血条检测逻辑 ---
                # 收集 player/monster 和 hp_bar
                targets = [(i, d) for i, d in enumerate(detections) if d[0] in ('player', 'monster')]
                hp_bars = [(i, d) for i, d in enumerate(detections) if d[0] == 'hp_bar']
                hp_info = []
                hp_idx = 0
                for idx, target in targets:
                    tx1, ty1, tx2, ty2 = target[1:5]
                    # 默认无血条
                    info = {'type': target[0], 'has_hp': False, 'block': None, 'hp': None, 'max_hp': None}
                    # 检查 hp_bar 是否与目标对齐
                    if hp_idx < len(hp_bars):
                        _, hpbar = hp_bars[hp_idx]
                        hx1, hy1, hx2, hy2 = hpbar[1:5]
                        # 判断左上角是否接近（阈值可调）
                        if max(hx1, tx1) < min(hx2, tx2):
                            # 有血条，OCR 识别
                            info['has_hp'] = True
                            hp_img = stable_frame[hy1:hy2, hx1:hx2]
                            hp_text = ascii_ocr(hp_img)
                            # 解析血条文本，支持“格挡/当前/最大”或“当前/最大”
                            info['hp'] = hp_text
                            hp_idx += 1
                    hp_info.append(info)
                # --- end ---
                # 找到 detections 中的能量状态
                energy_state = None
                for d in detections:
                    if d[0] == 'energy_state':
                        energy_state = self.get_box_text(stable_frame, d)
                        break
                if energy_state is None:
                    assert False, "Energy state not found in detections."
                self.battle_play_menu(energy_state, hp_info)
                # 将鼠标移动到 energy_state 区域上方 50 像素
                self.capture.move_to_edge()
                continue
            print(labels)
            print('Unknown battle phase.')

    def battle_play_menu(self, energy_state, hp_info):
        self.history_lines = []
        def add_history(line):
            print(line)
            self.history_lines.append(str(line))
        add_history(f'\nenergy_state : {energy_state}')
        add_history(f"player: {hp_info[0]['hp']}")
        for i in range(1, len(hp_info)):
            add_history(f"monster{i}: {hp_info[i]['hp']}")
        add_history("Choose your action:")
        add_history('1. Show all hand cards')
        add_history('2. Show all unit status')
        add_history('3. Show draw pile')
        add_history('4. Show discard pile')
        add_history('5. Play a card')
        add_history('6. End turn')
        hand_cards = hand_card_reader.read_hand_cards(self.capture, self.model)
        hand_cards_str = [str(card) for card in hand_cards]
        units = unit_status_reader.read_unit_status(self.capture, self.model)
        units_str = [str(u) for u in units]
        ai_prompt = {
            "system": "你是杀戮尖塔自动战斗助手，请根据以下信息，返回你要选择的编号（只返回数字，不要解释）：\n规则：如果你有能量且手牌中有费用小于等于当前能量的牌，就优先选择出牌（5）。如果有能在本回合内击杀的敌人，优先选择打出能击杀该敌人的牌。只有在没有可用牌或没有能量时才选择结束回合（6）。",
            "rule": "你只需要返回恰好一个 1,2,3,4,5,6中间的数字代表你的选择即可 ", 
            "battle_info": '\n'.join(self.history_lines),
            "hand_cards": hand_cards_str,
            "unit_status": units_str
        }
        print("\n===== 发送给AI的决策内容（主菜单） =====")
        print(json.dumps(ai_prompt, ensure_ascii=False, indent=2))
        print("===== END =====\n")
        # --- 增加自动重试 ---
        while True:
            try:
                ai_response = self.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
                break
            except Exception as e:
                if '429' in str(e) or 'rate limit' in str(e).lower():
                    print("[AI限流] 等待10秒后重试...")
                    time.sleep(10)
                else:
                    print(f"[AI请求异常] {e}")
                    time.sleep(5)
        ai_result = ai_response.msg.content.strip()
        add_history(f"AI选择: {ai_result}")
        import re, json as _json
        # 兼容AI主菜单直接返回json（如{"card":2,"target":1}）的情况
        choice = None
        play_result = None
        try:
            parsed = _json.loads(ai_result)
            if isinstance(parsed, dict) and 'card' in parsed:
                choice = '5'
                play_result = ai_result
        except Exception:
            pass
        if choice is None:
            match = re.search(r'"action"\s*:\s*"?(\d+)"?', ai_result)
            if match:
                choice = match.group(1)
            else:
                digits = ''.join(filter(str.isdigit, ai_result))
                choice = digits if digits else '1'
        # --- 写入最新状态到 status.json 供AI战术指挥官使用 ---
        try:
            player_status = {
                "energy": str(energy_state),
                "health": hp_info[0]['hp'] if hp_info and 'hp' in hp_info[0] else '',
                "block": hp_info[0].get('block', 0) if hp_info else 0,
                "statuses": {},  # 可根据实际识别补充
                "hand": []
            }
            for card in hand_cards:
                # 尝试解析卡牌名、类型、费用、效果
                card_str = str(card)
                # 简单正则提取
                import re
                name = re.search(r'^[\d. ]*([\u4e00-\u9fa5A-Za-z0-9_\- ]+)', card_str)
                name = name.group(1).strip() if name else card_str
                cost = re.search(r'(\d+)', card_str)
                cost = int(cost.group(1)) if cost else 1
                ctype = 'Attack' if 'Att' in card_str or '攻击' in card_str else ('Skill' if 'Sk' in card_str or '技能' in card_str else '')
                effect = card_str
                player_status["hand"].append({
                    "name": name,
                    "type": ctype,
                    "cost": cost,
                    "effect": effect
                })
            enemies = []
            for i, u in enumerate(units):
                ustr = str(u)
                name = re.search(r"'unit_label': 'monster'[^,]*", ustr)
                name = f"怪物{i+1}" if not name else f"怪物{i+1}"
                hp = ''
                for hi in hp_info[1:]:
                    if i < len(hp_info)-1:
                        hp = hp_info[i+1]['hp']
                        break
                block = 0
                intent = ''
                statuses = {}
                enemies.append({
                    "name": name,
                    "health": hp,
                    "block": block,
                    "intent": intent,
                    "statuses": statuses
                })
            status = {"player_status": player_status, "enemies": enemies}
            print(status)
            with open(r'd:\conda\camel\game_data\status.json', 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[状态写入异常] {e}")
        if choice != '5': activate_game_window()
        if choice == '1':
            try:
                add_history('Hand cards:')
                for i, card in enumerate(hand_cards):
                    add_history(f'{i+1}: {card}')
            except Exception as e:
                add_history(f'[ERROR] {e}')
        elif choice == '2':
            try:
                units = unit_status_reader.read_unit_status(self.capture, self.model)
                add_history('Units:')
                for u in units:
                    add_history(u)
            except Exception as e:
                add_history(f'[ERROR] {e}')
        elif choice == '3':
            try:
                self.click_box_by_label('deck', index=0)
                frame = self.capture.wait_for_stable_frame()
                detections = self.model.detect_all(frame)
                if any(d[0] == 'energy_state' for d in detections):
                    add_history("Empty draw pile.")
                    return
                cards = deck_card_reader.get_card_list_screenshots(self.capture, self.model)
                add_history('Draw pile:')
                for c in cards:
                    add_history(c)
                pyautogui.click()
            except Exception as e:
                add_history(f'[ERROR] {e}')
        elif choice == '4':
            try:
                self.click_box_by_label('discard_deck', index=0)
                frame = self.capture.wait_for_stable_frame()
                detections = self.model.detect_all(frame)
                if any(d[0] == 'energy_state' for d in detections):
                    add_history("Empty draw pile.")
                    return
                cards = deck_card_reader.get_card_list_screenshots(self.capture, self.model)
                add_history('Discard pile:')
                for c in cards:
                    add_history(c)
                pyautogui.click()
            except Exception as e:
                add_history(f'[ERROR] {e}')
        elif choice == '5':
            # 用AI战术指挥官生成指令
            command = self.commander.generate_command()
            add_history(f"AI战术指令: {command}")
            # 解析指令格式 〖卡牌名称->目标〗 或 〖卡牌名称〗
            import re
            match = re.match(r'〖(.+?)(?:->(.+?))?〗', command)
            if match:
                card_name = match.group(1).strip()
                target_name = match.group(2).strip() if match.group(2) else None
                # 在手牌中查找卡牌编号
                card_idx = None
                for i, card in enumerate(hand_cards):
                    if card_name in str(card):
                        card_idx = i+1
                        break
                if card_idx is None:
                    add_history(f"[ERROR] 未找到卡牌: {card_name}")
                    return
                # 在怪物中查找目标编号
                target_idx = 0
                if target_name:
                    for i, u in enumerate(units):
                        if target_name in str(u):
                            target_idx = i
                            break
                activate_game_window()
                try:
                    tt = 'monster' if target_idx > 0 else 'player'
                    y = target_idx - 1 if target_idx > 0 else 0
                    self.capture.move_mouse_to_center()
                    pyautogui.press(str(card_idx))
                    self.click_box_by_label(tt, index=y)
                    add_history(f'Played card {card_idx} to target {target_idx}.')
                except Exception as e:
                    add_history(f'[ERROR] {e}')
            else:
                add_history(f'[ERROR] 无法解析AI战术指令: {command}')
        elif choice == '6':
            try:
                self.click_box_by_label('button', index=0)
                add_history('Turn ended.')
            except Exception as e:
                add_history(f'[ERROR] {e}')
        else:
            add_history('Invalid choice. Please try again.')

    def hand_selection_phase(self, frame, detections):
        prompt_box = [d for d in detections if d[0] == 'prompt']
        button_box = [d for d in detections if d[0] == 'button']
        prompt_text = self.get_box_text(frame, prompt_box[0]) if prompt_box else ''
        button_text = self.get_box_text(frame, button_box[0]) if button_box else ''
        print(f'Prompt: {prompt_text}')
        print(f'Button: {button_text}')
        while True:
            idx = int(input('Enter hand card index (or -1 to confirm): '))
            activate_game_window()
            if idx == -1:
                self.click_box_by_label('button', index=0, frame=frame, detections=detections)
                break
            else:
                pyautogui.press(str(idx))

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
from fight import BattleCommander  # 新增
import subprocess
import ast
import os
import cv2
from annotator_battle_unit.model_manager import ModelManager

class BattleHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label, bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label
        self.bot = bot
        self.history_lines = []  # 新增历史上下文链
        self.fight_ai = BattleCommander()  # 新增
        self.battle_model = ModelManager()

    def handle_battle(self, frame, detections):
        while True:
            stable_frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(stable_frame)
            # 保存detections到本地，便于调试
            with open('figure/detections_dump.json', 'w', encoding='utf-8') as f:
                import json
                json.dump(detections, f, ensure_ascii=False, indent=2)
            # 保存stable_frame到本地，便于调试
            cv2.imwrite('figure/stable_frame.png', stable_frame)
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
                print("targets:", targets)
                print("hp_bars:", hp_bars)
                for idx, target in targets:
                    tx1, ty1, tx2, ty2 = target[1:5]
                    print("kuang:", target[1:5])
                    info = {'type': target[0], 'has_hp': False, 'block': None, 'hp': None, 'max_hp': None}
                    # 匹配最近的血条（X轴有重叠，Y轴在目标下方且距离最近）
                    best_bar = None
                    min_y_dist = float('inf')
                    for _, hpbar in hp_bars:
                        hx1, hy1, hx2, hy2 = hpbar[1:5]
                        # X轴有重叠
                        if max(hx1, tx1) < min(hx2, tx2):
                            # Y轴血条在目标下方或重叠
                            if hy1 >= ty2 or (ty1 <= hy2 <= ty2):
                                y_dist = abs(hy1 - ty2)
                                if y_dist < min_y_dist:
                                    min_y_dist = y_dist
                                    best_bar = hpbar
                    if best_bar is not None:
                        hx1, hy1, hx2, hy2 = best_bar[1:5]
                        print("血条:", best_bar[1:5])
                        info['has_hp'] = True
                        ocr_results = []
                        # 新增：保存截图到figure文件夹
                        save_dir = 'figure'
                        os.makedirs(save_dir, exist_ok=True)
                        for i in range(1):
                            stable_frame = self.capture.wait_for_stable_frame()
                            # 扩展血条下边界，防止漏截
                            hy2_expand = min(hy2 + 10, stable_frame.shape[0])
                            hp_img = stable_frame[hy1:hy2_expand, hx1:hx2]
                            img_path = os.path.join(save_dir, f"hpimg_target{idx}_bar{hx1}_{hy1}_{hx2}_{hy2}_{i}.png")
                            hp_text = ascii_ocr(hp_img)
                            ocr_results.append(hp_text)
                        from collections import Counter
                        most_common = Counter(ocr_results).most_common(1)
                        hp_text_final = most_common[0][0] if most_common else ''
                        info['hp'] = hp_text_final
                        print("hp:", hp_text_final)
                    hp_info.append(info)
                # --- end ---
                # 找到 detections 中的能量状态
                energy_state = None
                for d in detections:
                    if d[0] == 'energy_state':
                        print("能量状态检测到:", d)
                        ex1, ey1, ex2, ey2 = d[1:5]
                        os.makedirs('figure', exist_ok=True)
                        # 多次截图并识别能量，取众数
                        energy_texts = []
                        for i in range(5):
                            stable_frame_energy = self.capture.wait_for_stable_frame()
                            energy_img = stable_frame_energy[ey1:ey2, ex1:ex2]
                            if i == 0:
                                cv2.imwrite('figure/energy_state.png', energy_img)
                            energy_text = self.get_box_text(stable_frame_energy, d)
                            energy_texts.append(str(energy_text))
                        from collections import Counter
                        most_common = Counter(energy_texts).most_common(1)
                        energy_state = most_common[0][0] if most_common else ''
                        print("energy_state(众数):", energy_state)
                        break
                if energy_state is None:
                    assert False, "Energy state not found in detections."
                self.battle_play_menu(energy_state, hp_info)
                # 将鼠标移动到 energy_state 区域上方 50 像素
                self.capture.move_to_edge()
                continue
            print(labels)
            print('Unknown battle phase.')

            # 保存detections到本地，便于调试
            with open('figure/detections_dump.json', 'w', encoding='utf-8') as f:
                import json
                json.dump(detections, f, ensure_ascii=False, indent=2)
            # 保存stable_frame到本地，便于调试
            cv2.imwrite('figure/stable_frame.png', stable_frame)

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
        hand_cards = hand_card_reader.read_hand_cards(self.capture, self.battle_model)
        hand_cards_str = [str(card) for card in hand_cards]
        units = unit_status_reader.read_unit_status(self.capture, self.model)
        units_str = [str(u) for u in units]
        # 鼠标归位
        self.capture.move_to_edge()
        # === 新增：解析unit_status，自动填充intent和statuses ===
        # 解析unit_status，假设顺序与enemies一致
        print(units)
        parsed_units = [ast.literal_eval(u) if isinstance(u, str) else u for u in units]
        enemy_units = [u for u in parsed_units if u.get('unit_label') == 'monster']
        enemies = []
        print(enemy_units)
        for i, hp in enumerate(hp_info[1:], 0):
            statuses = {}
            if i < len(enemy_units):
                print(enemy_units[i])
                messages = enemy_units[i].get('messages', [])
                for idx, msg in enumerate(messages, 1):
                    statuses[f"msg{idx}"] = msg
                print(f"enemy {i+1} statuses:", statuses)
            enemies.append({
                "name": f"monster{i+1}",
                "health": str(hp['hp']),
                "block": 0,
                "intent": "?",
                "statuses": statuses
            })
        status_dict = {
            "player_status": {
                "energy": str(energy_state),
                "health": str(hp_info[0]['hp']),
                "block": 0,
                "statuses": {},
                "hand": hand_cards
            },
            "enemies": enemies
        }
        with open("fight/status.json", "w", encoding="utf-8") as f:
            json.dump(status_dict, f, ensure_ascii=False, indent=2)
        # === 新增：调用fix_status_hand.py修正hand结构 ===
        subprocess.run(["python", "fix_status_hand.py", "fight/status.json", "fight/status_fixed.json"], check=True)
       # 调用AI，主菜单只返回数字
        # 智能映射指令到主菜单选项
        choice = '5'
        play_result = None
        if choice != '5': activate_game_window()
        if choice == '1':
            try:
                cards = hand_card_reader.read_hand_cards(self.capture, self.battle_model)
                print('Hand cards:')
                for i, card in enumerate(cards):
                    print(f'{i+1}: {card}')
            except Exception as e:
                print(f'[ERROR] {e}')
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
            if play_result is None:
                info = self.fight_ai.generate_command_with_detail()
                print(info)
                card_idx = info["choice"]
                target_idx = info["target_idx"]
                # 新增：如果AI决策为End Turn，直接执行结束回合
                if info.get('card', '').strip().lower() == 'end turn':
                    try:
                        self.click_box_by_label('button', index=0)
                        add_history('AI决策为End Turn，已结束回合。')
                    except Exception as e:
                        add_history(f'[ERROR] {e}')
                    return
                add_history(f"AI打牌决策: idx=({card_idx}, {target_idx})")
                # --- 执行打牌 ---
                activate_game_window()
                try:
                    tt = 'monster' if target_idx is not None and target_idx > 0 else 'player'
                    y = target_idx - 1 if target_idx is not None and target_idx > 0 else 0
                    self.capture.move_mouse_to_center()
                    pyautogui.press(str(card_idx))
                    self.click_box_by_label(tt, index=y)
                    add_history(f'Played card {card_idx} to target {target_idx}.')
                except Exception as e:
                    add_history(f'[ERROR] {e}')
            else:
                pass
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

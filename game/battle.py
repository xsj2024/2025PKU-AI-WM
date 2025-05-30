import time
import pyautogui
from info_reader import hand_card_reader, unit_status_reader, deck_card_reader
from annotator import game_capture
from annotator.config import Config
from text_reader.ascii_ocr import ascii_ocr
from game.phase_common import card_selection_phase, choose_loot_phase
from annotator.game_capture import activate_game_window

class BattleHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label

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
        print(f'\nenergy_state : {energy_state}')
        print(f"player: {hp_info[0]['hp']}")
        for i in range(1, len(hp_info)):
            print(f"monster{i}: {hp_info[i]['hp']}")
        print("Choose your action:")
        print('1. Show all hand cards')
        print('2. Show all unit status')
        print('3. Show draw pile')
        print('4. Show discard pile')
        print('5. Play a card')
        print('6. End turn')
        choice = input('Enter your choice: ').strip()
        activate_game_window()
        if choice == '1':
            try:
                cards = hand_card_reader.read_hand_cards(self.capture, self.model)
                print('Hand cards:')
                for i, card in enumerate(cards):
                    print(f'{i+1}: {card}')
            except Exception as e:
                print(f'[ERROR] {e}')
        elif choice == '2':
            try:
                units = unit_status_reader.read_unit_status(self.capture, self.model)
                print('Units:')
                for u in units:
                    print(u)
            except Exception as e:
                print(f'[ERROR] {e}')
        elif choice == '3':
            try:
                self.click_box_by_label('deck', index=0)
                frame = self.capture.wait_for_stable_frame()
                detections = self.model.detect_all(frame)
                if any(d[0] == 'energy_state' for d in detections):
                    print("Empty draw pile.")
                    return
                cards = deck_card_reader.get_card_list_screenshots(self.capture, self.model)
                print('Draw pile:')
                for c in cards:
                    print(c)
                # self.click_box_by_label('deck', index=0)
                pyautogui.click()
            except Exception as e:
                print(f'[ERROR] {e}')
        elif choice == '4':
            try:
                self.click_box_by_label('discard_deck', index=0)
                frame = self.capture.wait_for_stable_frame()
                detections = self.model.detect_all(frame)
                if any(d[0] == 'energy_state' for d in detections):
                    print("Empty draw pile.")
                    return
                cards = deck_card_reader.get_card_list_screenshots(self.capture, self.model)
                print('Discard pile:')
                for c in cards:
                    print(c)
                # self.click_box_by_label('discard_deck', index=0)
                pyautogui.click()
            except Exception as e:
                print(f'[ERROR] {e}')
        elif choice == '5':
            print('Enter the index of the card to play (1-9,0 for 10th card):')
            x = input('Card index: ')
            activate_game_window()
            y = input('Target index: ')
            activate_game_window()
            try:
                y = int(y)
                tt = 'monster' if y > 0 else 'player'
                y = y - 1 if y > 0 else 0
                self.capture.move_mouse_to_center()  # 确保鼠标在游戏窗口内
                pyautogui.press(x)
                self.click_box_by_label(tt, index=y)
                print(f'Played card {x} to target {y}.')
            except Exception as e:
                print(f'[ERROR] {e}')
        elif choice == '6':
            try:
                self.click_box_by_label('button', index=0)
                print('Turn ended.')
            except Exception as e:
                print(f'[ERROR] {e}')
        else:
            print('Invalid choice. Please try again.')

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

import time
import json
import re
from game.phase_common import choose_loot_phase, deck_selection_phase
from annotator import game_capture
from annotator.game_capture import activate_game_window
from info_reader.hand_card_reader import read_card

class EventHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label, bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label
        self.bot = bot

    def match_and_keep_phase(self, frame, detections):
        # 获取所有 card_back
        card_backs = [d for d in detections if d[0] == 'card_back']
        if len(card_backs) != 12:
            print('Error: card_back count is not 12!')
            return
        # 计算所有卡牌的中心坐标
        centers = [((d[1]+d[3])//2, (d[2]+d[4])//2) for d in card_backs]
        xs = sorted([c[0] for c in centers])
        ys = sorted([c[1] for c in centers])
        # 取每列的中心
        col_centers = [xs[i] for i in [0,4,8,11]]
        row_centers = [ys[i] for i in [0,4,8]]
        # 建立网格(row,col)到card_back索引的映射
        grid_map = {}
        for idx, (cx, cy) in enumerate(centers):
            # 找到最近的行和列
            row = min(range(3), key=lambda r: abs(cy-row_centers[r]))
            col = min(range(4), key=lambda c: abs(cx-col_centers[c]))
            grid_map[(row, col)] = idx
        available = set(grid_map.keys())
        for turn in range(5):
            print(f'Round {turn+1}/5')
            # 选择第一个
            while True:
                # print('Available positions:')
                # for (r, c) in sorted(available):
                #     print(f'({r+1},{c+1})', end='  ')
                # print()
                # 构造AI输入
                available_str = ' '.join([f'({r+1},{c+1})' for (r, c) in sorted(available)])
                ai_prompt = {
                    "system": "你是杀戮尖塔事件自动助手，请根据可选卡牌位置，返回你要选择的第一个卡牌位置（格式：row col，只返回数字，不要解释）：",
                    "available_positions": available_str
                }
                while True:
                    try:
                        ai_response = self.get_box_text.__self__.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
                        break
                    except Exception as e:
                        if '429' in str(e) or 'rate limit' in str(e).lower():
                            print("[AI限流] 等待10秒后重试...")
                            time.sleep(10)
                        else:
                            print(f"[AI请求异常] {e}")
                            time.sleep(5)
                s = ai_response.msg.content.strip()
                print(f"AI选择: {s}")
                activate_game_window()
                try:
                    r1, c1 = [int(x)-1 for x in s.strip().split()]
                except:
                    print('Invalid input!')
                    continue
                if (r1, c1) in available:
                    break
                print('Invalid position!')
            idx1 = grid_map[(r1, c1)]
            self.click_box_by_label('card_back', index=idx1, frame=frame, detections=detections)
            time.sleep(0.5)
            frame1 = self.capture.get_frame()
            detections1 = self.model.detect_all(frame1)
            # 只识别点击区域的卡牌
            # 找到与目标位置最近的 card
            min_dist = float('inf')
            card1 = None
            for d in detections1:
                if d[0] == 'card':
                    cx, cy = (d[1]+d[3])//2, (d[2]+d[4])//2
                    dist = abs(cx - col_centers[c1]) + abs(cy - row_centers[r1])
                    if dist < min_dist:
                        min_dist = dist
                        card1 = d
            card1_info = ''
            if card1:
                x1, y1, x2, y2 = card1[1:5]
                roi = frame1[y1:y2, x1:x2]
                card1_info = read_card(roi)
            print(f'First card info: {card1_info}')
            # 选择第二个
            while True:
                # 构造AI输入
                available_str = ' '.join([f'({r+1},{c+1})' for (r, c) in sorted(available) if (r, c) != (r1, c1)])
                ai_prompt = {
                    "system": "你是杀戮尖塔事件自动助手，请根据可选卡牌位置，返回你要选择的第二个卡牌位置（格式：row col，只返回数字，不要解释）：",
                    "available_positions": available_str
                }
                while True:
                    try:
                        ai_response = self.get_box_text.__self__.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
                        break
                    except Exception as e:
                        if '429' in str(e) or 'rate limit' in str(e).lower():
                            print("[AI限流] 等待10秒后重试...")
                            time.sleep(10)
                        else:
                            print(f"[AI请求异常] {e}")
                            time.sleep(5)
                s = ai_response.msg.content.strip()
                print(f"AI选择: {s}")
                activate_game_window()
                try:
                    r2, c2 = [int(x)-1 for x in s.strip().split()]
                except:
                    print('Invalid input!')
                    continue
                if (r2, c2) in available and (r2, c2) != (r1, c1):
                    break
                print('Invalid position!')
            idx2 = grid_map[(r2, c2)]
            self.click_box_by_label('card_back', index=idx2, frame=frame, detections=detections)
            time.sleep(0.5)
            frame2 = self.capture.get_frame()
            time.sleep(0.5)
            self.capture.move_to_edge()
            frame3 = self.capture.wait_for_stable_frame()
            detections3 = self.model.detect_all(frame3)
            card_backs3 = [d for d in detections3 if d[0] == 'card_back']
            if len(card_backs3) < len(card_backs):
                print(f'You got the card: {card1_info}')
                centers3 = [((d[1]+d[3])//2, (d[2]+d[4])//2) for d in card_backs3]
                # 找到消失的卡牌
                # 用距离阈值判断哪个位置的卡牌消失，避免因识别误差导致判断错误
                disappeared = []
                for pos in available:
                    px, py = col_centers[pos[1]], row_centers[pos[0]]
                    found = False
                    for cx, cy in centers3:
                        if abs(cx - px) + abs(cy - py) < 20:  # 允许一定误差
                            found = True
                            break
                    if not found:
                        disappeared.append(pos)
                for pos in disappeared:
                    available.remove(pos)
                card_backs = card_backs3
            else:
                detections2 = self.model.detect_all(frame2)
                # 找到与目标位置最近的 card
                min_dist = float('inf')
                card2 = None
                for d in detections2:
                    if d[0] == 'card':
                        cx, cy = (d[1]+d[3])//2, (d[2]+d[4])//2
                        dist = abs(cx - col_centers[c2]) + abs(cy - row_centers[r2])
                        if dist < min_dist:
                            min_dist = dist
                            card2 = d
                card2_info = ''
                if card2:
                    x1, y1, x2, y2 = card2[1:5]
                    roi = frame2[y1:y2, x1:x2]
                    card2_info = read_card(roi)
                print(f'Second card info: {card2_info}')
                print('No card obtained this round.')
        print('Match and keep phase finished.')


    def handle_event(self, frame, detections):
        while True:
            frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(frame)
            labels = [d[0] for d in detections]
            # --- 新增：识别血量和金币（修正标签） ---
            player_hp = None
            player_gold = None
            # 识别血量
            hp_box = next((d for d in detections if d[0] == 'hp'), None)
            if hp_box:
                try:
                    player_hp = self.get_box_text(frame, hp_box)
                except Exception as e:
                    print(f"[血量识别异常] {e}")
            # 识别金币
            money_box = next((d for d in detections if d[0] == 'money'), None)
            if money_box:
                try:
                    player_gold = self.get_box_text(frame, money_box)
                except Exception as e:
                    print(f"[金币识别异常] {e}")
            long_buttons = [d for d in detections if d[0] == 'long_button']
            # 需要对 long_button 按 y 排序，但要注意 click_box_by_label 需要原始索引
            if long_buttons:
                print("Event options:")
                # 记录原始索引和y坐标
                long_buttons = [(i, d, d[2]) for i, d in enumerate(long_buttons) if d[0] == 'long_button']
                # 按y排序
                long_buttons.sort(key=lambda x: x[2])
                options = []
                for display_idx, (orig_idx, d, _) in enumerate(long_buttons):
                    text = self.get_box_text(frame, d)
                    print(text)
                    options.append((orig_idx, text))
                # AI决策
                ai_prompt = {
                    "system": "你是杀戮尖塔事件选项助手，请根据以下选项，返回你要选择的编号（只返回数字，不要解释）：",
                    "options": [text for _, text in options],
                    "player_hp": player_hp,
                    "player_gold": player_gold
                }
                print(ai_prompt)
                while True:
                    try:
                        ai_response = self.get_box_text.__self__.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
                        break
                    except Exception as e:
                        if '429' in str(e) or 'rate limit' in str(e).lower():
                            print("[AI限流] 等待10秒后重试...")
                            time.sleep(10)
                        else:
                            print(f"[AI请求异常] {e}")
                            time.sleep(5)
                idx_str = ai_response.msg.content.strip()
                print(f"AI选择: {idx_str}")
                # 兼容AI返回json或纯数字
                match = re.search(r'"choice"\s*:\s*(\d+)', idx_str)
                if match:
                    idx = int(match.group(1))
                else:
                    idx_digits = ''.join(filter(str.isdigit, idx_str))
                    idx = int(idx_digits) if idx_digits else 1
                activate_game_window()
                orig_idx = long_buttons[idx-1][0]
                self.click_box_by_label('long_button', index=orig_idx, frame=frame, detections=detections)
                self.capture.move_to_edge()
                continue
            if 'energy_state' in labels:
                print("Event ended, switching to battle scene.")
                return
            if 'loot' in labels:
                print("Switching to loot selection phase.")
                choose_loot_phase(self, frame, detections)
                return
            if 'card_back' in labels:
                print("Match and Keep phase detected. (Not implemented, will exit if no card_back)")
                self.match_and_keep_phase(frame, detections)
                continue
            if 'card' in labels:
                print("Deck selection phase in event.")
                # 获取唯一 button 的 text
                button_boxes = [d for d in detections if d[0] == 'button']
                button_text = None
                if len(button_boxes) == 1:
                    try:
                        button_text = self.get_box_text(frame, button_boxes[0])
                    except Exception:
                        button_text = None
                deck_selection_phase(self, frame, detections, button_text=button_text)
                return
            buttons = [d for d in detections if d[0] == 'button']
            if len(buttons) == 1 and buttons[0][1] > 20:  # 假设 eps 为 0.1
                # 如果只有 1 个 button 且该 button x1 坐标大于 eps 则点击按钮
                print("Clicking button in event.")
                self.click_box_by_label('button', index=0, frame=frame, detections=detections)
                continue
            print("Event ended, returning to map.")
            return
import time
import json
import cv2
from annotator.game_capture import activate_game_window
from game.phase_common import choose_loot_phase, deck_selection_phase
from info_reader.hand_card_reader import read_card
from info_reader.relic_info_reader import read_relic_info
from info_reader.potion_info_reader import read_potion_info
from cleaner import Cleaner
class ShopHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label,bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label
        self.bot=bot

    def handle_shop(self, frame, detections):
        # 先点击 merchant
        self.click_box_by_label('merchant', index=0, frame=frame, detections=detections)
        self.capture.move_to_edge()
        while True:
            time.sleep(5)
            frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(frame)
            # 识别玩家金钱
            money_box = next((d for d in detections if d[0] == 'money'), None)
            money = None
            if money_box is not None:
                # 修改money区域截图：左边界右移45%，下边界和右边界略微扩大
                mx1, my1, mx2, my2 = money_box[1:5]
                w = mx2 - mx1
                h = my2 - my1
                new_mx1 = int(mx1 + w * 0.45)
                new_mx2 = min(mx2 + int(w * 0.08), frame.shape[1])  # 右边界扩大8%
                new_my2 = min(my2 + int(h * 0.12), frame.shape[0])  # 下边界扩大12%
                import os
                os.makedirs('figure', exist_ok=True)
                cv2.imwrite('figure/money_box.png', frame[my1:new_my2, new_mx1:new_mx2])
                money_text = self.get_box_text(frame, (money_box[0], new_mx1, my1, new_mx2, new_my2))
                try:
                    money = int(''.join(filter(str.isdigit, money_text)))
                except:
                    money = None
                print("money=",money)
            # 识别所有 price
            price_boxes = [(i, d) for i, d in enumerate(detections) if d[0] == 'price']
            goods = []
            for price_idx, price_box in price_boxes:
                px1, py1, px2, py2 = price_box[1:5]
                # 找到横坐标与其相交，纵坐标在其上方且最近的一个标签
                candidates = []
                for i, d in enumerate(detections):
                    if d[0] in ('card', 'relic', 'potion', 'card_removal_service'):
                        dx1, dy1, dx2, dy2 = d[1:5]
                        if dx2 > px1 and dx1 < px2 and dy2 <= py1:
                            candidates.append((i, d, abs(py1 - dy2)))
                if not candidates:
                    continue
                # 最近的
                best = min(candidates, key=lambda x: x[2])
                label = best[1][0]
                info = ''
                if label == 'card':
                    info = read_card(frame[best[1][2]:best[1][4], best[1][1]:best[1][3]])
                elif label == 'relic':
                    info = read_relic_info(self.capture, self.model, best[1])
                elif label == 'potion':
                    info = read_potion_info(self.capture, self.model, best[1])
                elif label == 'card_removal_service':
                    info = 'card removal service'
                else:
                    assert False
                price = self.get_box_text(frame, price_box)
                goods.append({'type': label, 'info': info, 'price': price, 'idx': best[0], 'price_idx': price_idx})
            print(f'Your money: {money}')
            for i, g in enumerate(goods):
                print(f'{i+1}. [{g["type"]}] {g["info"]} - Price: {g["price"]}')
            print(f'{len(goods)+1}. [leave] 0 leave - Price: 0')


            lines = []
            # Add money line
            lines.append(f"Your money: {money}")
            # Add each item in goods
            for i, g in enumerate(goods):
                lines.append(f'{i+1}. [{g["type"]}] {g["info"]} - Price: {g["price"]}')
            # Add "Leave shop" option
            lines.append(f'{len(goods)+1}. [leave] 0 leave - Price: 0')
            # Join all lines with '\n' into a single string
            text= '\n'.join(lines)

            # 输出信息收集
            output_lines = []
            output_lines.append(f"Your money: {money}")
            for i, g in enumerate(goods):
                output_lines.append(f'{i+1}. [{g["type"]}] {g["info"]} - Price: {g["price"]}')
            output_lines.append(f'{len(goods)+1}. [leave] 0 leave - Price: 0')
            text = '\n'.join(output_lines)

            # 用AI决策
            ai_prompt = {
                "system": "你是杀戮尖塔自动商店助手，请根据以下商店信息和选项，返回你要选择的编号（只返回数字，不要解释）：",
                "rule": "如果没有很好的牌，可以保存金币下来以后再用，另外钱不够的东西不能买",
                "shop_info": text
            }
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
            result = ai_response.msg.content.strip()
            print(f"AI选择: {result}")

            choice = int(result)
            activate_game_window()
            if choice == len(goods)+1:
                # 离开商店
                print('Leaving shop...')
                for _ in range(2):
                    frame2 = self.capture.wait_for_stable_frame()
                    detections2 = self.model.detect_all(frame2)
                    buttons = [d for d in detections2 if d[0] == 'button']
                    if buttons:
                        self.click_box_by_label('button', index=0, frame=frame2, detections=detections2)
                print('Exited shop scene.')
                return
            # 购买物品
            g = goods[choice-1]
            self.click_box_by_label(g['type'], index=len([d for d in detections[:g['idx']] if d[0]==g['type']]), frame=frame, detections=detections)
            self.capture.move_to_edge()
            activate_game_window()
            # 检查是否进入其他阶段
            frame2 = self.capture.wait_for_stable_frame()
            detections2 = self.model.detect_all(frame2)
            labels2 = [d[0] for d in detections2]
            if 'card_removal_service' not in labels2:
                if 'loot' in labels2:
                    print('Loot selection phase after purchase.')
                    choose_loot_phase(self, frame2, detections2)
                elif 'card' in labels2:
                    print('Deck selection phase after purchase.')
                    deck_selection_phase(self, frame2, detections2)
                else:
                    assert False
            print('Purchase finished, waiting for next action...')

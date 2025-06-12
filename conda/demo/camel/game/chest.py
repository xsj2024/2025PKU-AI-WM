import time
from annotator.game_capture import activate_game_window
from game.phase_common import choose_loot_phase, deck_selection_phase
from info_reader.relic_info_reader import read_relic_info
import json
import re

class ChestHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label, bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label
        self.bot = bot

    def handle_chest(self, frame, detections):
        while True:
            time.sleep(2) # 等待加载跳过 按钮
            frame = self.capture.wait_for_stable_frame()
            import cv2
            cv2.imwrite("no_chest.png", frame)
            detections = self.model.detect_all(frame)
            labels = [d[0] for d in detections]
            print(labels)
            # 让AI决策是否打开宝箱
            print('Chest found. Open it? (y/n): ')
            ai_prompt = {
                "system": "你是杀戮尖塔自动宝箱助手，请根据当前信息，返回你要选择的操作（y表示打开，n表示跳过，只返回y或n，不要解释）：",
                "chest_labels": labels
            }
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
            choice = ai_response.msg.content.strip().lower()
            print(f"AI选择: {choice}")
            import re
            match = re.search(r'"action"\s*:\s*"?([yn])"?', choice)
            if match:
                choice = match.group(1)
            else:
                # 只取y或n
                if 'y' in choice:
                    choice = 'y'
                elif 'n' in choice:
                    choice = 'n'
                else:
                    choice = 'y'
            activate_game_window()
            if choice != 'y':
                print('Skipped chest.')
                self.click_box_by_label('button', index=0, frame=frame, detections=detections)
                return
            chest_name = 'chest' if 'chest' in labels else 'boss_chest'
            self.click_box_by_label(chest_name, index=0, frame=frame, detections=detections)
            frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(frame)
            labels = [d[0] for d in detections]
            # 检查 loot
            if 'loot' in labels:
                print('Loot selection phase in chest.')
                choose_loot_phase(self, frame, detections)
                return
            # 检查 relic
            elif 'relic' in labels and 'prompt' in labels:
                print('Relic selection phase in chest.')
                all_relics = [d for d in detections if d[0] == 'relic']
                # 找到 prompt 坐标，然后找出在 prompt 下方的 relic
                prompt_box = next((d for d in detections if d[0] == 'prompt'), None)
                boss_relics = [(i, d) for i, d in enumerate(all_relics) if d[4] > prompt_box[4]]
                print('Relics:')
                for i, d in enumerate(boss_relics):
                    info = read_relic_info(self.capture,self.model,d[1])
                    print(f'{i+1}. {info}')
                print('-1. Skip relic')
                # relic选择AI决策
                ai_prompt = {
                    "system": "你是杀戮尖塔自动遗物助手，请根据以下遗物信息，返回你要选择的编号（只返回数字，-1表示跳过，不要解释）：",
                    "relic_options": [read_relic_info(self.capture,self.model,d[1]) for i,d in enumerate(boss_relics)]
                }
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
                idx = ai_response.msg.content.strip()
                print(f"AI选择: {idx}")
                match = re.search(r'"action"\s*:\s*"?(-?\d+)"?', idx)
                if match:
                    idx = int(match.group(1))
                else:
                    digits = re.findall(r'-?\d+', idx)
                    idx = int(digits[0]) if digits else 1
                activate_game_window()
                if idx == -1:
                    print('Skipped relic selection.')
                    self.click_box_by_label('button', index=0, frame=frame, detections=detections)
                else:
                    self.click_box_by_label('relic', index=boss_relics[idx-1][0], frame=frame, detections=detections)
                    # relic后续检测
                    if True:
                        time.sleep(0.5)
                        frame2 = self.capture.wait_for_stable_frame()
                        detections2 = self.model.detect_all(frame2)
                        labels2 = [d[0] for d in detections2]
                        print(labels2)
                        if len([d for d in detections2 if d[0] == 'button' and frame.shape[1] - d[3] <= 20]) == 1:
                            print('Only one button detected after relic, clicking.')
                            self.click_box_by_label('button', index=0, frame=frame2, detections=detections2)
                            frame2 = self.capture.wait_for_stable_frame()
                            detections2 = self.model.detect_all(frame2)
                            labels2 = [d[0] for d in detections2]
                        if 'loot' in labels2:
                            print('Loot selection phase after relic.')
                            choose_loot_phase(self, frame2, detections2)
                            return
                        elif 'card' in labels2:
                            print('Deck selection phase after relic.')
                            deck_selection_phase(self, frame2, detections2)
            # 其它情况
            else:
                assert False, 'Unexpected chest scene without loot or relic.'
            # 等待出现 button，点击它
            while True:
                frame3 = self.capture.wait_for_stable_frame()
                detections3 = self.model.detect_all(frame3)
                buttons = [d for d in detections3 if d[0] == 'button']
                if buttons:
                    print('Exiting chest scene.')
                    self.click_box_by_label('button', index=0, frame=frame3, detections=detections3)
                    if chest_name == 'boss_chest':
                        time.sleep(5)
                    return
                time.sleep(0.2)

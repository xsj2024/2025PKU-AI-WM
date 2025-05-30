import time
from game.phase_common import choose_loot_phase, deck_selection_phase
from annotator import game_capture
from annotator.game_capture import activate_game_window

class EventHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label

    def match_and_keep_phase(self, frame, detections):
        while True:
            if not any(d[0] == 'card_back' for d in detections):
                print("No card_back found, exiting match and keep phase.")
                return
            frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(frame)

    def handle_event(self, frame, detections):
        while True:
            frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(frame)
            labels = [d[0] for d in detections]
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
                    options.append((orig_idx, text))
                    print(f"{display_idx+1}. {text}")
                idx = int(input("Choose an option (number): "))
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
                deck_selection_phase(self, frame, detections)
                return
            buttons = [d for d in detections if d[0] == 'button']
            if len(buttons) == 1 and buttons[0][1] > 20:  # 假设 eps 为 0.1
                # 如果只有 1 个 button 且该 button x1 坐标大于 eps 则点击按钮
                print("Clicking button in event.")
                self.click_box_by_label('button', index=0, frame=frame, detections=detections)
                continue
            print("Event ended, returning to map.")
            return
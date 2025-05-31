from text_reader.ascii_ocr import ascii_ocr
from annotator.game_capture import activate_game_window
from game.phase_common import card_selection_phase, choose_loot_phase, deck_selection_phase

class CampfireHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label

    def handle_campfire(self, frame, detections):
        while True:
            frame = self.capture.get_frame()
            detections = self.model.detect_all(frame)
            campfire_buttons = [d for d in detections if d[0] == 'campfire_button']
            print(campfire_buttons)
            if not campfire_buttons:
                print('No campfire buttons found, exiting campfire scene.')
                return
            # 识别每个 campfire_button 下方的文字
            options = []
            for idx, btn in enumerate(campfire_buttons):
                x1, y1, x2, y2 = btn[1:5]
                h = y2 - y1
                text_y1 = y2
                text_y2 = y2 + h // 2
                roi = frame[text_y1:text_y2, x1:x2]
                text = ascii_ocr(roi)
                options.append((idx, text))
            print('Campfire options:')
            for i, (idx, text) in enumerate(options):
                print(f'{i+1}. {text}')
            choice = int(input('Choose a campfire option (number): '))
            activate_game_window()
            btn_idx = options[choice-1][0]
            self.click_box_by_label('campfire_button', index=btn_idx, frame=frame, detections=detections)
            self.capture.move_to_edge()
            # 进入后判断场景
            if True:
                frame2 = self.capture.wait_for_stable_frame()
                detections2 = self.model.detect_all(frame2)
                labels = [d[0] for d in detections2]
                if 'prompt' in labels and 'card' in labels:
                    print('Card selection phase in campfire.')
                    card_selection_phase(self, frame2, detections2)
                elif 'prompt' in labels and 'loot' in labels:
                    print('Loot selection phase in campfire.')
                    choose_loot_phase(self, frame2, detections2)
                    return
                elif 'card' in labels:
                    print('Deck selection phase in campfire.')
                    deck_selection_phase(self, frame2, detections2)
                # 等待出现 button 后点击并退出
                for i in range(3):
                    frame3 = self.capture.wait_for_stable_frame()
                    detections3 = self.model.detect_all(frame3)
                    buttons = [d for d in detections3 if d[0] == 'button']
                    if buttons:
                        print('Exiting campfire scene.')
                        self.click_box_by_label('button', index=0, frame=frame3, detections=detections3)
                        return
                assert False, "No button found after campfire interaction, something went wrong."

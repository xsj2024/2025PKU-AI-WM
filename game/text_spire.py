import time
import cv2
import numpy as np
from game.battle import BattleHandler
from annotator import config
from annotator import game_capture
from annotator import model_manager
from text_reader import ascii_ocr
from annotator.config import Config

class TextSlayTheSpire:
    def __init__(self):
        self.capture = game_capture.GameCapture()
        self.model = model_manager.ModelManager()
        self.last_scene = None
        self.running = True
        self.battle_handler = BattleHandler(
            self.capture, self.model, self.get_box_text, self.click_box_by_label
        )

    def get_scene(self, detections):
        # Priority: long_button > chest/boss chest > monster > merchant/card_removal_service > button > map
        labels = [d[0] for d in detections]
        if 'long_button' in labels:
            return 'event'
        if 'chest' in labels or 'boss chest' in labels:
            return 'chest'
        if 'energy_state' in labels:
            return 'battle'
        if 'merchant' in labels or 'card_removal_service' in labels:
            return 'shop'
        if 'button' in labels:
            return 'campfire'
        return 'map'

    def run(self):
        print('Text-based Slay the Spire started.')
        self.capture.start_capture()
        try:
            while self.running:
                frame = self.capture.get_frame()
                if frame is None:
                    time.sleep(0.1)
                    continue
                detections = self.model.detect_all(frame)
                scene = self.get_scene(detections)
                if scene != self.last_scene:
                    print(f'--- Scene switched to: {scene} ---')
                    self.last_scene = scene
                if scene == 'battle':
                    self.battle_handler.handle_battle(frame, detections)
                # TODO: handle other scenes
                time.sleep(0.5)
        except KeyboardInterrupt:
            print('Exiting game...')
            self.capture.stop_capture()
            self.running = False

    def activate_game_window(self):
        game_capture.activate_game_window(Config.GAME_WINDOW_TITLE)

    # 保留 click_box_by_label 和 get_box_text 供 battle handler 使用
    def click_box_by_label(self, label, index=0, text=None, frame=None, detections=None):
        self.activate_game_window()
        if frame is None:
            frame = self.capture.get_frame()
        if detections is None:
            detections = self.model.detect_all(frame)
        matches = []
        for d in detections:
            if d[0] == label:
                if text:
                    if self.get_box_text(frame, d) == text:
                        matches.append(d)
                else:
                    matches.append(d)
        if not matches:
            print(f'[WARN] No box found for label {label}')
            return
        if index >= len(matches):
            print(f'[WARN] Not enough boxes for label {label}')
            return
        x1, y1, x2, y2 = matches[index][1:5]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        game_capture.move_mouse_in_window(cx, cy, window_title=Config.GAME_WINDOW_TITLE)
        import pyautogui
        pyautogui.click()
        time.sleep(0.2)

    def get_box_text(self, frame, detection):
        try:
            x1, y1, x2, y2 = detection[1:5]
            roi = frame[y1:y2, x1:x2]
            text = ascii_ocr.ascii_ocr(roi)
            return text.strip().lower()
        except Exception as e:
            print(f'[OCR ERROR] {e}')
            return ''

if __name__ == '__main__':
    import win32gui
    from annotator.config import Config

    # hwnd = win32gui.FindWindow(None, Config.GAME_WINDOW_TITLE)
    # win32gui.SetForegroundWindow(hwnd)
    game_capture.activate_game_window(Config.GAME_WINDOW_TITLE)
    # win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    game = TextSlayTheSpire()
    game.run()

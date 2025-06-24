import time
import numpy as np
from game.battle import BattleHandler
from game.event import EventHandler
from game.campfire import CampfireHandler
from game.chest import ChestHandler
from game.map import MapHandler 
from game.shop import ShopHandler
from annotator import game_capture
from annotator import model_manager
from text_reader import ascii_ocr
from annotator.config import Config
from slay import SlaytheSpire
from annotator.game_capture import activate_game_window
import annotator_map.model_manager
import pyautogui
import json
import sys

class TextSlayTheSpire:
    def __init__(self):
        self.capture = game_capture.GameCapture()
        print('Game capture initialized.')
        self.model = model_manager.ModelManager()
        print('Model manager initialized.')
        self.last_scene = None
        self.running = True
        
        self.bot=SlaytheSpire()
        print('Slay the Spire bot initialized.')
        self.battle_handler = BattleHandler(
            self.capture, self.model, self.get_box_text, self.click_box_by_label,self.bot
        )
        print('Battle handler initialized.')
        self.event_handler = EventHandler(
            self.capture, self.model, self.get_box_text, self.click_box_by_label, self.bot
        )
        self.campfire_handler = CampfireHandler(
            self.capture, self.model, self.get_box_text, self.click_box_by_label, self.bot
        )
        self.chest_handler = ChestHandler(
            self.capture, self.model, self.get_box_text, self.click_box_by_label, self.bot
        )
        self.map_handler = MapHandler(
            self.capture, annotator_map.model_manager.ModelManager(), self.get_box_text, self.click_box_by_label, self.bot
        )
        self.shop_handler = ShopHandler(
            self.capture, self.model, self.get_box_text, self.click_box_by_label,
            self.bot
        )
        print('Handlers initialized.')

    def get_scene(self, detections):
        # Priority: long_button > chest/boss chest > monster > merchant/card_removal_service > button > map
        labels = [d[0] for d in detections]
        if 'long_button' in labels:
            return 'event'
        if 'chest' in labels or 'boss_chest' in labels:
            return 'chest'
        if 'energy_state' in labels:
            return 'battle'
        if 'merchant' in labels or 'card_removal_service' in labels:
            return 'shop'
        if 'campfire_button' in labels:
            return 'campfire'
        if "legend" in labels:
            return 'map'
        return 'unknown'

    def run(self):
        print('Text-based Slay the Spire started.')
        self.capture.start_capture()
        try:
            while self.running:
                try:
                    frame = self.capture.get_frame()
                    if frame is None:
                        time.sleep(0.1)
                        continue
                    detections = self.model.detect_all(frame)
                    scene = self.get_scene(detections)
                    self.last_scene = scene
                    if scene == 'battle':
                        self.battle_handler.handle_battle(frame, detections)
                    elif scene == 'event':
                        self.event_handler.handle_event(frame, detections)
                    elif scene == 'campfire':
                        self.campfire_handler.handle_campfire(frame, detections)
                    elif scene == 'chest':
                        self.chest_handler.handle_chest(frame, detections)
                    elif scene == 'map':
                        time.sleep(1)
                        self.map_handler.handle_map(frame, detections)
                        self.capture.move_to_edge()  # 确保地图处理后鼠标不在游戏区域
                        time.sleep(1)
                    elif scene == 'shop':
                        self.shop_handler.handle_shop(frame, detections)
                    elif scene == 'unknown':
                        print('Unknown scene detected.')
                        continue
                    # TODO: handle other scenes
                except Exception as e:
                    print(f"[场景处理异常] {e}, 自动重试...")
                    import traceback
                    traceback.print_exc()
                    time.sleep(1)
                    continue
        except KeyboardInterrupt:
            print('Exiting game...')
            self.capture.stop_capture()
            self.running = False

    # 保留 click_box_by_label 和 get_box_text 供 battle handler 使用
    def click_box_by_label(self, label, index=0, text=None, frame=None, detections=None):
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
        pyautogui.click()

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
    from annotator.config import Config
    from game.ui import start_ui

    def main():
        activate_game_window()
        game = TextSlayTheSpire()
        game.run()

    start_ui(main)

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import cv2
import keyboard
import threading
from annotator.game_capture import GameCapture
from annotator.model_manager import ModelManager
from annotator.overlay import Overlay
from core.hand_card_reader import read_hand_cards
from core.unit_status_reader import read_unit_status
from core.deck_card_reader import get_card_list_screenshots

def main():
    capture = GameCapture()
    if not capture.find_game_window():
        print("游戏窗口未找到，请先启动游戏！")
        return
    capture.start_capture()
    model = ModelManager()
    overlay = Overlay(capture)
    cv2.namedWindow("Card Overlay")  # 显式创建窗口，允许调整大小
    print("窗口已定位，按 F1 识别手牌，F2 检测单位状态，F3 滚动卡牌识别，ESC 退出。")
    f1_last = False
    f2_last = False
    f3_last = False
    worker_thread = None
    def recognize_hand():
        print("识别手牌中...")
        cards = read_hand_cards(capture, model)
        for idx, card in enumerate(cards):
            print(f"Card {idx+1}: text={card['card_text']}, cost={card['cost_text']}")
        print("识别完成。按 F1 可再次识别。")
    def recognize_status():
        print("检测单位状态中...")
        status = read_unit_status(capture, model)
        for unit in status:
            print(unit)
        print("检测完成。按 F2 可再次检测。")
    def recognize_deck():
        print("识别牌组中...")
        cards = get_card_list_screenshots(capture, model)
        for idx, card in enumerate(cards):
            print(f"Deck Card {idx+1}: text={card['card_text']}, box={card['box']}")
        print(f"识别完成，共识别到 {len(cards)} 张卡牌。按 F3 可再次识别。")
    while True:
        frame = capture.get_frame()
        if frame is None:
            continue
        detections = model.detect_all(frame)
        # 转换为 overlay 需要的格式
        overlay_input = [
            {"box": [x1, y1, x2, y2], "label": label}
            for (label, x1, y1, x2, y2) in detections
        ]
        display_frame = overlay.update_overlay(frame, overlay_input)
        cv2.imshow("Card Overlay", display_frame)  # 恢复窗口显示
        key = cv2.waitKey(10)
        if key == 27:  # ESC
            break
        f1_now = keyboard.is_pressed('f1')
        f2_now = keyboard.is_pressed('f2')
        f3_now = keyboard.is_pressed('f3')
        if (f1_now and not f1_last) and (worker_thread is None or not worker_thread.is_alive()):
            worker_thread = threading.Thread(target=recognize_hand)
            worker_thread.start()
        elif (f2_now and not f2_last) and (worker_thread is None or not worker_thread.is_alive()):
            worker_thread = threading.Thread(target=recognize_status)
            worker_thread.start()
        elif (f3_now and not f3_last) and (worker_thread is None or not worker_thread.is_alive()):
            worker_thread = threading.Thread(target=recognize_deck)
            worker_thread.start()
        f1_last = f1_now
        f2_last = f2_now
        f3_last = f3_now
    cv2.destroyAllWindows()  # 恢复窗口关闭
    keyboard.unhook_all()

if __name__ == '__main__':
    main()

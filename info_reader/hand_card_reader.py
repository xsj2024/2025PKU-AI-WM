import keyboard
import numpy as np
from annotator import game_capture
from annotator.model_manager import ModelManager
from text_reader.ascii_ocr import ascii_ocr

# 可选：你可以根据实际情况更换为更强的OCR方法

def ioA(boxA, boxB):
    # box: [x1, y1, x2, y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)
    if interArea == 0:
        return 0.0
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    iou = interArea / float(boxAArea)
    return iou

def read_card(card_img):
    card_text = ascii_ocr(card_img)
    return card_text

def read_hand_cards(capture, model):
    # 先将鼠标移动到游戏窗口中央
    capture.move_mouse_to_center()
    hand_cards = []
    key_list = ['1','2','3','4','5','6','7','8','9','0']
    for key in key_list:
        # 按下数字键，等待动画展示
        keyboard.press_and_release(key)
        frame = capture.wait_for_stable_frame()
        if frame is None:
            continue
        detections = model.detect_all(frame)
        card_box = None
        for det in detections:
            label, x1, y1, x2, y2 = det
            if label == 'card':
                card_box = (x1, y1, x2, y2)
                break
        if card_box is None:
            # try again
            frame = capture.wait_for_stable_frame()
            detections = model.detect_all(frame)
            card_box = None
            for det in detections:
                label, x1, y1, x2, y2 = det
                if label == 'card':
                    card_box = (x1, y1, x2, y2)
                    break
        if not (card_box is None):
            # 截取 card 区域图片
            x1, y1, x2, y2 = card_box
            card_img = frame[y1:y2, x1:x2]
            hand_cards.append(read_card(card_img))
        # 再次按下数字键收回手牌
        keyboard.press_and_release(key)
    return hand_cards

# 用于测试
if __name__ == '__main__':
    cards = read_hand_cards()
    for idx, card in enumerate(cards):
        print(f"Card {idx+1}: text={card['card_text']}, cost={card['cost_text']}")

import cv2
import keyboard
import time
import numpy as np
from annotator.game_capture import GameCapture
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

def read_hand_cards(capture, model):
    hand_cards = []
    key_list = ['1','2','3','4','5','6','7','8','9','0']
    for key in key_list:
        # 按下数字键，等待动画展示
        keyboard.press_and_release(key)
        time.sleep(0.6)  # 适当延迟，确保动画完成
        frame = capture.get_frame()
        if frame is None:
            continue
        detections = model.detect_all(frame)
        card_box = None
        cost_box = None
        for det in detections:
            label, x1, y1, x2, y2 = det
            if label == 'card':
                card_box = (x1, y1, x2, y2)
                break
        if card_box is None:
            # try again
            time.sleep(0.5)
            detections = model.detect_all(frame)
            card_box = None
            cost_box = None
            for det in detections:
                label, x1, y1, x2, y2 = det
                if label == 'card':
                    card_box = (x1, y1, x2, y2)
                    break
        if not (card_box is None):
            # 找 cost 区域
            max_iou = 0
            for det in detections:
                label, x1, y1, x2, y2 = det
                if label == 'cost':
                    this_iou = ioA((x1, y1, x2, y2), card_box)
                    if this_iou > 0.6 and this_iou > max_iou:
                        max_iou = this_iou
                        cost_box = (x1, y1, x2, y2)
            # 截取 card 区域图片
            x1, y1, x2, y2 = card_box
            card_img = frame[y1:y2, x1:x2]
            # # 保存手牌图片为对应数字.png
            # cv2.imwrite(f"{key}.png", card_img)
            card_text = ascii_ocr(card_img)
            # 去除首项为数字或大写字母 'X'
            if card_text and (card_text[0].isdigit() or card_text[0] == 'X'):
                card_text = card_text[1:]
            cost_text = None
            if cost_box is not None:
                cx1, cy1, cx2, cy2 = cost_box
                cost_img = frame[cy1:cy2, cx1:cx2]
                cost_text = ascii_ocr(cost_img)
            hand_cards.append({
                'card_text': card_text,
                'cost_text': cost_text,
                'card_box': card_box,
                'cost_box': cost_box
            })
        # 再次按下数字键收回手牌
        keyboard.press_and_release(key)
    return hand_cards

# 用于测试
if __name__ == '__main__':
    cards = read_hand_cards()
    for idx, card in enumerate(cards):
        print(f"Card {idx+1}: text={card['card_text']}, cost={card['cost_text']}")

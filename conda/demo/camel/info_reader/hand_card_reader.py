import keyboard
import numpy as np
from annotator import game_capture
from annotator.model_manager import ModelManager
import text_reader.easyocr_ as easyocr
from text_reader.ascii_ocr import ascii_ocr
import time

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

from image_matcher.img_matcher.card_matcher33 import get_card
def read_hand_cards(capture, model):
    frame = capture.wait_for_stable_frame()
    detections = model.detect_all(frame)
    cost = [d for d in detections if d[0]=='cost']
    upgraded = [d for d in detections if d[0]=='upgraded']
    res = []
    for d in detections:
        if d[0] == 'hand_card':
            label, x1, y1, x2, y2 = d
            name = get_card(frame[y1:y2, x1:x2])
            if upgraded:
                _, x11,y11,x22,y22 = upgraded[0]
                if min(x22,x2) - max(x11,x1) >= 0.5 * (x22 - x11):
                    name += '+'
                    upgraded = upgraded[1:]
            if cost:
                _, x11,y11,x22,y22 = cost[0]
                if x22 < (x1 + x2)/2:
                    c = easyocr.ascii_ocr(frame[y11:y22, x11:x22])
                    name = c + ' ' + name
                    cost = cost[1:]
            
            res.append(name)
    return res

def parse_hand_card(card_list):
    """
    将 hand_card 形如 ['1 Red Defend', ...] 的列表，整理成 [{'cost': '1', 'name': 'Defend'}, ...]
    规则：第一个是费用数字，第二个如果是颜色（Red/Green/Blue/Purple）就跳过，接下来的是名字
    """
    color_set = {"Red", "Green", "Blue", "Purple"}
    result = []
    for card in card_list:
        parts = card.split()
        if not parts:
            continue
        cost = parts[0]
        if len(parts) >= 3 and parts[1] in color_set:
            name = ' '.join(parts[2:])
        else:
            name = ' '.join(parts[1:])
        result.append({'cost': cost, 'name': name})
    return result

# 用于测试
if __name__ == '__main__':
    cards = read_hand_cards()
    for idx, card in enumerate(cards):
        print(f"Card {idx+1}: text={card['card_text']}, cost={card['cost_text']}")

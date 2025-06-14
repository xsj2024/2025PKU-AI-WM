import time
from annotator.game_capture import move_mouse_in_window
from text_reader.ascii_ocr import ascii_ocr
import numpy as np


import random
def read_relic_info(capture, model, relic_box):
    """
    将鼠标移动到指定遗物(relic_box)上，等待一段时间，返回 message_box 区域的文字信息。
    relic_box: [label, x1, y1, x2, y2, ...]
    """
    x1, y1, x2, y2 = relic_box[1:5]
    # 移动到遗物中心
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    move_mouse_in_window(cx, cy)

    while True:
        time.sleep(0.1)  # 等待信息显示
        frame = capture.get_frame()
        detections = model.detect_all(frame)
        msg_box = next((d for d in detections if d[0] == 'message_box'), None)
        if msg_box is None:
            # 随机微小扰动鼠标位置再试
            dx = random.randint(-5, 5)
            dy = random.randint(-5, 5)
            move_mouse_in_window(cx + dx, cy + dy)
            continue
        mx1, my1, mx2, my2 = msg_box[1:5]
        roi = frame[my1:my2, mx1:mx2]
        text = ascii_ocr(roi)
        return text

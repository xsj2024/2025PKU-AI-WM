import time
import pyautogui
from annotator.model_manager import ModelManager
from annotator.game_capture import GameCapture, move_mouse_in_window
from text_reader.ascii_ocr import ascii_ocr
import cv2

def get_center(box):
    x1, y1, x2, y2 = box
    return int((x1 + x2) / 2), int((y1 + y2) / 2)

def box_center(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) // 2, (y1 + y2) // 2

def center_distance(boxA, boxB):
    ax, ay = box_center(boxA)
    bx, by = box_center(boxB)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5

def box_min_dist(boxA, boxB):
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB
    # 计算水平和垂直方向的最近距离
    dx = max(bx1 - ax2, ax1 - bx2, 0)
    dy = max(by1 - ay2, ay1 - by2, 0)
    return (dx ** 2 + dy ** 2) ** 0.5

def read_unit_status(capture, model):
    frame = capture.get_frame()
    detections = model.detect_all(frame)
    units = []
    h, w = frame.shape[:2]
    dist_thresh = max(h, w) / 10
    for label, x1, y1, x2, y2 in detections:
        if label in ("player", "monster"):
            units.append({"label": label, "box": (x1, y1, x2, y2)})
    result = []
    for unit in units:
        cx, cy = get_center(unit["box"])
        move_mouse_in_window(cx, cy, window_title='Slay the Spire', speed=1000)
        import time
        time.sleep(0.1)
        frame2 = capture.get_frame()
        det2 = model.detect_all(frame2)
        msg_boxes = []
        for l2, xx1, yy1, xx2, yy2 in det2:
            if l2 == "message_box":
                msg_boxes.append((xx1, yy1, xx2, yy2))
        messages = []
        for mb in msg_boxes:
            x1, y1, x2, y2 = mb
            roi = frame2[y1:y2, x1:x2]
            text = ascii_ocr(roi)
            messages.append(text)
        result.append({
            "unit_label": unit["label"],
            "unit_box": unit["box"],
            "messages": messages
        })
    return result
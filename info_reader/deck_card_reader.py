import time
import cv2
import pyautogui
from annotator.model_manager import ModelManager
from annotator.game_capture import GameCapture
from text_reader.ascii_ocr import ascii_ocr

def get_card_list_screenshots(capture, model, max_scroll=50, sleep_time=0.5):
    """
    自动滚动并识别所有牌组界面卡牌。
    每次滚动五分之屏幕高度的距离。
    若最低卡牌y2上升或出现新卡牌则继续滑动，否则停止。
    eps: 若最低卡牌y2变化小于该值，认为未移动。
    返回所有识别到的卡牌信息列表。
    """
    all_cards = []
    last_max_y2 = None
    # 获取屏幕高度
    screen_height = capture.get_frame().shape[0]
    print(capture.get_frame().shape)
    bottom = int(screen_height * (1 - 1/6))
    eps = int(screen_height / 100)
    print(bottom)
    # pyautogui.scroll 的单位不是像素，通常需要很大数值才有较大滚动幅度
    # 这里建议 scroll_step = screen_height * 2 或更大，实际效果需根据游戏窗口微调
    for scroll_idx in range(max_scroll):
        frame = capture.get_frame()
        detections = model.detect_all(frame)
        card_boxes = [(x1, y1, x2, y2) for (label, x1, y1, x2, y2) in detections if label == 'card' and y2 <= bottom]
        if not card_boxes:
            pyautogui.scroll(-1)
            time.sleep(sleep_time)
            continue
        max_y2 = max([y2 for (x1, y1, x2, y2) in card_boxes])
        # 记录新出现的卡牌（y2大于上次最大y2的卡牌）
        new_row_boxes = [box for box in card_boxes if last_max_y2 is None or box[3] > last_max_y2 + eps]
        if new_row_boxes:
            # 按y坐标分组，组内x排序，组间y排序
            new_row_boxes.sort(key=lambda b: (b[1]//eps, b[0]))
            # 按y分组
            grouped = []
            for box in new_row_boxes:
                if not grouped or abs(box[1] - grouped[-1][0][1]) > eps:
                    grouped.append([box])
                else:
                    grouped[-1].append(box)
            # 组间按y排序，组内按x排序
            for group in grouped:
                group.sort(key=lambda b: b[0])
            grouped.sort(key=lambda g: g[0][1])
            for group in grouped:
                for box in group:
                    x1, y1, x2, y2 = box
                    print(f"New card found: {box}")
                    card_img = frame[y1:y2, x1:x2]
                    card_text = ascii_ocr(card_img)
                    all_cards.append({'card_text': card_text, 'box': box})
            new_card_found = True
        else:
            new_card_found = False
        # 判断是否需要继续滑动
        print(f"Scroll {scroll_idx + 1}/{max_scroll}: max_y2={max_y2}, last_max_y2={last_max_y2}, new_card_found={new_card_found}")
        if last_max_y2 is not None:
            if max_y2 + eps < last_max_y2 or new_card_found:
                # 最低卡牌上升或出现新卡牌，继续滑动
                pass
            else:
                # 最低卡牌未移动且无新卡牌，停止
                break
        last_max_y2 = max_y2
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
        time.sleep(sleep_time)
    return all_cards

if __name__ == '__main__':
    capture = GameCapture()
    if not capture.find_game_window():
        print("游戏窗口未找到，请先启动游戏！")
        exit(1)
    capture.start_capture()
    model = ModelManager()
    print("开始识别所有牌组卡牌...")
    cards = get_card_list_screenshots(capture, model)
    for idx, card in enumerate(cards):
        print(f"Card {idx+1}: text={card['card_text']}, box={card['box']}")
    print(f"共识别到 {len(cards)} 张卡牌。")

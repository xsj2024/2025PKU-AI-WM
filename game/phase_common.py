from info_reader.hand_card_reader import read_card
from info_reader.deck_card_reader import get_card_list_screenshots
from annotator.game_capture import activate_game_window

def card_selection_phase(handle, frame, detections):
    card_boxes = [d for d in detections if d[0] == 'card']
    card_infos = []
    for i, d in enumerate(card_boxes):
        x1, y1, x2, y2 = d[1:5]
        roi = frame[y1:y2, x1:x2]
        info = read_card(roi)
        card_infos.append(info)
    for idx, info in enumerate(card_infos):
        print(f'{idx+1}. {info}')
    skip_idx = None
    button_boxes = [d for d in detections if d[0] == 'button']
    for b in button_boxes:
        if handle.get_box_text(frame, b) == 'skip':
            skip_idx = len(card_infos) + 1
            print(f'{skip_idx}. Skip')
    choice = int(input('Choose a card (number): '))
    activate_game_window()
    if skip_idx and choice == skip_idx:
        handle.click_box_by_label('button', index=0, text='skip', frame=frame, detections=detections)
    else:
        handle.click_box_by_label('card', index=choice-1, frame=frame, detections=detections)

def choose_loot_phase(handle, frame, detections):
    while True:
        loot_boxes = [d for d in detections if d[0] == 'loot']
        loot_with_index = [(i, d) for i, d in enumerate(loot_boxes)]
        loot_with_index.sort(key=lambda x: x[1][2])
        has_two_choose_one = any(d[0] == 'two choose one' for d in detections)
        print("choose your loots, or -1 to skip" + (" (You can only choose one of the last two loots)" if has_two_choose_one else ""))
        loot_infos = []
        for _, d in loot_with_index:
            info = handle.get_box_text(frame, d)
            loot_infos.append(info)
        for idx, info in enumerate(loot_infos):
            print(f'{idx+1}. {info}')
        choice = int(input('Choose a loot (number): '))
        activate_game_window()
        if choice == -1:
            print('Skipped loot selection.')
            handle.click_box_by_label('button', index=0, frame=frame, detections=detections)
            return
        original_index = loot_with_index[choice-1][0]
        handle.click_box_by_label('loot', index=original_index, frame=frame, detections=detections)
        handle.click_box_by_label('prompt', index=0, frame=frame, detections=detections)
        # 检查是否进入选牌
        # 等待新帧并检测是否有 card
        new_frame = handle.capture.wait_for_stable_frame()
        new_detections = handle.click_box_by_label.__self__.model.detect_all(new_frame)
        if any(d[0] == 'card' for d in new_detections):
            if any(d[0] == 'prompt' for d in new_detections):
                card_selection_phase(handle, new_frame, new_detections)
            else:
                deck_selection_phase(handle, new_frame, new_detections)
            frame = handle.capture.wait_for_stable_frame()
        else:
            frame = new_frame
        detections = handle.model.detect_all(frame)
            

import pyautogui
import time
from functools import cmp_to_key
def deck_selection_phase(handle, frame, detections):
    """
    公用卡牌选择阶段。支持多卡点击，自动检测退出。
    1. 先读取卡组信息，展示所有卡牌和索引，用户输入索引序列。
    2. 滚动到最顶，仿照 read_deck_card 的分组方式一行行检测卡牌，若索引在输入序列中则点击。
    3. 每次点击后判断：若出现两个 button，则点击右侧 button 并退出；若无 card 则退出。
    4. 所有索引点击完还未退出则报错。
    """
    deck_cards = get_card_list_screenshots(handle.capture, handle.model)
    print("Deck cards:")
    for i, card in enumerate(deck_cards):
        print(f"{i+1}: {card['card_text']}")
    print("Enter card indices to select (space separated, e.g. 1 3 5):")
    idxs = [int(x)-1 for x in input().strip().split()]
    activate_game_window()
    handle.capture.move_to_edge()
    idxs_set = set(idxs)
    # 向上滚动到最顶，直到最高卡牌y坐标变化小于eps
    last_min_y = None
    screen_height = frame.shape[0]
    eps = int(screen_height / 100)
    for _ in range(50):
        frame = handle.capture.wait_for_stable_frame()
        detections = handle.model.detect_all(frame)
        card_boxes = [d for d in detections if d[0] == 'card']
        if not card_boxes:
            break
        min_y = min(d[2] for d in card_boxes)
        if last_min_y is not None and abs(min_y - last_min_y) < eps:
            break
        last_min_y = min_y
        pyautogui.scroll(1)
        pyautogui.scroll(1)
        pyautogui.scroll(1)
    # 主循环：每次只处理新出现的卡牌
    last_max_y2 = None
    current_card_index = 0
    clicked_count = 0
    while True:
        frame = handle.capture.wait_for_stable_frame()
        detections = handle.model.detect_all(frame)
        buttons = [d for d in detections if d[0] == 'button']
        if len(buttons) == 2:
            right_btn = max(buttons, key=lambda d: d[1])
            handle.click_box_by_label('button', index=buttons.index(right_btn), frame=frame, detections=detections)
            print("Two buttons detected, clicked right button and exited card selection phase.")
            return
        if not any(d[0] == 'card' for d in detections):
            print("No more cards, exited card selection phase.")
            return
        if clicked_count >= len(idxs_set):
            assert False, "Clicked all indices but still in card selection phase, something went wrong."
            return
        bottom = int(screen_height * (1 - 1/6))
        card_boxes = [d for d in detections if d[0] == 'card']
        if not card_boxes:
            pyautogui.scroll(-1)
            continue

        card_boxes_sorted = [d for d in card_boxes if d[4] <= bottom]
        card_boxes_sorted.sort(key=cmp_to_key(lambda a,b: (a[1] < b[1]) if (abs(a[2] - b[2]) < eps) else (a[2] < b[2])))
        if last_max_y2 is not None:
            card_boxes_sorted = [d for d in card_boxes_sorted if d[4] - last_max_y2 > eps]
        # 应自定义一个比较函数，若 y 相差不超过 eps 就比较 x
        for box in card_boxes_sorted:
            if current_card_index in idxs_set:
                # for b in card_boxes:
                #     print(b)
                # print("_____________")
                # for b in card_boxes_sorted:
                #     print(b)
                idx_in_frame = card_boxes.index(box)
                handle.click_box_by_label('card', index=idx_in_frame, frame=frame, detections=detections)
                handle.capture.move_to_edge()
                clicked_count += 1
            current_card_index += 1
            print(current_card_index)
        if card_boxes:
            last_max_y2 = max(d[4] for d in card_boxes if d[4] <= bottom)
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)
        pyautogui.scroll(-1)

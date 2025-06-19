from info_reader.hand_card_reader import read_card
from info_reader.deck_card_reader import get_card_list_screenshots
from annotator.game_capture import activate_game_window
import json
from annotator_other import model_manager

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
    # 获取当前卡牌库前，按下D键进入deck
    import pyautogui
    pyautogui.press('d')
    deck_cards = get_card_list_screenshots(handle.capture, handle.model)
    deck_card_texts = [card['card_text'] for card in deck_cards]
    deck_info = "\n".join([f"{i+1}: {text}" for i, text in enumerate(deck_card_texts)])
    # 读取完卡组后，按下ESC退出deck
    pyautogui.press('esc')
    # AI输入替换人工输入
    options = [f'{idx+1}. {info}' for idx, info in enumerate(card_infos)]
    if skip_idx:
        options.append(f'{skip_idx}. Skip')
    ai_prompt = {
        "system": "你是杀戮尖塔自动选牌助手，请根据以下选项，返回你要选择的编号、选择原因，并输出目前卡牌库中有哪些卡牌（格式：编号，原因: ...，卡牌库: ...，只返回一行，不要解释）：",
        "card_options": options,
        "deck_cards": deck_info
    }
    # --- 增加自动重试 ---
    while True:
        try:
            ai_response = handle.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
            break
        except Exception as e:
            if '429' in str(e) or 'rate limit' in str(e).lower():
                print("[AI限流] 等待10秒后重试...")
                import time
                time.sleep(10)
            else:
                print(f"[AI请求异常] {e}")
                import time
                time.sleep(5)
    ai_result = ai_response.msg.content.strip()
    print(f"AI选择: {ai_result}")
    import re
    match = re.search(r'(\-?\d+)[,，]\s*原因[:：]?([^,，]*)[,，]\s*卡牌库[:：]?(.*)', ai_result)
    if match:
        choice = int(match.group(1))
        reason = match.group(2).strip()
        deck_cards_ai = match.group(3).strip()
        print(f"AI决策原因: {reason}")
        print(f"AI识别卡牌库: {deck_cards_ai}")
    else:
        # fallback: 只提取编号
        digits = re.findall(r'-?\d+', ai_result)
        choice = int(digits[0]) if digits else 1
        reason = ''
        deck_cards_ai = ''
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
        print('-1. Skip')
        # AI输入替换人工输入
        options = [f'{idx+1}. {info}' for idx, info in enumerate(loot_infos)]
        options.append('-1. Skip')
        ai_prompt = {
            "system": "你是杀戮尖塔自动选奖励助手，请根据以下选项，返回你要选择的编号（只返回数字，不要解释）：",
            "loot_options": options
        }
        # --- 增加自动重试 ---
        while True:
            try:
                ai_response = handle.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
                break
            except Exception as e:
                if '429' in str(e) or 'rate limit' in str(e).lower():
                    print("[AI限流] 等待10秒后重试...")
                    time.sleep(10)
                else:
                    print(f"[AI请求异常] {e}")
                    time.sleep(5)
        ai_result = ai_response.msg.content.strip()
        print(f"AI选择: {ai_result}")
        import re
        match = re.search(r'"action"\s*:\s*"?(-?\d+)"?', ai_result)
        if match:
            choice = int(match.group(1))
        else:
            digits = re.findall(r'-?\d+', ai_result)
            choice = int(digits[0]) if digits else 1
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
            handle.click_box_by_label('prompt', index=0, frame=frame, detections=detections)
            frame = handle.capture.wait_for_stable_frame()
        else:
            frame = new_frame
        detections = handle.model.detect_all(frame)
            

import pyautogui
import time
from functools import cmp_to_key

from annotator.game_capture import GameCapture
def deck_selection_phase(handle, frame, detections, button_text=None):
    """
    公用卡牌选择阶段。AI只返回一个最优选择编号。
    1. 读取卡组信息，展示所有卡牌和索引，AI自动决策。
    2. 只允许选择一张卡。
    """
    deck_cards = get_card_list_screenshots(handle.capture, handle.model)
    eframe = handle.capture.wait_for_stable_frame()
    detections = model_manager.ModelManager().detect_all(eframe)
    output_lines = ["Deck cards:"]
    for i, card in enumerate(deck_cards):
        output_lines.append(f"{i+1}: {card['card_text']}")
    output_lines.append("请选择你认为最优的一张卡牌编号：")
    ai_prompt = {
        "system": "你是杀戮尖塔自动选牌助手，请根据以下卡牌列表，返回你要选择的最优卡牌编号和理由（格式：数字，理由: ...），你需要根据prompt_text的内容分析是要删牌还是升级牌之类的。",
        "deck_info": "\n".join(output_lines)
    }
        # 检查是否有 prompt 类别，提取其内容
    prompt_boxes = [d for d in detections if 'prompt' in d[0]]
    if prompt_boxes:
        prompt_text = handle.get_box_text(eframe, prompt_boxes[0])
        ai_prompt["prompt_text"] = prompt_text
    print(ai_prompt)
    # --- 增加自动重试 ---
    while True:
        try:
            ai_response = handle.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
            break
        except Exception as e:
            if '429' in str(e) or 'rate limit' in str(e).lower():
                print("[AI限流] 等待10秒后重试...")
                import time
                time.sleep(10)
            else:
                print(f"[AI请求异常] {e}")
                import time
                time.sleep(5)
    ai_result = ai_response.msg.content.strip()
    print(f"AI选择: {ai_result}")
    # 输出AI决策理由（如有）
    import re
    reason_match = re.search(r'理由[:：]?(.+)', ai_result)
    if reason_match:
        print(f"AI决策理由: {reason_match.group(1).strip()}")
    # 只取一个编号
    match = re.search(r'(\d+)', ai_result)
    idx= int(match.group(1)) - 1 if match else 0
    idxs = [idx]
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
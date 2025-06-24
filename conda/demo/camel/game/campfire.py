from text_reader.ascii_ocr import ascii_ocr
from annotator.game_capture import activate_game_window
from game.phase_common import card_selection_phase, choose_loot_phase, deck_selection_phase
import json
# ===== 引入typewriter美观输出 =====
from fight import typewriter

class CampfireHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label, bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label
        self.bot = bot

    def handle_campfire(self, frame, detections):
        while True:
            frame = self.capture.get_frame()
            detections = self.model.detect_all(frame)
            # --- 新增：识别血量 ---
            player_hp = None
            hp_box = next((d for d in detections if d[0] == 'hp'), None)
            if hp_box:
                try:
                    player_hp = self.get_box_text(frame, hp_box)
                except Exception as e:
                    typewriter(f"[血量识别异常] {e}")
            campfire_buttons = [d for d in detections if d[0] == 'campfire_button']
            if not campfire_buttons:
                typewriter('No campfire buttons found, exiting campfire scene.')
                return
            # 识别每个 campfire_button 下方的文字
            options = []
            for idx, btn in enumerate(campfire_buttons):
                x1, y1, x2, y2 = btn[1:5]
                h = y2 - y1
                text_y1 = y2
                text_y2 = y2 + h // 2
                roi = frame[text_y1:text_y2, x1:x2]
                text = ascii_ocr(roi)
                options.append((idx, text))
            typewriter('Campfire options:', color="#00e676")
            for i, (idx, text) in enumerate(options):
                typewriter(f'{i+1}. {text}', color="#00e676")
            # AI输入替换人工输入
            ai_prompt = {
                "system": "你是杀戮尖塔自动营火助手，请根据以下选项，返回你要选择的编号（只返回数字，不要解释）：\nrest 事件会恢复30%最大血量，smith 事件会选择一张牌升级，在血量充足的时候就不要选择rest了。",
                "campfire_options": [text for _, text in options],
                "player_hp": player_hp
            }
            # --- 增加自动重试 ---
            while True:
                try:
                    ai_response = self.bot.manager.agent.step(json.dumps(ai_prompt, ensure_ascii=False))
                    break
                except Exception as e:
                    if '429' in str(e) or 'rate limit' in str(e).lower():
                        typewriter("[AI限流] 等待10秒后重试...")
                        import time
                        time.sleep(10)
                    else:
                        typewriter(f"[AI请求异常] {e}")
                        import time
                        time.sleep(5)
            choice = ai_response.msg.content.strip()
            typewriter(f"AI选择: {choice}",color="#ffd600")
            try:
                btn_idx = options[int(choice)-1][0]
            except Exception:
                btn_idx = options[0][0]
            activate_game_window()
            self.click_box_by_label('campfire_button', index=btn_idx, frame=frame, detections=detections)
            self.capture.move_to_edge()
            # 进入后判断场景
            if True:
                frame2 = self.capture.wait_for_stable_frame()
                detections2 = self.model.detect_all(frame2)
                labels = [d[0] for d in detections2]
                if 'prompt' in labels and 'card' in labels:
                    typewriter('Card selection phase in campfire.')
                    card_selection_phase(self, frame2, detections2)
                elif 'prompt' in labels and 'loot' in labels:
                    typewriter('Loot selection phase in campfire.')
                    choose_loot_phase(self, frame2, detections2)
                    return
                elif 'card' in labels:
                    typewriter('Deck selection phase in campfire.')
                    deck_selection_phase(self, frame2, detections2)
                # 等待出现 button 后点击并退出
                for i in range(3):
                    frame3 = self.capture.wait_for_stable_frame()
                    detections3 = self.model.detect_all(frame3)
                    buttons = [d for d in detections3 if d[0] == 'button']
                    if buttons:
                        typewriter('Exiting campfire scene.')
                        self.click_box_by_label('button', index=0, frame=frame3, detections=detections3)
                        return
                assert False, "No button found after campfire interaction, something went wrong."

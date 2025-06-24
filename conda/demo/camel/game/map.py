from annotator.game_capture import activate_game_window
import time

class MapHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label,bot):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label

    def handle_map(self, frame, detections):
        while True:
            frames = []
            for i in range(10):
                frames.append(self.capture.get_frame())
            detections = None
            frame = None
            for frame in frames:
                detections = self.model.detect_all(frame)
                selectable_rooms = [d for d in detections if d[0] == 'selectable_room']
                if selectable_rooms:
                    print('Selectable room found, clicking the first one.')
                    self.click_box_by_label('selectable_room', index=0, frame=frame, detections=detections)
                    return
            retry_count = 0
            while 'boss_room' not in [d[0] for d in detections]:
                print('[地图识别] 未检测到boss_room，自动重试...')
                time.sleep(2)
                frame = self.capture.wait_for_stable_frame()
                detections = self.model.detect_all(frame)
                retry_count += 1
                if retry_count > 10:
                    raise RuntimeError('地图识别重试10次仍未检测到boss_room，请检查游戏画面或模型。')
            print('No selectable room, clicking boss room.')
            self.click_box_by_label('boss_room', index=0, frame=frame, detections=detections)
            return

from annotator.game_capture import activate_game_window

class MapHandler:
    def __init__(self, capture, model, get_box_text, click_box_by_label):
        self.capture = capture
        self.model = model
        self.get_box_text = get_box_text
        self.click_box_by_label = click_box_by_label

    def handle_map(self, frame, detections):
        while True:
            frame = self.capture.wait_for_stable_frame()
            detections = self.model.detect_all(frame)
            selectable_rooms = [d for d in detections if d[0] == 'selectable_room']
            if selectable_rooms:
                print('Selectable room found, clicking the first one.')
                self.click_box_by_label('selectable_room', index=0, frame=frame, detections=detections)
                return
            else:
                assert 'boss_room' in [d[0] for d in detections], "No boss room found in detections"
                print('No selectable room, clicking boss room.')
                self.click_box_by_label('boss_room', index=0, frame=frame, detections=detections)
                return

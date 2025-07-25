import cv2
import keyboard  # 使用keyboard库处理按键监听
import os
from .game_capture import GameCapture
from .annotation_tool import AnnotationTool
from .model_manager import ModelManager
from .overlay import Overlay
from .config import Config
import time
# import img_matcher.relic_matcher_Res50 as relic
# import img_matcher.card_matcher33 as card
class MainApplication:
    def __init__(self):
        # 初始化组件
        self.capture = GameCapture()
        self.model = ModelManager()
        self.annotator = AnnotationTool(self.model)
        self.overlay = Overlay(self.capture)
        
        # 状态标志
        self.running = True
        self.annotation_mode = False
        
        # 设置热键
        self._setup_hotkeys()
        cv2.namedWindow("Slay the Spire Overlay")
        cv2.setMouseCallback("Slay the Spire Overlay", self._handle_mouse_event)

        self.lock_frame = None

    def _handle_mouse_event(self, event, x, y, flags, param):
        """统一处理鼠标事件"""
        if self.annotation_mode:
            self.annotator.handle_mouse(event, x, y, flags)
        
    def _setup_hotkeys(self):
        """设置按键监听"""
        keyboard.add_hotkey('f1', self._relocate_window)
        keyboard.add_hotkey('f2', self._toggle_annotation_mode)
        keyboard.add_hotkey('f3', self.overlay.toggle_overlay)
        keyboard.add_hotkey('f4', self._start_training)  # 新增训练热键
    
    def _start_training(self):
        """启动训练"""
        if self.annotator.check_dataset_ready():
            print("Starting training process...")
            success = self.annotator.start_training()
            print("Training succeeded!" if success else "Training failed!")
            if success:
                self.model = ModelManager()
        else:
            samples = len(os.listdir(os.path.join(Config.YOLO_DATA_DIR_REAL, "images")))
            print(f"Insufficient data: {samples}/{Config.MIN_SAMPLES}")

    def _relocate_window(self):
        """重新定位游戏窗口"""
        print("Relocating game window...")
        if self.capture.find_game_window():
            print("Game window located successfully")
        else:
            print("Failed to locate game window")
    
    def _toggle_annotation_mode(self):
        """切换标注模式"""
        if self.annotation_mode:
            self._exit_annotation_mode()
        else:
            self._enter_annotation_mode()
    
    def _enter_annotation_mode(self):
        """进入标注模式 - 适配新版AnnotationTool"""
        if self.capture.current_frame is None:
            print("No frame available for annotation")
            return
            
        self.annotation_mode = True
        print("Entering annotation mode...")
        self.overlay.overlay_enabled = False  # 临时关闭悬浮层
        self.annotator.enter_annotation_mode()  # 激活标注工具
        
    def _exit_annotation_mode(self):
        """退出标注模式"""
        if self.annotation_mode:
            self.annotation_mode = False
            self.overlay.overlay_enabled = True
            self.annotator.exit_annotation_mode()  # 停用标注工具
            print("Exited annotation mode")
    
    def get_detections(self, detections, frame):
        res = []
        for result in detections:
            if result.boxes is None:
                continue
            
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy().astype(int)
            names = getattr(result, 'names', {})
            for box, conf, cls_id in zip(boxes, confs, cls_ids):
                box = list(map(int, box))
                info = {}
                info["box"] = box
                info["label"] = names.get(cls_id, cls_id)
                # if info["label"] == "relic":
                #     x, y, x1, y1 = box  # 矩形框坐标
                #     roi = frame[y:y1, x:x1]  # 截取矩形区域
                #     vv = relic.get_relic(roi)
                #     info["label"] = vv['name']
                # if info["label"] == "card":
                #     x, y, x1, y1 = box  # 矩形框坐标
                #     roi = frame[y:y1, x:x1]  # 截取矩形区域
                #     info["label"] = card.get_card(roi)
                info["conf"] = conf
                res.append(info)
        return res
                    
    def run(self):
        """主运行循环"""
        # 开始截图
        if not self.capture.find_game_window():
            print("游戏窗口未找到，请先启动游戏！")
            exit(0)        
        self.capture.start_capture()
        
        try:
            print("Start!")
            while self.running:
                frame = self.capture.get_frame()
                if frame is None: continue
                # 处理标注模式
                if self.annotation_mode:
                    if self.lock_frame is None:
                        self.lock_frame = frame.copy()
                        detections = self.model.detect_all(frame)
                        for result in detections:
                            if result.boxes is None:
                                continue
                            
                            boxes = result.boxes.xyxy.cpu().numpy()
                            # confs = result.boxes.conf.cpu().numpy()
                            cls_ids = result.boxes.cls.cpu().numpy().astype(int)
                            names = getattr(result, 'names', {})
                            
                            for box, cls_id in zip(boxes, cls_ids):
                                box = list(map(int,box))
                                name = names.get(cls_id, cls_id)
                                # print("AAAAAAA:")
                                # for j in box:
                                #     print(j)
                                # print(name)
                                self.annotator.annotations.append({
                                    "bbox": (box[0],box[1],box[2]-box[0],box[3]-box[1]),
                                    "label": name,
                                })

                    frame = self.lock_frame.copy()
                    display_frame, bbox, annotations = self.annotator.process_frame(frame)
                    if keyboard.is_pressed('enter') and bbox:
                        img_h, img_w = frame.shape[:2]
                        self.annotator.confirm_selection(img_h=img_h,img_w=img_w)
                    if key == ord('d') or key == ord('D'):
                        self.annotator.delete_selected_annotation()
                    if key == ord('q') or key == ord('Q'):
                        self.annotator.finalize_annotations(frame)
                        self._exit_annotation_mode()
                else:
                    self.lock_frame = None
                    # 正常检测模式（传递frame和detections）
                    detections = self.model.detect_all(frame)
                    detections = self.get_detections(detections, frame)
                    display_frame = self.overlay.update_overlay(frame, detections)
                # 显示统一窗口
                cv2.imshow("Slay the Spire Overlay", display_frame)
                key = cv2.waitKey(1)
                if key == 27:  # ESC退出
                    if self.annotation_mode:
                        self._exit_annotation_mode()
                    else:
                        self.running = False
        except KeyboardInterrupt:pass
        self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        self.capture.stop_capture()
        cv2.destroyAllWindows()
        keyboard.unhook_all()  # 移除所有键盘钩子
if __name__ == "__main__":
    
    # import os
    # os.environ['KMP_DUPLICATE_LIB_OK']='True'
    Config.load_class_name()
    app = MainApplication()
    app.run()
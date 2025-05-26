import cv2
import keyboard  # 使用keyboard库处理按键监听
import os
from game_capture import GameCapture
from annotation_tool import AnnotationTool
from model_manager import ModelManager
from overlay import Overlay
from config import Config
import shutil

# import ocr

def _handle_mouse_event(event, x, y, flags, param):
    """统一处理鼠标事件"""
    ann.handle_mouse(event, x, y, flags)
def Open(img_name):
    img_p = os.path.join(img_path, img_name)
    lab_name = img_name[:-3]+"txt"
    lab_p = os.path.join(lab_path, lab_name)
    global frame
    frame = cv2.imread(img_p)

    ann.enter_annotation_mode()

    bb = []
    if(open_mode == 1):
        detections = model.detect_all(frame)
        for result in detections:
            if result.boxes is None:
                continue
            
            boxes = result.boxes.xyxy.cpu().numpy()
            # confs = result.boxes.conf.cpu().numpy()
            cls_ids = result.boxes.cls.cpu().numpy().astype(int)
            names = getattr(result, 'names', {})
            
            for box, cls_id in zip(boxes, cls_ids):
                box = list(map(int,box))
                bb.append(box)
                name = names.get(cls_id, cls_id)
                # print("AAAAAAA:")
                # for j in box:
                #     print(j)
                # print(name)
                ann.annotations.append({
                    "bbox": (box[0],box[1],box[2]-box[0],box[3]-box[1]),
                    "label": name,
                })
        return
    else:
        data = []
        with open(lab_p,"r") as f:
            for s in f.readlines():
                l = s.split()
                data.append([eval(i) for i in l])
        # print(data)

        img_h, img_w = frame.shape[:2]
        for t in data:
            name = Config.query_class_name(t[0])
            t[1] *= img_w
            t[2] *= img_h
            t[3] *= img_w
            t[4] *= img_h
            t[1] -= t[3]/2
            t[2] -= t[4]/2
            t = list(map(int, t))
            bb.append((t[1],t[2],t[1]+t[3],t[2]+t[4]))
            ann.annotations.append({"bbox": (t[1],t[2],t[3],t[4]),
                                    "label": name})
    # res = ocr.get_text(frame)
    # for text in res:
    #     print(text)

def Close():
    ann.exit_annotation_mode()

def Update(img_name):
    # img_p = os.path.join(img_path, img_name)
    lab_name = img_name[:-3]+"txt"
    lab_p = os.path.join(lab_path, lab_name)
    img_h, img_w = frame.shape[:2]
    with open(lab_p,"w") as f:
        for i in ann.annotations:
            x,y,w,h = i['bbox']
            name = i['label']
            id = Config.query_class_id(name)

            x += w/2
            y += h/2
            x /= img_w
            w /= img_w
            y /= img_h
            h /= img_h

            f.write(f"{id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
def SAVE_ANOTHER(img_name):
    TEMP_PATH = os.path.join(Config.YOLO_DATA_DIR, "tempdata")
    shutil.copyfile(os.path.join(img_path, img_name), os.path.join(TEMP_PATH,"images",img_name))
    lab_name = img_name[:-3]+"txt"
    lab_p = os.path.join(os.path.join(TEMP_PATH,"labels"), lab_name)
    img_h, img_w = frame.shape[:2]
    with open(lab_p,"w") as f:
        for i in ann.annotations:
            x,y,w,h = i['bbox']
            name = i['label']
            id = Config.query_class_id(name)

            x += w/2
            y += h/2
            x /= img_w
            w /= img_w
            y /= img_h
            h /= img_h

            f.write(f"{id} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")
if __name__ == '__main__':
    Config.load_class_name()
    path = Config.YOLO_DATA_DIR_REAL
    img_path = os.path.join(path,"images")
    lab_path = os.path.join(path,"labels")
    try:
        l = [name for name in os.listdir(img_path)]
        assert l.__len__() > 0
    except:
        print("无数据")
        exit(0)
    
    model = ModelManager()
    open_mode = 0
    ann = AnnotationTool(None)
    cv2.namedWindow("Slay the Spire YOLODATA")
    cv2.setMouseCallback("Slay the Spire YOLODATA", _handle_mouse_event)

    frame = None
    Open(l[0])

    cur = 0

    while True:
        display_frame, bbox, annotations = ann.process_frame(frame)
        if keyboard.is_pressed('enter') and bbox:
            img_h, img_w = frame.shape[:2]
            ann.confirm_selection(img_h=img_h,img_w=img_w)
        cv2.imshow("Slay the Spire YOLODATA", display_frame)
        key = cv2.waitKey(1)
        if key == ord('d') or key == ord('D'):
            ann.delete_selected_annotation()
        if key == ord('q') or key == ord('Q'):
            Update(l[cur])
            print("已保存")
        if key == ord('g'):
            SAVE_ANOTHER(l[cur])
            print("已另存为")
        if key == 27:  # ESC退出
            break
        if key == ord('z'):
            if (cur == 0):
                cur = l.__len__() - 1
            else:
                cur -= 1
            print(f"往前切换到第 {cur} 张图片")
            Close()
            Open(l[cur])
        if key == ord('c'):
            if (cur == l.__len__() - 1):
                cur = 0
            else:
                cur += 1
            print(f"往后切换到第 {cur} 张图片")
            Close()
            Open(l[cur])
        if key == ord('f'):
            Close()
            if open_mode == 0:
                print("初始框切换为检测结果")
            else:
                print("初始框切换为数据结果")
            open_mode ^= 1
            Open(l[cur])
    cv2.destroyAllWindows()
    keyboard.unhook_all()  # 移除所有键盘钩子


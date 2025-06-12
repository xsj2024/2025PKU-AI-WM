import cv2
import numpy as np
import os
from .config import Config
class Overlay:
    def __init__(self, game_capture):
        self.capture = game_capture
        self.overlay_enabled = True
        
    def update_overlay(self, frame, detections):
        """彻底修正检测框偏移问题的最终版"""
        if frame is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)
        
        display_frame = frame.copy()
        
        if not self.overlay_enabled or not detections:
            return display_frame
        
        for res in detections:
            # 关键修正1：去除不必要的y1偏移
            box = res['box']
            label = res['label']
            x1, y1, x2, y2 = map(int, [
                max(0, box[0]),
                max(0, box[1]),
                min(frame.shape[1]-1, box[2]),
                min(frame.shape[0]-1, box[3])
            ])
            # print(x1,y1,x2,y2,frame.shape[0],frame.shape[1])
            # 立即绘制矩形（不再使用透明度叠加）
            cv2.rectangle(
                display_frame, 
                (x1, y1), (x2, y2),
                Config.OVERLAY_COLOR,
                Config.OVERLAY_THICKNESS,
                cv2.LINE_AA
            )
            
            # 标签处理
            (text_w, text_h), baseline = cv2.getTextSize(
                label, cv2.FONT_HERSHEY_SIMPLEX,
                Config.OVERLAY_FONT_SCALE,
                Config.OVERLAY_THICKNESS)
            
            # 关键修正2：精确计算文本位置
            text_bottom = y1  # 文本底部与框顶对齐
            text_top = text_bottom - text_h  # 文本顶部位置
            
            # 绘制标签背景（考虑基线偏移）
            bg_bottom = text_bottom + baseline
            cv2.rectangle(
                display_frame,
                (x1, text_top - 2),  # 上方多留2像素空隙
                (x1 + text_w, bg_bottom),
                Config.OVERLAY_COLOR,
                -1, cv2.LINE_AA
            )
            
            # 关键修正3：精确文本位置（考虑基线）
            cv2.putText(
                display_frame, label,
                (x1, text_bottom),  # 直接使用框顶y坐标
                cv2.FONT_HERSHEY_SIMPLEX,
                Config.OVERLAY_FONT_SCALE,
                (255, 255, 255),
                Config.OVERLAY_THICKNESS,
                cv2.LINE_AA
            )
        
        return display_frame

        
    def toggle_overlay(self):
        """开关悬浮显示"""
        self.overlay_enabled = not self.overlay_enabled
        if not self.overlay_enabled:
            cv2.destroyWindow("Slay the Spire Overlay")
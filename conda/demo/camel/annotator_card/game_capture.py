import pyautogui
import cv2
import numpy as np
import time
from threading import Thread
from .config import Config
class GameCapture:
    def __init__(self):
        self._running = False
        self.current_frame = None
        self.game_window = None
        
    def find_game_window(self):
        """定位游戏窗口"""
        try:
            windows = pyautogui.getWindowsWithTitle(Config.GAME_WINDOW_TITLE)
            if windows:
                self.game_window = windows[0]
                return True
            return False
        except Exception as e:
            print(f"Error finding game window: {e}")
            return False
            
    def start_capture(self):
        """开始持续截图"""
        if not self.find_game_window():
            raise Exception("Game window not found")
            
        self._running = True
        Thread(target=self._capture_loop, daemon=True).start()
        
    def _capture_loop(self):
        while self._running:
            try:
                if self.game_window.isActive:
                    # 获取窗口位置和尺寸
                    x, y, width, height = (
                        self.game_window.left,
                        self.game_window.top,
                        self.game_window.width,
                        self.game_window.height
                    )
                    
                    # 截图并转换为OpenCV格式
                    screenshot = pyautogui.screenshot(region=(x, y, width, height))
                    self.current_frame = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                    
            except Exception as e:
                print(f"Error during capture: {e}")
                
            time.sleep(Config.CAPTURE_INTERVAL)
            
    def stop_capture(self):
        """停止截图"""
        self._running = False
        
    def get_frame(self):
        """获取当前帧"""
        return self.current_frame.copy() if self.current_frame is not None else None
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

# 移动鼠标到窗口内坐标（窗口内容区左上角为原点）
def move_mouse_in_window(x, y, window_title='Slay the Spire', speed=1000):
    import pygetwindow as gw
    import pyautogui
    try:
        win = gw.getWindowsWithTitle(window_title)[0]
        win_x, win_y = win.left, win.top
    except Exception as e:
        print(f"[DEBUG] pygetwindow failed: {e}")
        win_x, win_y = 0, 0
    abs_x = win_x + x
    abs_y = win_y + y
    cur_x, cur_y = pyautogui.position()
    dist = ((cur_x - abs_x) ** 2 + (cur_y - abs_y) ** 2) ** 0.5
    duration = dist / speed if speed > 0 else 0.01
    pyautogui.moveTo(abs_x, abs_y, duration=duration)
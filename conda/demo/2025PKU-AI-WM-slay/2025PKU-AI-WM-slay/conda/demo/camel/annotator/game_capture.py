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
            print(f"Found {len(windows)} windows with title '{Config.GAME_WINDOW_TITLE}'")
            if windows:
                self.game_window = windows[0]
                return True
            return False
        except Exception as e:
            print(f"Error finding game window: {e}")
            return False
            
    def start_capture(self):
        """开始持续截图"""
        print("Starting game capture...")
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
        """获取当前帧，并将焦点切换到游戏窗口"""
        return self.current_frame.copy() if self.current_frame is not None else None
    def wait_for_stable_frame(self, max_wait=60, interval=0.15, threshold=3, min_count=5):
        """
        连续采集帧，直到画面变化低于阈值，返回稳定帧。
        :param capture: GameCapture 实例
        :param max_wait: 最大等待秒数
        :param interval: 帧间隔秒数
        :param threshold: 均值绝对差阈值
        :param min_count: 连续多少帧都低于阈值才算稳定
        :return: 一帧可用于识别的 np.ndarray
        """
        last_frame = None
        stable_count = 0
        start_time = time.time()
        while time.time() - start_time < max_wait:
            frame = self.get_frame()
            if frame is None:
                time.sleep(interval)
                continue
            if last_frame is not None:
                diff = np.abs(frame.astype(np.float32) - last_frame.astype(np.float32)).mean()
                if diff < threshold:
                    stable_count += 1
                    if stable_count >= min_count:
                        return frame
                else:
                    stable_count = 0
            last_frame = frame
            time.sleep(interval)
        return last_frame
    def move_mouse_to_center(self):
        """将鼠标移动到游戏窗口中心"""
        if not self.game_window:
            print("Game window not found")
            return
        center_x = self.game_window.width // 2
        center_y = self.game_window.height // 2
        # pyautogui.moveTo(center_x, center_y, duration=0.1)
        move_mouse_in_window(center_x, center_y)
    def move_to_edge(self):
        """移动到一个固定的不会遮挡关键信息的位置"""
        if not self.game_window:
            print("Game window not found")
            return
        # 这里假设移动到窗口左上角偏下的位置
        edge_x = 10
        # y 坐标为窗口高度一半
        edge_y = self.game_window.height // 2
        move_mouse_in_window(edge_x, edge_y)

# 移动鼠标到窗口内坐标（窗口内容区左上角为原点）
def move_mouse_in_window(x, y, window_title=Config.GAME_WINDOW_TITLE, speed=1000):
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
import win32gui, win32com.client
def activate_game_window():
    hwnd = win32gui.FindWindow(None, Config.GAME_WINDOW_TITLE)
    shell = win32com.client.Dispatch("WScript.Shell")
    shell.SendKeys('%')
    win32gui.SetForegroundWindow(hwnd)

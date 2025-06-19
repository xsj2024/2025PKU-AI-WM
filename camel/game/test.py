import win32gui
import win32con
import time

def activate_game_window(window_title="游戏窗口标题"):
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        raise Exception(f"错误：未找到窗口 '{window_title}'，请检查标题！")
    
    # 先恢复窗口（如果最小化）
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    # 再激活到前台
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.5)  # 等待窗口响应

# 调用示例
activate_game_window("Slay the Spire")  # 替换为你的窗口标题

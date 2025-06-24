import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QVBoxLayout, QWidget
from PyQt5.QtCore import QThread, QObject, pyqtSignal
from PyQt5 import QtGui

class EmittingStream(QObject):
    text_written = pyqtSignal(str, bool)
    def __init__(self):
        super().__init__()
        self._last_message_prefix = None
    def write(self, text):
        if text == "":
            return
        if "\r" in text:
            last = text.split("\r")[-1]
            self.text_written.emit(last, True)
        else:
            self.text_written.emit(text, False)
    def flush(self):
        pass

class GameThread(QThread):
    def __init__(self, game_entry_func):
        super().__init__()
        self.game_entry_func = game_entry_func
    def run(self):
        self.game_entry_func()

class MainWindow(QMainWindow):
    write_signal = pyqtSignal(str, object)  # str: text, object: color
    def __init__(self, game_entry_func):
        super().__init__()
        self.setWindowTitle("Slay the Spire AI 控制台")
        # 调整窗口为更小尺寸，并靠右下角显示，减少与游戏窗口重合
        self.resize(600, 320)  # 更小尺寸
        # 获取屏幕大小，设置窗口初始位置靠左上角
        screen = QApplication.primaryScreen().geometry()
        win_w, win_h = 600, 320
        margin = 40  # 离屏幕边缘留点距离
        self.move(margin, margin)
        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        self.text_edit.setStyleSheet(
            "QTextEdit { font-family: Consolas, 'Courier New', monospace; font-size: 15px; "
            "background: #23272e; color: #e6e6e6; padding: 8px; border-radius: 8px; }"
        )
        layout = QVBoxLayout()
        layout.addWidget(self.text_edit)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self._last_line_len = 0
        self._last_line_prefix = None

        # 用信号安全地重定向标准输出
        self.emitter = EmittingStream()
        self.emitter.text_written.connect(self.append_text)
        sys.stdout = self.emitter
        sys.stderr = self.emitter

        # 让 typewriter 可直接用 sys.ui_stream.write(char, color)
        sys.ui_stream = self

        # 启动游戏线程
        self.game_thread = GameThread(game_entry_func)
        self.game_thread.start()

        self.write_signal.connect(self._write_on_main_thread)

    def write(self, text, color=None):
        self.write_signal.emit(text, color)
    def _write_on_main_thread(self, text, color):
        self.append_text(text, overwrite=False, color=color)

    def flush(self):
        pass

    def append_text(self, text, overwrite=False, color=None):
        cursor = self.text_edit.textCursor()
        # 颜色判断
        if color is None:
            color = "#e6e6e6"  # 默认灰色
            if text.startswith("[AI]"):
                color = "#00e676"  # 绿色
                text = text[4:].lstrip()
            elif text.startswith("[SYS]"):
                color = "#42a5f5"  # 蓝色
                text = text[5:].lstrip()
        self.text_edit.setTextColor(QtGui.QColor(color))
        if overwrite:
            # 只替换最后一行的symbol部分，保留前缀
            self.text_edit.moveCursor(cursor.End)
            self.text_edit.moveCursor(cursor.StartOfLine, cursor.KeepAnchor)
            last_line = self.text_edit.textCursor().selectedText()
            if self._last_line_prefix is None:
                if ' ' in last_line:
                    prefix = last_line.rsplit(' ', 1)[0]
                else:
                    prefix = last_line
                self._last_line_prefix = prefix
            prefix = self._last_line_prefix or ''
            new_line = prefix + ' ' + text[-1] if prefix and text else text
            self.text_edit.textCursor().removeSelectedText()
            self.text_edit.textCursor().deletePreviousChar()
            pad = max(0, self._last_line_len - len(new_line))
            self.text_edit.insertPlainText(new_line + ' ' * pad)
            self.text_edit.setTextColor(QtGui.QColor("#e6e6e6"))
            self._last_line_len = len(new_line)
        else:
            self.text_edit.insertPlainText(text)
            self.text_edit.setTextColor(QtGui.QColor("#e6e6e6"))
            if text.endswith('\n'):
                self._last_line_len = 0
                self._last_line_prefix = None
            else:
                if ' ' in text:
                    self._last_line_prefix = text.rsplit(' ', 1)[0]
                else:
                    self._last_line_prefix = text
                self._last_line_len = len(text)
        self.text_edit.moveCursor(self.text_edit.textCursor().End)

def start_ui(game_entry_func):
    app = QApplication(sys.argv)
    window = MainWindow(game_entry_func)
    window.show()
    sys.exit(app.exec_())

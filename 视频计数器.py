import tkinter as tk
from tkinter import messagebox
import keyboard
import threading
import time
import json
import os
import sys
import wave
import struct
import tempfile
from datetime import datetime
try:
    import winsound
    HAS_WINSOUND = True
except:
    HAS_WINSOUND = False

def make_tick_wav():
    tmp_dir = tempfile.gettempdir()
    tick_path = os.path.join(tmp_dir, "video_counter_tick.wav")
    if os.path.exists(tick_path):
        return tick_path
    framerate = 22050
    duration = 0.12
    freq = 2200
    nframes = int(framerate * duration)
    wf = wave.open(tick_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(framerate)
    for i in range(nframes):
        t = i / framerate
        s = 0.35 * 32767 * abs((t * freq * 2 * 3.14159265) % 6.2831853 - 3.14159265) / 3.14159265
        val = int(s)
        wf.writeframes(struct.pack('<h', val))
    wf.close()
    return tick_path

def make_alert_wav():
    tmp_dir = tempfile.gettempdir()
    alert_path = os.path.join(tmp_dir, "video_counter_alert.wav")
    if os.path.exists(alert_path):
        return alert_path
    framerate = 22050
    duration = 1.0
    freq_start = 600
    freq_end = 1600
    nframes = int(framerate * duration)
    wf = wave.open(alert_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(framerate)
    for i in range(nframes):
        t = i / framerate
        f = freq_start + (freq_end - freq_start) * t / duration
        s = 0.40 * 32767 * abs((t * f * 2 * 3.14159265) % 6.2831853 - 3.14159265) / 3.14159265
        val = int(s)
        wf.writeframes(struct.pack('<h', val))
    wf.close()
    return alert_path

TICK_FILE = make_tick_wav()
ALERT_FILE = make_alert_wav()


class VideoCounterApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("视频计数器")
        self.window.geometry("180x200")
        self.window.resizable(False, False)
        self.window.overrideredirect(True)
        self.window.attributes('-topmost', True)
        # 先布局完成再更新位置，消除启动闪烁
        self.window.update_idletasks()
        screen_width = self.window.winfo_screenwidth()
        window_width = 180
        window_height = 200
        x = screen_width - window_width - 10
        y = 10
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")

        self.max_count = 50
        self.remain = 50
        self.is_running = True
        self.history = []
        self.history_file = "scroll_history.json"
        self._is_closing = False
        self.is_warning_showing = False
        self.drag_data = {"x": 0, "y": 0}
        self.pressing = False
        self.press_thread = None

        self.create_ui()
        self.load_history()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.start_key_monitor()
        self.window.focus_force()
        self.window.bind('<Button-1>', self.on_window_click)
        # 初始化立刻绘制一次，避免先空白/左闪
        self.draw_progress(0)
        self.update_display_no_timer()

    def on_window_click(self, event):
        widget = self.window.winfo_containing(event.x_root, event.y_root)
        if widget != self.max_entry:
            self.window.focus_set()
            self.max_entry.selection_clear()

    def play_tick_sound(self):
        if HAS_WINSOUND:
            try:
                winsound.PlaySound(TICK_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception as e:
                print("滴答音播放失败：", e)
        self.window.bell()

    def _alert_worker(self):
        if HAS_WINSOUND:
            try:
                winsound.PlaySound(ALERT_FILE, winsound.SND_FILENAME)
            except:
                pass

    def play_alert_sound(self):
        threading.Thread(target=self._alert_worker, daemon=True).start()

    def start_key_monitor(self):
        def monitor():
            while not self._is_closing:
                if keyboard.is_pressed("down"):
                    if not self.pressing:
                        self.pressing = True
                    if self.is_running and not self.is_warning_showing and self.remain > 0:
                        self.remain -= 1
                        self.play_tick_sound()
                        print(f"↓ 剩余：{self.remain}")
                        if self.remain <= 0:
                            self.window.after(0, self.show_warning)
                        self.window.after(0, self.update_display_no_timer)
                    time.sleep(0.25)
                else:
                    self.pressing = False
                    time.sleep(0.05)
        self.press_thread = threading.Thread(target=monitor, daemon=True)
        self.press_thread.start()

    def create_ui(self):
        main_frame = tk.Frame(self.window, bg='#f0f0f0', relief=tk.RAISED, bd=1)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_bar = tk.Frame(main_frame, bg='#2196F3', height=28)
        title_bar.pack(fill=tk.X)
        title_bar.pack_propagate(False)
        title_label = tk.Label(title_bar, text="📱 视频计数器", bg='#2196F3', fg='white', font=("微软雅黑", 11, "bold"))
        title_label.pack(side=tk.LEFT, padx=6)
        close_btn = tk.Label(title_bar, text="✕", bg='#2196F3', fg='white', font=("微软雅黑", 11, "bold"), cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=6)
        close_btn.bind('<Button-1>', lambda e: self.on_close())
        title_bar.bind('<Button-1>', self.start_drag)
        title_bar.bind('<B1-Motion>', self.drag)
        title_label.bind('<Button-1>', self.start_drag)
        title_label.bind('<B1-Motion>', self.drag)

        content_frame = tk.Frame(main_frame, bg='#f0f0f0')
        content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        setting_row = tk.Frame(content_frame, bg='#f0f0f0')
        setting_row.pack(fill=tk.X, pady=(0,0))
        tk.Label(setting_row, text="限制:", bg='#f0f0f0', font=("微软雅黑", 14)).pack(side=tk.LEFT, padx=(0, 3))
        self.max_var = tk.StringVar(value="50")
        self.max_entry = tk.Entry(setting_row, textvariable=self.max_var, width=4, font=("微软雅黑", 14))
        self.max_entry.pack(side=tk.LEFT, padx=(0, 3))
        tk.Button(setting_row, text="✓", command=self.apply_settings, width=2, height=0, font=("微软雅黑", 13), bg='#4CAF50', fg='white').pack(side=tk.LEFT, padx=(0, 2))
        tk.Button(setting_row, text="↻", command=self.reset_counter, width=2, height=0, font=("微软雅黑", 13), bg='#FF9800', fg='white').pack(side=tk.LEFT)
        self.max_entry.bind('<Return>', self.on_enter_pressed)

        self.count_label = tk.Label(content_frame, text="50", font=("微软雅黑", 52, "bold"), fg="#2196F3", bg='#f0f0f0')
        self.count_label.pack(pady=(0,0))

        self.canvas = tk.Canvas(content_frame, bg='#f0f0f0', height=32, highlightthickness=0)
        self.canvas.pack(fill=tk.X)

        control_frame = tk.Frame(content_frame, bg='#f0f0f0')
        control_frame.pack(fill=tk.X, pady=3)
        self.start_btn = tk.Button(control_frame, text="▶ 开始", command=self.start_listening, width=6, font=("微软雅黑", 11), bg='#4CAF50', fg='white')
        self.start_btn.pack(side=tk.LEFT, padx=(0, 4))
        self.stop_btn = tk.Button(control_frame, text="⏹ 停止", command=self.stop_listening, width=6, font=("微软雅黑", 11), bg='#f44336', fg='white', state='disabled')
        self.stop_btn.pack(side=tk.LEFT)

    def draw_progress(self, percent):
        self.canvas.delete("all")
        self.canvas.update_idletasks()
        w = self.canvas.winfo_width() - 10
        bar_y1 = 14
        bar_y2 = 24
        self.canvas.create_rectangle(0,bar_y1,w,bar_y2,fill="#cccccc",outline="")
        fill_width = w * percent /100
        self.canvas.create_rectangle(0,bar_y1,fill_width,bar_y2,fill="#2196F3",outline="")
        #放大字体到12号，居中绘制
        self.canvas.create_text(w/2, 7, text=f"{percent:.0f}%",font=("微软雅黑",12),fill="#333333")

    def update_display_no_timer(self):
        if self._is_closing:
            return
        self.count_label.config(text=str(self.remain))
        if self.max_count > 0:
            done = self.max_count - self.remain
            percent = min(100, (done / self.max_count) * 100)
        else:
            percent = 0
        self.draw_progress(percent)

    def on_enter_pressed(self, event):
        self.apply_settings()
        self.window.focus_set()
        self.max_entry.selection_clear()
        return "break"

    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def drag(self, event):
        x = self.window.winfo_x() + (event.x - self.drag_data["x"])
        y = self.window.winfo_y() + (event.y - self.drag_data["y"])
        self.window.geometry(f"+{x}+{y}")

    def apply_settings(self):
        try:
            input_text = self.max_var.get().strip()
            if not input_text:
                self.max_var.set(str(self.max_count))
                return
            new_max = int(input_text)
            if new_max <= 0 or new_max > 9999:
                self.max_var.set(str(self.max_count))
                return
            self.max_count = new_max
            self.remain = self.max_count
            self.is_warning_showing = False
            self.update_display_no_timer()
            print(f"✅ 起始值设为 {self.max_count}")
        except ValueError:
            self.max_var.set(str(self.max_count))

    def show_warning(self):
        if not self.is_running or self._is_closing or self.is_warning_showing:
            return
        self.is_warning_showing = True
        self.play_alert_sound()
        self.is_running = False
        message = (
            "📚 学习提醒\n\n"
            f"剩余数量已归零！\n\n"
            "💪 是时候放下视频，继续学习啦！\n"
            "📖 知识的海洋在等待你探索\n\n"
            "点击确定继续学习"
        )
        messagebox.showinfo("📚 学习提醒", message)
        self.is_warning_showing = False
        self.remain = self.max_count
        self.is_running = True
        self.update_display_no_timer()
        print("🔄 重置并继续监听")

    def reset_counter(self):
        self.remain = self.max_count
        self.is_warning_showing = False
        self.is_running = True
        self.update_display_no_timer()
        print("🔄 重置并继续监听")

    def start_listening(self):
        if self.is_running or self._is_closing:
            return
        self.is_running = True
        self.start_btn.config(state='disabled', bg='#cccccc')
        self.stop_btn.config(state='normal', bg='#f44336')
        print("✅ 开始监听")

    def stop_listening(self):
        if not self.is_running or self._is_closing:
            return
        self.is_running = False
        self.start_btn.config(state='normal', bg='#4CAF50')
        self.stop_btn.config(state='disabled', bg='#cccccc')
        print("⏹ 停止监听")

    def save_record(self):
        if self._is_closing:
            return
        record = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "start_value": self.max_count,
            "final_remain": self.remain
        }
        self.history.append(record)
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except:
            pass

    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except:
                self.history = []
        else:
            self.history = []

    def on_close(self):
        if self._is_closing:
            return
        self._is_closing = True
        if self.is_running:
            self.is_running = False
        self.save_record()
        self.window.destroy()

    def run(self):
        self.window.mainloop()


if __name__ == "__main__":
    try:
        import keyboard
    except ImportError:
        print("❌缺少keyboard库，请执行 pip install keyboard")
        input("按回车退出")
    try:
        print("🚀启动程序")
        app = VideoCounterApp()
        app.run()
    except Exception as e:
        print(f"❌程序异常:{e}")
        import traceback
        traceback.print_exc()
        input("回车退出")

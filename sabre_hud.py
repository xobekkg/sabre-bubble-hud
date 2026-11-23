import tkinter as tk
from tkinter import messagebox
import time
import json
import os
import sys
import subprocess
import ctypes
from pynput import keyboard

DEFAULT_KEY_STR = "Key.f2"
DEFAULT_KEY_LABEL = "F2"
PROBE_DURATION = 120
CYCLE_DELAY = 5.0
RELOAD_DURATION = 60.0

def get_app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_config_path():
    return os.path.join(get_app_dir(), "sabre_config.json")

def get_active_window_title():
    try:
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        if not hwnd:
            return ""
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return ""
        buff = ctypes.create_unicode_buffer(length + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value
    except Exception:
        return ""

class SabreOverlay:
    def __init__(self):
        self.config_file = get_config_path()
        self.is_first_run = not os.path.exists(self.config_file)
        self.config = self.load_config()

        self.root = tk.Tk()
        self.root.title("Sabre Bubble HUD")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.88)
        self.root.configure(bg="#11141a")
        self.root.geometry(f"250x215+{self.config['x']}+{self.config['y']}")

        self.root.bind("<Button-1>", self.start_move)
        self.root.bind("<B1-Motion>", self.do_move)
        self.root.bind("<ButtonRelease-1>", self.stop_move)
        self.root.bind("<Button-3>", self.show_menu)

        self.launch_key_str = self.config["key_str"]
        self.launch_key_label = self.config["key_label"]
        self.probe_duration = self.config["probe_duration"]
        self.client_filter_mode = self.config.get("client_filter_mode", "any_eve")
        self.target_window = self.config.get("target_window", "")
        self.binding_mode = False

        self.probe_ends = [0.0, 0.0, 0.0]
        self.reload_start = 0.0
        self.reload_end = 0.0
        self.probe_index = 0
        self.last_press = 0.0
        self.is_reloading = False
        self.ctrl_pressed = False

        self.header = tk.Label(
            self.root, text=self.get_header_text(),
            fg="#8fa3b0", bg="#11141a", font=("Consolas", 9, "bold")
        )
        self.header.pack(pady=(6, 0))

        self.client_lbl = tk.Label(
            self.root, text=self.get_client_text(),
            fg="#5bc0de", bg="#11141a", font=("Consolas", 8)
        )
        self.client_lbl.pack(pady=(0, 4))

        self.menu = tk.Menu(self.root, tearoff=0, bg="#1e242b", fg="#ffffff", activebackground="#2b8cbe")
        self.menu.add_command(label="Set Launch Hotkey...", command=self.enter_bind_mode)
        self.menu.add_separator()
        self.menu.add_command(label="Link Specific EVE Pilot (3s)...", command=self.start_client_link)
        self.menu.add_command(label="Filter: Any EVE Client", command=lambda: self.set_filter_mode("any_eve"))
        self.menu.add_command(label="Filter: All Windows (No Filter)", command=lambda: self.set_filter_mode("all"))
        self.menu.add_separator()
        self.menu.add_command(label="Standard Probes (120s)", command=lambda: self.set_probe_type(120))
        self.menu.add_command(label="Surgical Probes (180s)", command=lambda: self.set_probe_type(180))
        self.menu.add_separator()
        self.menu.add_command(label="Force Reload (Ctrl+R)", command=self.trigger_manual_reload)
        self.menu.add_command(label="Reset / Instant Full Clip", command=self.reset_timers)
        self.menu.add_separator()
        self.menu.add_command(label="Create Desktop Shortcut", command=self.create_desktop_shortcut)
        self.menu.add_command(label="Help & File Locations", command=self.show_help)
        self.menu.add_separator()
        self.menu.add_command(label="Close HUD", command=self.close_app)

        self.bars = []
        labels = ["PROBE 1", "PROBE 2", "PROBE 3", "RELOAD"]
        for label in labels:
            frame = tk.Frame(self.root, bg="#11141a")
            frame.pack(fill="x", padx=10, pady=2)
            canvas = tk.Canvas(frame, width=230, height=24, bg="#1e242b", highlightthickness=0)
            canvas.pack()
            rect = canvas.create_rectangle(0, 0, 0, 24, fill="#2b8cbe", width=0)
            text = canvas.create_text(
                115, 12, text=f"{label}: READY",
                fill="#ffffff", font=("Consolas", 9, "bold")
            )
            self.bars.append((canvas, rect, text, label))

        btn_frame = tk.Frame(self.root, bg="#11141a")
        btn_frame.pack(fill="x", padx=10, pady=(4, 4))

        self.btn_probe = tk.Button(
            btn_frame, text=f"+ BUBBLE ({self.launch_key_label})", command=self.trigger_probe,
            bg="#1e242b", fg="#8fa3b0", activebackground="#2b8cbe", activeforeground="#ffffff",
            relief="flat", font=("Consolas", 8, "bold"), cursor="hand2"
        )
        self.btn_probe.pack(side="left", expand=True, fill="x", padx=(0, 3))

        btn_reload = tk.Button(
            btn_frame, text="RELOAD (Ctrl+R)", command=self.trigger_manual_reload,
            bg="#1e242b", fg="#8fa3b0", activebackground="#f0ad4e", activeforeground="#11141a",
            relief="flat", font=("Consolas", 8, "bold"), cursor="hand2"
        )
        btn_reload.pack(side="right", expand=True, fill="x", padx=(3, 0))

        self.listener = keyboard.Listener(on_press=self.on_key_press, on_release=self.on_key_release)
        self.listener.start()

        if self.is_first_run:
            self.save_config()
            self.root.after(300, self.show_help)

        self.update_ui()
        self.root.mainloop()

    def load_config(self):
        default = {
            "key_str": DEFAULT_KEY_STR,
            "key_label": DEFAULT_KEY_LABEL,
            "probe_duration": PROBE_DURATION,
            "client_filter_mode": "any_eve",
            "target_window": "",
            "x": 100,
            "y": 300
        }
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                    default.update(data)
        except Exception:
            pass
        return default

    def save_config(self):
        try:
            self.config["key_str"] = self.launch_key_str
            self.config["key_label"] = self.launch_key_label
            self.config["probe_duration"] = self.probe_duration
            self.config["client_filter_mode"] = self.client_filter_mode
            self.config["target_window"] = self.target_window
            self.config["x"] = self.root.winfo_x()
            self.config["y"] = self.root.winfo_y()
            with open(self.config_file, "w") as f:
                json.dump(self.config, f)
        except Exception:
            pass

    def get_header_text(self):
        return f"SABRE HUD [{self.launch_key_label} - {self.probe_duration}s]"

    def get_client_text(self):
        if self.client_filter_mode == "locked" and self.target_window:
            pilot = self.target_window.replace("EVE - ", "")
            return f"CLIENT: {pilot[:24]}"
        elif self.client_filter_mode == "any_eve":
            return "CLIENT: ANY EVE WINDOW"
        return "CLIENT: ALL WINDOWS"

    def start_client_link(self):
        self.countdown_capture(3)

    def countdown_capture(self, sec):
        if sec > 0:
            self.client_lbl.config(text=f"CLICK SABRE WINDOW ({sec}s)...", fg="#f0ad4e")
            self.root.after(1000, lambda: self.countdown_capture(sec - 1))
        else:
            title = get_active_window_title()
            if title.startswith("EVE - "):
                self.target_window = title
                self.client_filter_mode = "locked"
                self.client_lbl.config(text=self.get_client_text(), fg="#5cb85c")
                self.save_config()
            else:
                self.client_lbl.config(text="NOT AN EVE CLIENT! RETRY", fg="#d9534f")
                self.root.after(2000, lambda: self.client_lbl.config(text=self.get_client_text(), fg="#5bc0de"))

    def set_filter_mode(self, mode):
        self.client_filter_mode = mode
        self.client_lbl.config(text=self.get_client_text(), fg="#5bc0de")
        self.save_config()

    def is_valid_client_active(self):
        if self.client_filter_mode == "all":
            return True
        title = get_active_window_title()
        if self.client_filter_mode == "any_eve":
            return title.startswith("EVE - ")
        if self.client_filter_mode == "locked":
            return title == self.target_window
        return True

    def show_help(self):
        app_dir = get_app_dir()
        msg = (
            "WHERE TO SAVE THIS APP:\n"
            f"Currently running from:\n{app_dir}\n\n"
            "Move sabre_hud.exe into its own permanent folder (e.g. C:\\EVE Tools\\SabreHUD\\). "
            "Your preferences (sabre_config.json) automatically save in the same folder as the .exe.\n\n"
            "MULTIBOXING & CONTROLS:\n"
            "- Link Specific Pilot: Right-click -> Link Specific EVE Pilot (3s), then click onto your Sabre client.\n"
            "- Move Widget: Left-click & drag anywhere on the dark box.\n"
            "- Change Hotkey / Probe Type: Right-click the widget.\n"
            "- EVE Display Mode: Use Fixed Window or Windowed mode.\n"
            "- Exit App: Right-click -> Close HUD."
        )
        messagebox.showinfo("Sabre Bubble HUD - Setup & Controls", msg, parent=self.root)

    def create_desktop_shortcut(self):
        try:
            target = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
            work_dir = get_app_dir()
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop, "Sabre Bubble HUD.lnk")
            ps_cmd = (
                f'$s=(New-Object -COM WScript.Shell).CreateShortcut("{shortcut_path}");'
                f'$s.TargetPath="{target}";'
                f'$s.WorkingDirectory="{work_dir}";'
                f'$s.Save()'
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
            messagebox.showinfo("Shortcut Created", "Added 'Sabre Bubble HUD' shortcut to your Desktop.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Error", f"Could not create shortcut:\n{e}", parent=self.root)

    def enter_bind_mode(self):
        self.binding_mode = True
        self.header.config(text="PRESS NEW HOTKEY...", fg="#f0ad4e")

    def format_key(self, key):
        key_str = str(key)
        if hasattr(key, "char") and key.char is not None:
            label = key.char.upper()
        elif hasattr(key, "name"):
            label = key.name.upper()
        else:
            label = key_str.replace("Key.", "").upper()
        return key_str, label

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.root.winfo_x() + (event.x - self.x)
        y = self.root.winfo_y() + (event.y - self.y)
        self.root.geometry(f"+{x}+{y}")

    def stop_move(self, event):
        self.save_config()

    def show_menu(self, event):
        self.menu.tk_popup(event.x_root, event.y_root)

    def set_probe_type(self, duration):
        self.probe_duration = duration
        self.header.config(text=self.get_header_text(), fg="#8fa3b0")
        self.save_config()

    def reset_timers(self):
        self.probe_ends = [0.0, 0.0, 0.0]
        self.reload_start = 0.0
        self.reload_end = 0.0
        self.probe_index = 0
        self.is_reloading = False

    def close_app(self):
        self.save_config()
        self.listener.stop()
        self.root.destroy()

    def trigger_probe(self):
        now = time.time()
        if self.is_reloading or (now - self.last_press) < CYCLE_DELAY:
            return
        self.last_press = now
        self.probe_ends[self.probe_index] = now + self.probe_duration
        self.probe_index += 1
        if self.probe_index >= 3:
            self.is_reloading = True
            self.reload_start = now + CYCLE_DELAY
            self.reload_end = self.reload_start + RELOAD_DURATION

    def trigger_manual_reload(self):
        now = time.time()
        if self.is_reloading or self.probe_index == 0:
            return
        self.is_reloading = True
        cycle_rem = max(0.0, (self.last_press + CYCLE_DELAY) - now)
        self.reload_start = now + cycle_rem
        self.reload_end = self.reload_start + RELOAD_DURATION

    def on_key_press(self, key):
        if self.binding_mode:
            if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r, keyboard.Key.shift, keyboard.Key.shift_r, keyboard.Key.alt_l, keyboard.Key.alt_r):
                return
            self.launch_key_str, self.launch_key_label = self.format_key(key)
            self.binding_mode = False
            self.root.after(0, self.refresh_hotkey_labels)
            return

        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = True
            return

        if not self.is_valid_client_active():
            return

        if str(key) == self.launch_key_str:
            self.trigger_probe()
            return

        if self.ctrl_pressed:
            try:
                if hasattr(key, "char") and key.char in ("r", "R", "\x12"):
                    self.trigger_manual_reload()
            except Exception:
                pass

    def refresh_hotkey_labels(self):
        self.header.config(text=self.get_header_text(), fg="#8fa3b0")
        self.btn_probe.config(text=f"+ BUBBLE ({self.launch_key_label})")
        self.save_config()

    def on_key_release(self, key):
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self.ctrl_pressed = False

    def update_ui(self):
        now = time.time()
        if self.is_reloading and now >= self.reload_end:
            self.is_reloading = False
            self.probe_index = 0

        for i in range(3):
            canvas, rect, text, label = self.bars[i]
            rem = self.probe_ends[i] - now
            if rem > 0:
                pct = rem / self.probe_duration
                width = int(230 * pct)
                color = "#d9534f" if rem <= 15 else "#2b8cbe"
                canvas.coords(rect, 0, 0, width, 24)
                canvas.itemconfig(rect, fill=color)
                canvas.itemconfig(text, text=f"{label}: {rem:05.1f}s")
            else:
                canvas.coords(rect, 0, 0, 0, 24)
                status = "EMPTY" if self.is_reloading else "READY"
                canvas.itemconfig(text, text=f"{label}: {status}")

        canvas, rect, text, label = self.bars[-1]
        if self.is_reloading:
            if now < self.reload_start:
                cycle_rem = self.reload_start - now
                pct = cycle_rem / CYCLE_DELAY
                width = int(230 * pct)
                canvas.coords(rect, 0, 0, width, 24)
                canvas.itemconfig(rect, fill="#5bc0de")
                canvas.itemconfig(text, text=f"CYCLING: {cycle_rem:03.1f}s")
            else:
                rem_reload = self.reload_end - now
                pct = max(0.0, rem_reload / RELOAD_DURATION)
                width = int(230 * pct)
                canvas.coords(rect, 0, 0, width, 24)
                canvas.itemconfig(rect, fill="#f0ad4e")
                canvas.itemconfig(text, text=f"RELOAD: {rem_reload:05.1f}s")
        else:
            canvas.coords(rect, 0, 0, 0, 24)
            canvas.itemconfig(text, text=f"LOADED ({3 - self.probe_index}/3)")

        self.root.after(50, self.update_ui)

if __name__ == "__main__":
    SabreOverlay()

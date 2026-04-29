import tkinter as tk
import threading
import math
import time

class JarvisUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Jarvis")
        self.root.geometry("300x300")
        self.root.overrideredirect(True)          # no title bar
        self.root.wm_attributes("-topmost", True) # always on top
        self.root.wm_attributes("-alpha", 0.85)   # translucent window
        self.root.configure(bg="#000000")
        self.root.wm_attributes("-transparentcolor", "#000000")  # black = transparent

        # --- Position: bottom right corner ---
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"300x300+{sw - 320}+{sh - 340}")

        # --- Canvas for drawing ---
        self.canvas = tk.Canvas(self.root, width=300, height=300,
                                bg="#000000", highlightthickness=0)
        self.canvas.pack()

        # --- State ---
        self.state = "sleeping"   # sleeping | listening | thinking | speaking
        self.angle = 0
        self.pulse = 0
        self.pulse_dir = 1

        # --- Status label ---
        self.status_var = tk.StringVar(value="...")
        self.status_label = tk.Label(
            self.root, textvariable=self.status_var,
            font=("Consolas", 11), fg="#00FFFF", bg="#000000"
        )
        self.status_label.place(x=150, y=265, anchor="center")

        # --- Drag to move ---
        self.canvas.bind("<ButtonPress-1>", self._drag_start)
        self.canvas.bind("<B1-Motion>", self._drag_motion)

        self._animate()

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_motion(self, event):
        dx = event.x - self._drag_x
        dy = event.y - self._drag_y
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")

    def set_state(self, state: str, message: str = ""):
        self.state = state
        labels = {
            "sleeping":  "...",
            "listening": "Listening...",
            "thinking":  "Thinking...",
            "speaking":  message or "Speaking...",
        }
        self.status_var.set(labels.get(state, ""))

    def _draw_sleeping(self):
        cx, cy = 150, 135
        self.pulse += 0.04 * self.pulse_dir
        if self.pulse > 1 or self.pulse < 0:
            self.pulse_dir *= -1
        r = 55 + int(self.pulse * 8)
        alpha_hex = hex(int(80 + self.pulse * 60))[2:].zfill(2)
        color = f"#00{alpha_hex}{'aa'}"
        # outer glow rings
        for i in range(3):
            ri = r + i * 12
            self.canvas.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                                    outline="#004455", width=1)
        # core orb
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                fill="#001830", outline="#006688", width=2)
        # dim eye slits
        self.canvas.create_line(cx-18, cy, cx-6, cy, fill="#004466", width=2)
        self.canvas.create_line(cx+6,  cy, cx+18, cy, fill="#004466", width=2)

    def _draw_listening(self):
        cx, cy = 150, 135
        self.angle = (self.angle + 3) % 360
        r = 65
        # spinning arcs
        for i in range(6):
            a = math.radians(self.angle + i * 60)
            x1 = cx + r * math.cos(a)
            y1 = cy + r * math.sin(a)
            x2 = cx + (r - 18) * math.cos(a)
            y2 = cy + (r - 18) * math.sin(a)
            brightness = int(100 + i * 25)
            col = f"#{0:02x}{brightness:02x}{brightness:02x}"
            self.canvas.create_line(x1, y1, x2, y2, fill=col, width=2)
        # core
        self.canvas.create_oval(cx-50, cy-50, cx+50, cy+50,
                                fill="#001525", outline="#00CCDD", width=2)
        # open eyes
        self.canvas.create_oval(cx-22, cy-6, cx-8, cy+6,
                                fill="#00FFFF", outline="")
        self.canvas.create_oval(cx+8,  cy-6, cx+22, cy+6,
                                fill="#00FFFF", outline="")

    def _draw_thinking(self):
        cx, cy = 150, 135
        self.angle = (self.angle + 5) % 360
        r = 60
        # rotating dashes
        for i in range(12):
            a = math.radians(self.angle + i * 30)
            x1 = cx + r * math.cos(a)
            y1 = cy + r * math.sin(a)
            x2 = cx + (r+10) * math.cos(a)
            y2 = cy + (r+10) * math.sin(a)
            fade = int(60 + i * 16)
            self.canvas.create_line(x1, y1, x2, y2,
                                    fill=f"#00{fade:02x}{fade:02x}", width=2)
        self.canvas.create_oval(cx-50, cy-50, cx+50, cy+50,
                                fill="#001020", outline="#0099AA", width=2)
        # thinking squint
        self.canvas.create_line(cx-22, cy-3, cx-8, cy+3,
                                fill="#00FFFF", width=2)
        self.canvas.create_line(cx+8,  cy-3, cx+22, cy+3,
                                fill="#00FFFF", width=2)

    def _draw_speaking(self):
        cx, cy = 150, 135
        self.pulse += 0.08 * self.pulse_dir
        if self.pulse > 1 or self.pulse < 0:
            self.pulse_dir *= -1
        r = 60 + int(self.pulse * 10)
        # pulsing rings
        for i in range(4):
            ri = r + i * 10
            fade = 180 - i * 35
            self.canvas.create_oval(cx-ri, cy-ri, cx+ri, cy+ri,
                                    outline=f"#00{fade:02x}{fade:02x}", width=1)
        self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                fill="#001828", outline="#00EEFF", width=2)
        # open mouth expression
        self.canvas.create_oval(cx-22, cy-7, cx-8, cy+7,
                                fill="#00FFFF", outline="")
        self.canvas.create_oval(cx+8,  cy-7, cx+22, cy+7,
                                fill="#00FFFF", outline="")
        self.canvas.create_arc(cx-18, cy+8, cx+18, cy+22,
                               start=200, extent=140,
                               outline="#00FFFF", style=tk.ARC, width=2)

    def _animate(self):
        self.canvas.delete("all")
        if self.state == "sleeping":
            self._draw_sleeping()
        elif self.state == "listening":
            self._draw_listening()
        elif self.state == "thinking":
            self._draw_thinking()
        elif self.state == "speaking":
            self._draw_speaking()
        self.root.after(30, self._animate)

    def run_in_thread(self, fn, *args):
        threading.Thread(target=fn, args=args, daemon=True).start()

    def start(self):
        self.root.mainloop()
"""Lightweight Tk loading cover; it never touches audio or native game state."""

import math
from tkinter import ttk
import tkinter as tk


class LoadingCover:
    def __init__(self, root):
        self.root = root
        self.frame = ttk.Frame(root, padding=28, relief="ridge", borderwidth=2)
        self.label = ttk.Label(
            self.frame,
            font=("DejaVu Sans", 15, "bold"),
            anchor="center",
            wraplength=580,
        )
        self.label.pack(fill="x", pady=(8, 20))
        self.canvas = tk.Canvas(
            self.frame, width=120, height=120, bg="#16232f", highlightthickness=0
        )
        self.canvas.pack()
        self.active = False
        self.job = None
        self.step = 0

    def show(self, text):
        self.label.configure(text=text)
        self.frame.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.68)
        self.frame.lift()
        if not self.active:
            self.active = True
            self.animate()

    def animate(self):
        if not self.active:
            return
        self.canvas.delete("all")
        for i in range(8):
            a = i * math.pi / 4
            x = 60 + 40 * math.cos(a)
            y = 60 + 40 * math.sin(a)
            color = "#8ce0c0" if i == self.step % 8 else "#34515e"
            self.canvas.create_oval(x - 7, y - 7, x + 7, y + 7, fill=color, outline="")
        self.step += 1
        self.job = self.root.after(90, self.animate)

    def hide(self):
        self.active = False
        self.frame.place_forget()
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None

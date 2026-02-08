import tkinter as tk
from tkinter import ttk

class TestWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Hello from test page").pack(pady=10)

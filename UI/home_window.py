import tkinter as tk
from tkinter import ttk

class HomeWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Welcome To Home Window").pack(pady=10)

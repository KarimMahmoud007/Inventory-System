import tkinter as tk
from tkinter import ttk

class OrderWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Order Window").pack(pady=10)

import tkinter as tk
from tkinter import ttk

class StockWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Stock Window").pack(pady=10)

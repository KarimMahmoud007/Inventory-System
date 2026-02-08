import tkinter as tk
from tkinter import ttk

class StaffWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Staff Window").pack(pady=10)

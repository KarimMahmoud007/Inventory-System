import tkinter as tk
from tkinter import ttk
from UI.stock_window import StockWindow
from UI.order_window import OrderWindow
from UI.staff_window import StaffWindow
from UI.home_window  import HomeWindow
from UI.test_window  import TestWindow

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventory System")
        self.geometry("800x600")

        # 1. MODERN STYLING CONFIGURATION
        style = ttk.Style()
        style.theme_use('clam')  # 'clam' is usually the cleanest built-in theme

        # Configure Colors
        bg_color = "#f0f0f0"
        sidebar_color = "#2c3e50"
        text_color = "#ffffff"

        self.configure(bg=bg_color)

        # Style Definitions
        style.configure("Sidebar.TFrame", background=sidebar_color)
        style.configure("Content.TFrame", background=bg_color)
        style.configure("Nav.TButton", font=('Segoe UI', 11), padding=10)

        # Container for Layout (Sidebar + Main)
        main_layout = ttk.Frame(self)
        main_layout.pack(fill="both", expand=True)

        # Sidebar
        sidebar = ttk.Frame(main_layout, style="Sidebar.TFrame", width=200)
        sidebar.pack(side="left", fill="y")

        # Content Area
        container = ttk.Frame(main_layout, style="Content.TFrame")
        container.pack(side="right", fill="both", expand=True)

        self.frames = {}

        # Create Buttons in Sidebar
        buttons = [("Home", "HomeWindow"), ("Stock", "StockWindow"),
                   ("Orders", "OrderWindow"), ("Staff", "StaffWindow"),("Test", "TestWindow")]

        for text, page in buttons:
            btn = tk.Button(sidebar, text=text, bg=sidebar_color, fg=text_color,
                            bd=0, font=("Segoe UI", 12), activebackground="#34495e", activeforeground="white",
                            command=lambda p=page: self.show_frame(p))
            btn.pack(fill="x", pady=2)


        for F in (StockWindow, OrderWindow, StaffWindow,HomeWindow,TestWindow):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

            # Configure grid weight for the container to center/stretch content
            container.grid_rowconfigure(0, weight=1)
            container.grid_columnconfigure(0, weight=1)

        self.show_frame("HomeWindow")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
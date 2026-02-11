from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget
)
from PySide6.QtCore import Qt


from views.stock_window import StockWindow
from views.order_window import OrderWindow
from views.staff_window import StaffWindow
from views.home_window import HomeWindow
from views.test_window import TestWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Inventory System")
        self.resize(800, 600)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # -------------------
        # Sidebar
        # -------------------
        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("""
            background-color: #2c3e50;
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(2)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        # -------------------
        # Stacked Pages
        # -------------------
        self.pages = QStackedWidget()

        self.page_map = {
            "Home": HomeWindow(),
            "Stock": StockWindow(),
            "Orders": OrderWindow(),
            "Staff": StaffWindow(),
            "Test": TestWindow(),
        }

        for page in self.page_map.values():
            self.pages.addWidget(page)

        # -------------------
        # Sidebar Buttons
        # -------------------
        for name in self.page_map:
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    color: white;
                    padding: 12px;
                    border: none;
                    text-align: left;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #34495e;
                }
            """)
            btn.clicked.connect(lambda checked, n=name: self.show_page(n))
            sidebar_layout.addWidget(btn)

        sidebar_layout.addStretch()

        # -------------------
        # Layout Assembly
        # -------------------
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        self.show_page("Home")

    def show_page(self, name):
        self.pages.setCurrentWidget(self.page_map[name])


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()


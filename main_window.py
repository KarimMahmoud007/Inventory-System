from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget
)
from PySide6.QtCore import Qt

from pathlib import Path

STYLESHEET = Path(__file__).parent / "styles" / "main.qss"


from views.staff_window import StaffWindow
from views.home_window import HomeWindow
from views.test_window import TestWindow

from controllers.stock_controller import StockController
from controllers.recipes_controller import RecipesController
from controllers.order_controller import OrderController
from controllers.finance_controller import FinanceController

from models.stock_model import StockModel
from models.stock_batch_model import StockBatchModel
from models.recipes_model import RecipesModel
from models.order_model import OrderModel
from models.finance_model import FinanceModel



class MainWindow(QMainWindow):

    def __init__(self):
        # Models are created once here and injected into the controllers. The single
        # StockBatchModel is shared by the Stock page and the order path (OrderModel),
        # so all stock_batch access goes through one persistent instance.
        self.stock_model = StockModel()
        self.batch_model = StockBatchModel()
        self.recipes_model = RecipesModel()
        self.finance_model = FinanceModel()
        self.order_model = OrderModel(self.batch_model, self.finance_model)

        self.stock_controller = StockController(self.stock_model, self.batch_model)
        self.recipes_controller = RecipesController(self.recipes_model)
        self.order_controller = OrderController(self.order_model)
        self.finance_controller = FinanceController(self.finance_model)

        # Keep the Order page in sync with stock/recipe edits made on other pages.
        self.stock_controller.data_changed.connect(self.order_controller.refresh_current_order)
        self.recipes_controller.data_changed.connect(self.order_controller.refresh_current_order)

        # Finance follows the model's signal, not the order UI — the page stays
        # correct even if the order flow is driven from somewhere else later.
        self.order_model.order_placed_successfully.connect(self.finance_controller.refresh)

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
        sidebar.setObjectName("sidebar")

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(2)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        # -------------------
        # Stacked Pages
        # -------------------
        self.pages = QStackedWidget()

        self.page_map = {
            "Home": HomeWindow(),
            "Stock": self.stock_controller.stock_view,
            "Recipes": self.recipes_controller.recipes_view,
            "Order": self.order_controller.order_view,
            "Finance": self.finance_controller.finance_view,
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
            btn.setObjectName("sidebarBtn")
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
    app.setStyleSheet(STYLESHEET.read_text(encoding="utf-8"))
    window = MainWindow()
    window.show()
    app.exec()


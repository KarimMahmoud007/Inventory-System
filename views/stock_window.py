from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView, QPushButton
from Controllers.stock_controller import *
from Model.stock_model import *

from views.addstock_window import AddStockWindow

class StockWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.model = get_stock_model(self)

        # Setting headers
        headers = ["ID","Name", "Unit", "Price", "Production Date", "Expiration Date", "Quantity","Batch"]
        for i, header in enumerate(headers):
            self.model.setHeaderData(i, Qt.Horizontal, header)

        self.table = QTableView()
        self.table.setModel(self.model)

        # Optional: Make columns stretch to fill the table width for a cleaner look
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # --- CENTERING LOGIC ---
        # 1. Set a fixed size for the table so it doesn't fill the whole window
        self.table.setFixedSize(800, 600)

        layout = QVBoxLayout()
        layout.addWidget(self.table)


        self.button = QPushButton("ADD")
        self.button.clicked.connect(self.add_click_button)
        layout.addWidget(self.button)

        # 2. Align the contents of the layout to the center
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)

        self.setWindowTitle("Stock")
        # Ensure the window is larger than the table so you can see the centering
        self.resize(500, 400)


    def add_click_button(self):
        self.w = AddStockWindow()
        self.w.show()

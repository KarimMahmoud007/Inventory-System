from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView, QPushButton

from Model.stock_model import *



class StockWindow(QWidget):
    insert_view_signal = Signal()
    def __init__(self,model):


        super().__init__()



        # Setting headers
        headers = ["ID","Name", "Unit", "Price", "Production Date", "Expiration Date", "Quantity","Batch"]
        for i, header in enumerate(headers):
            model.setHeaderData(i, Qt.Horizontal, header)

        self.table = QTableView()
        self.table.setModel(model)

        # Optional: Make columns stretch to fill the table width for a cleaner look
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # --- CENTERING LOGIC ---
        # 1. Set a fixed size for the table so it doesn't fill the whole window
        self.table.setFixedSize(800, 600)

        layout = QVBoxLayout()
        layout.addWidget(self.table)


        self.button = QPushButton("Insert")
        self.button.clicked.connect(self.insertButton)
        layout.addWidget(self.button)

        # 2. Align the contents of the layout to the center
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)

        self.setWindowTitle("Stock")
        # Ensure the window is larger than the table so you can see the centering
        self.resize(500, 400)



    def insertButton(self):
        self.insert_view_signal.emit()



from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView, QPushButton, QAbstractItemView, QMenu





class StockWindow(QWidget):
    insert_request_signal = Signal()
    delete_request_signal = Signal(list)
    edit_request_signal = Signal(int)

    def __init__(self,model):

        super().__init__()

        # Setting headers
        headers = ["ID","Name", "Unit", "Price", "Production Date", "Expiration Date", "Quantity","Batch"]
        for i, header in enumerate(headers):
            model.setHeaderData(i, Qt.Horizontal, header)

        self.table = QTableView()
        self.table.setModel(model)


        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)



        # Optional: Make columns stretch to fill the table width for a cleaner look
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # --- CENTERING LOGIC ---
        # 1. Set a fixed size for the table so it doesn't fill the whole window
        self.table.setFixedSize(800, 600)

        layout = QVBoxLayout()
        layout.addWidget(self.table)


        self.button = QPushButton("Insert")
        self.button.clicked.connect(self.insert_button)
        layout.addWidget(self.button)

        # 2. Align the contents of the layout to the center
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)

        self.setWindowTitle("Stock")
        # Ensure the window is larger than the table so you can see the centering
        self.resize(500, 400)

    def insert_button(self):
        self.insert_request_signal.emit()

    def edit_row(self, row):
        self.edit_request_signal.emit(row)

    def delete_row(self, index):
        self.delete_request_signal.emit([index])


    def show_context_menu(self, position):
        index = self.table.indexAt(position)

        if not index.isValid():
            return  # clicked outside row

        menu = QMenu()

        edit_action = QAction("Edit", self)
        delete_action = QAction("Delete", self)

        menu.addAction(delete_action)
        menu.addAction(edit_action)

        delete_action.triggered.connect(lambda: self.delete_row(index))
        edit_action.triggered.connect(lambda: self.edit_row(index.row()))


        menu.exec(self.table.viewport().mapToGlobal(position))



from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableView, QHeaderView, QPushButton, QLabel, QAbstractItemView, QMenu


class StockBatchWindow(QWidget):
    add_batch_requested = Signal()
    edit_batch_requested = Signal(int)
    delete_batch_requested = Signal(int)
    toggle_status_requested = Signal(int)
    back_requested = Signal()

    def __init__(self, stock_id: int, stock_name: str, model):
        super().__init__()
        self.stock_id = stock_id

        headers = ["ID", "Stock ID", "Price", "Production Date", "Expiration Date", "Quantity", "Status", "Added At"]
        for i, header in enumerate(headers):
            model.setHeaderData(i, Qt.Horizontal, header)

        self.table = QTableView()
        self.table.setModel(model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setColumnHidden(1, True)
        self.table.setFixedSize(800, 400)

        layout = QVBoxLayout()

        header_layout = QHBoxLayout()

        title = QLabel(f"Batches for: {stock_name}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self._on_back_clicked)
        header_layout.addWidget(self.back_btn)

        layout.addLayout(header_layout)

        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("+ Add Batch")
        self.add_btn.clicked.connect(self._on_add_clicked)
        button_layout.addWidget(self.add_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        layout.addWidget(self.table)
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)
        self.setWindowTitle("Stock Batches")

    def _on_add_clicked(self):
        self.add_batch_requested.emit()

    def _on_back_clicked(self):
        self.back_requested.emit()

    def show_context_menu(self, position):
        index = self.table.indexAt(position)

        if not index.isValid():
            return

        menu = QMenu()

        edit_action = QAction("Edit", self)
        toggle_action = QAction("Toggle Available / Out of Stock", self)
        delete_action = QAction("Delete", self)

        menu.addAction(edit_action)
        menu.addAction(toggle_action)
        menu.addAction(delete_action)

        edit_action.triggered.connect(lambda: self._on_edit_row(index.row()))
        toggle_action.triggered.connect(lambda: self._on_toggle_status(index.row()))
        delete_action.triggered.connect(lambda: self._on_delete_row(index.row()))

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _get_batch_id(self, row: int) -> int:
        return self.table.model().data(self.table.model().index(row, 0))

    def _on_edit_row(self, row):
        self.edit_batch_requested.emit(self._get_batch_id(row))

    def _on_toggle_status(self, row):
        self.toggle_status_requested.emit(self._get_batch_id(row))

    def _on_delete_row(self, row):
        self.delete_batch_requested.emit(self._get_batch_id(row))

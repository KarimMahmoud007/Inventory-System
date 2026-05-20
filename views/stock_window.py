from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView, QPushButton, QAbstractItemView, QMenu


class StockWindow(QWidget):
    add_item_requested = Signal()
    delete_item_requested = Signal(int)
    edit_item_requested = Signal(int)
    view_batches_requested = Signal(int)

    def __init__(self, model):
        super().__init__()

        headers = ["ID", "Name", "Unit"]
        for i, header in enumerate(headers):
            model.setHeaderData(i, Qt.Horizontal, header)

        self.table = QTableView()
        self.table.setModel(model)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setFixedSize(600, 400)

        layout = QVBoxLayout()

        self.button = QPushButton("+ Add Item")
        self.button.clicked.connect(self._on_add_clicked)
        layout.addWidget(self.button)

        layout.addWidget(self.table)
        layout.setAlignment(Qt.AlignCenter)

        self.setLayout(layout)
        self.setWindowTitle("Stock Items")
        self.resize(500, 400)

    def _on_add_clicked(self):
        self.add_item_requested.emit()

    def show_context_menu(self, position):
        index = self.table.indexAt(position)

        if not index.isValid():
            return

        menu = QMenu()

        view_batches_action = QAction("View Batches", self)
        edit_action = QAction("Edit", self)
        delete_action = QAction("Delete", self)

        menu.addAction(view_batches_action)
        menu.addAction(edit_action)
        menu.addAction(delete_action)

        view_batches_action.triggered.connect(lambda: self._on_view_batches(index))
        edit_action.triggered.connect(lambda: self._on_edit_row(index.row()))
        delete_action.triggered.connect(lambda: self._on_delete_row(index.row()))

        menu.exec(self.table.viewport().mapToGlobal(position))

    def _get_item_id(self, row: int) -> int:
        return self.table.model().data(self.table.model().index(row, 0))

    def _on_view_batches(self, index):
        stock_id = self._get_item_id(index.row())
        self.view_batches_requested.emit(stock_id)

    def _on_edit_row(self, row):
        self.edit_item_requested.emit(self._get_item_id(row))

    def _on_delete_row(self, row):
        self.delete_item_requested.emit(self._get_item_id(row))

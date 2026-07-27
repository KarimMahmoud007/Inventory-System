from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QLineEdit, QFormLayout, QPushButton, QComboBox, QMessageBox
from enum import Enum
from models.entities import StockItem


class StockMode(Enum):
    INSERT = 1
    UPDATE = 2


class StockItemFormWindow(QWidget):
    stock_item_submitted = Signal(StockItem)
    stock_item_update_submitted = Signal(StockItem)

    def __init__(self, mode, units):
        super().__init__()
        self.mode = mode
        self._editing_id = None

        self.entries = {}

        layout = QFormLayout()

        self.name_edit = QLineEdit()
        self.entries["Name"] = self.name_edit
        layout.addRow("Name", self.name_edit)

        self.unit_combo = QComboBox()
        for unit_id, unit_name in units:
            self.unit_combo.addItem(unit_name, unit_id)
        self.entries["Unit"] = self.unit_combo
        layout.addRow("Unit", self.unit_combo)

        self.saveBtn = QPushButton("Save", self)
        self.saveBtn.clicked.connect(self.save)
        layout.addWidget(self.saveBtn)

        self.setLayout(layout)
        self.setWindowTitle("Stock Item")

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    def save(self):
        if self.mode == StockMode.INSERT:
            self._on_insert_clicked()
        elif self.mode == StockMode.UPDATE:
            self._on_update_clicked()

    def _on_insert_clicked(self):
        self.stock_item_submitted.emit(self.wrap_data())

    def _on_update_clicked(self):
        self.stock_item_update_submitted.emit(self.wrap_data())

    def load_data(self, stock_item: StockItem):
        self.name_edit.setText(stock_item.name)
        combo = self.unit_combo
        for i in range(combo.count()):
            if combo.itemData(i) == stock_item.unit_id:
                combo.setCurrentIndex(i)
                break
        self._editing_id = stock_item.id

    def wrap_data(self) -> StockItem:
        return StockItem(
            id=self._editing_id,
            name=self.name_edit.text(),
            unit_id=self.unit_combo.currentData(),
        )

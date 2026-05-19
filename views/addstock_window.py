from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QWidget, QDateEdit, QLineEdit, QFormLayout, QPushButton, QComboBox
from enum import Enum
from Utilities.utilities import get_units
from models.entities import StockItem

class StockMode(Enum):
    INSERT = 1
    UPDATE = 2

class AddStockWindow(QWidget):
    stock_item_data_signal = Signal(StockItem)
    stock_item_update_data = Signal(StockItem)

    def __init__(self, mode):
        super().__init__()
        self.mode = mode

        form_config = {
            "Name": QLineEdit,
            "Unit": QComboBox,
            "Price": QLineEdit,
            "Production Date": QDateEdit,
            "Expiration Date": QDateEdit,
            "Quantity": QLineEdit
        }

        self.entries = {}

        layout = QFormLayout()

        for label_text, widget_class in form_config.items():
            widget = widget_class()

            if isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
                widget.setCalendarPopup(True)

            if isinstance(widget, QComboBox):
                for unit_id, unit_name in get_units():
                    widget.addItem(unit_name, unit_id)

            self.entries[label_text] = widget
            layout.addRow(label_text, widget)

        self.saveBtn = QPushButton("Save",self)
        self.saveBtn.clicked.connect(self.save)
        layout.addWidget(self.saveBtn)

        self.setLayout(layout)
        self.setWindowTitle("Add Stock")


    def save(self):
        if self.mode == StockMode.INSERT.value:
            self.on_insert_clicked()
        elif self.mode == StockMode.UPDATE.value:
            self.on_update_clicked()

    def on_insert_clicked(self):
        self.stock_item_data_signal.emit(self.wrap_data())

    def on_update_clicked(self):
        self.stock_item_update_data.emit(self.wrap_data())



    def wrap_data(self) -> StockItem:
        return StockItem(
            name=self.entries["Name"].text(),
            unit_id=self.entries["Unit"].currentData(),
            price=float(self.entries["Price"].text()),
            production_date=self.entries["Production Date"].date().toString("yyyy-MM-dd"),
            expiration_date=self.entries["Expiration Date"].date().toString("yyyy-MM-dd"),
            quantity=float(self.entries["Quantity"].text()),
        )

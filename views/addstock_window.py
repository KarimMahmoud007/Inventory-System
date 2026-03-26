from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QWidget, QDateEdit, QLineEdit, QFormLayout, QPushButton
from enum import Enum

class StockMode(Enum):
    INSERT = 1
    UPDATE = 2

class AddStockWindow(QWidget):
    stock_item_data_signal = Signal(list)
    stock_item_update_data = Signal(list)

    def __init__(self, mode):
        super().__init__()
        self.mode = mode

        form_config = {
            "Name": QLineEdit,
            "Unit": QLineEdit,
            "Price": QLineEdit,
            "Production Date": QDateEdit,
            "Expiration Date": QDateEdit,
            "Quantity": QLineEdit
        }

        self.entries = {}
        self.data = []

        layout = QFormLayout()

        for label_text, widget_class in form_config.items():
            widget = widget_class()

            if isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
                widget.setCalendarPopup(True)

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
        wrapped_data = self.wrapData()
        self.stock_item_data_signal.emit(wrapped_data)

    def on_update_clicked(self):
        wrapped_data = self.wrapData()
        self.stock_item_update_data.emit(wrapped_data)

    def load_data(self, data):
        widgets = list(self.entries.values())

        for widget, value in zip(widgets, data):

            if isinstance(widget, QDateEdit):
                date = QDate.fromString(value, "yyyy-MM-dd")
                widget.setDate(date)

            else:
                widget.setText(str(value))

    def wrapData(self):
        self.data = []
        for widget in self.entries.values():
            if isinstance(widget, QDateEdit):
                self.data.append(widget.date().toString("yyyy-MM-dd"))
            else:
                self.data.append(widget.text())
        return self.data

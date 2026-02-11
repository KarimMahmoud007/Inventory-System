from PySide6.QtCore import QDate
from PySide6.QtWidgets import QWidget, QDateEdit, QLineEdit, QFormLayout, QPushButton
from Controllers.stock_controller import get_data

class AddStockWindow(QWidget):
    def __init__(self):
        super().__init__()

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
        self.saveBtn.clicked.connect(self.on_save_clicked)
        layout.addWidget(self.saveBtn)

        self.setLayout(layout)
        self.setWindowTitle("Add Stock")

    def on_save_clicked(self):
        self.data = []
        for widget in self.entries.values():
            if isinstance(widget, QDateEdit):
                self.data.append(widget.date().toString("yyyy-MM-dd"))
            else:
                self.data.append(widget.text())
        get_data(self.data)


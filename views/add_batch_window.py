from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QWidget, QDateEdit, QLineEdit, QFormLayout, QPushButton, QMessageBox
from enum import Enum
from models.entities import StockBatch


class BatchMode(Enum):
    INSERT = 1
    UPDATE = 2


class AddBatchWindow(QWidget):
    batch_data_signal = Signal(StockBatch)
    batch_update_data = Signal(StockBatch)

    def __init__(self, mode):
        super().__init__()
        self.mode = mode

        form_config = {
            "Price": QLineEdit,
            "Production Date": QDateEdit,
            "Expiration Date": QDateEdit,
            "Quantity": QLineEdit,
        }

        self.entries = {}

        layout = QFormLayout()

        for label_text, widget_class in form_config.items():
            widget = widget_class()

            if isinstance(widget, QDateEdit):
                widget.setDate(QDate.currentDate())
                widget.setCalendarPopup(True)

            self.entries[label_text] = widget
            layout.addRow(label_text, widget)

        self.saveBtn = QPushButton("Save", self)
        self.saveBtn.clicked.connect(self.save)
        layout.addWidget(self.saveBtn)

        self.setLayout(layout)
        self.setWindowTitle("Batch")

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    def save(self):
        if self.mode == BatchMode.INSERT.value:
            self._on_insert_clicked()
        elif self.mode == BatchMode.UPDATE.value:
            self._on_update_clicked()

    def _on_insert_clicked(self):
        self.batch_data_signal.emit(self.wrap_data())

    def _on_update_clicked(self):
        self.batch_update_data.emit(self.wrap_data())

    def load_data(self, batch: StockBatch):
        self.entries["Price"].setText(str(batch.price))
        self.entries["Production Date"].setDate(
            QDate.fromString(batch.production_date, "yyyy-MM-dd")
        )
        self.entries["Expiration Date"].setDate(
            QDate.fromString(batch.expiration_date, "yyyy-MM-dd")
        )
        self.entries["Quantity"].setText(str(batch.quantity))
        self._editing_id = batch.id

    def wrap_data(self, stock_id: int | None = None) -> StockBatch:
        return StockBatch(
            id=getattr(self, '_editing_id', None),
            stock_id=stock_id if stock_id is not None else 0,
            price=float(self.entries["Price"].text()),
            production_date=self.entries["Production Date"].date().toString("yyyy-MM-dd"),
            expiration_date=self.entries["Expiration Date"].date().toString("yyyy-MM-dd"),
            quantity=float(self.entries["Quantity"].text()),
        )

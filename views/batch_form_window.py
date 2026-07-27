from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QWidget, QDateEdit, QLineEdit, QFormLayout, QPushButton, QMessageBox
from enum import Enum
from models.entities import StockBatch
from Utilities.validate_data import parse_float


class BatchMode(Enum):
    INSERT = 1
    UPDATE = 2


class BatchFormWindow(QWidget):
    batch_submitted = Signal(StockBatch)
    batch_update_submitted = Signal(StockBatch)

    def __init__(self, mode):
        super().__init__()
        self.mode = mode
        self._editing_id = None

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
        error = self._field_error()
        if error:
            self.show_warning("Validation Error", error)
            return

        if self.mode == BatchMode.INSERT:
            self._on_insert_clicked()
        elif self.mode == BatchMode.UPDATE:
            self._on_update_clicked()

    def _field_error(self) -> str | None:
        """Check the numeric fields before wrap_data() converts them, so an empty
        or non-numeric entry becomes a warning instead of an exception in a slot."""
        for label in ("Price", "Quantity"):
            _value, error = parse_float(self.entries[label].text(), label)
            if error:
                return error
        return None

    def _on_insert_clicked(self):
        self.batch_submitted.emit(self.wrap_data())

    def _on_update_clicked(self):
        self.batch_update_submitted.emit(self.wrap_data())

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

    def wrap_data(self) -> StockBatch:
        """Build the entity. Safe only after _field_error() has passed —
        save() is the only caller and checks first."""
        return StockBatch(
            id=self._editing_id,
            stock_id=0,   # set by BatchController, which owns the current stock_id
            price=float(self.entries["Price"].text()),
            production_date=self.entries["Production Date"].date().toString("yyyy-MM-dd"),
            expiration_date=self.entries["Expiration Date"].date().toString("yyyy-MM-dd"),
            quantity=float(self.entries["Quantity"].text()),
        )

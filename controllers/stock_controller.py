from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget

from models.stock_model import StockModel
from models.stock_batch_model import StockBatchModel
from views.stock_window import StockWindow
from views.stock_batch_window import StockBatchWindow
from views.add_stock_item_window import AddStockItemWindow, StockMode
from views.add_batch_window import AddBatchWindow, BatchMode
from models.entities import StockItem, StockBatch
from Utilities.validate_data import validate_stock_item, validate_stock_batch


class StockController(QObject):

    # Relayed to OrderController so the Order page refreshes on any stock change.
    data_changed = Signal()

    def __init__(self):
        super().__init__()

        self.stack = QStackedWidget()
        self.add_item_window = None
        self.add_batch_window = None
        self.batch_view = None
        self.batch_model_instance = None

        # ---- Level 1: Stock items ----
        self.stock_model = StockModel()
        self.table_model = self.stock_model.get_stock_model()
        self.item_view = StockWindow(self.table_model)
        self.stack.addWidget(self.item_view)

        self.item_view.add_item_requested.connect(self.open_add_item_window)
        self.item_view.edit_item_requested.connect(self.open_edit_item_window)
        self.item_view.delete_item_requested.connect(self.delete_item)
        self.item_view.view_batches_requested.connect(self.open_batch_window)

        self.stock_model.item_delete_rejected.connect(
            lambda msg: self.item_view.show_warning("Cannot Delete", msg))
        self.stock_model.item_insert_rejected.connect(
            lambda msg: self.add_item_window and self.add_item_window.show_warning("Duplicate Name", msg))

        # Relay stock-item changes to the Order page.
        self.stock_model.item_inserted_successfully.connect(self.data_changed.emit)
        self.stock_model.item_updated_successfully.connect(self.data_changed.emit)
        self.stock_model.item_deleted_successfully.connect(self.data_changed.emit)

        self.stock_view = self.stack

    # ──────────────────────────────────────────────
    #  Item operations
    # ──────────────────────────────────────────────

    def open_add_item_window(self):
        self.add_item_window = AddStockItemWindow(StockMode.INSERT.value, units=self.stock_model.units)
        self.add_item_window.show()
        self.add_item_window.stock_item_data_signal.connect(self.handle_add_item)
        self.stock_model.item_inserted_successfully.connect(self.add_item_window.close)

    def handle_add_item(self, data):
        if validate_stock_item(data):
            self.stock_model.insert_stock_item(data)
        else:
            self.add_item_window.show_warning("Validation Error", "Name is required and unit must be selected.")

    def open_edit_item_window(self, item_id: int):
        item = self.stock_model.get_stock_item(item_id)
        if item is None:
            return

        self.add_item_window = AddStockItemWindow(StockMode.UPDATE.value, units=self.stock_model.units)
        self.add_item_window.load_data(item)
        self.add_item_window.show()
        self.add_item_window.stock_item_update_data.connect(self.handle_edit_item)
        self.stock_model.item_updated_successfully.connect(self.add_item_window.close)

    def handle_edit_item(self, data):
        if validate_stock_item(data):
            self.stock_model.update_stock_item(data)
        else:
            self.add_item_window.show_warning("Validation Error", "Name is required and unit must be selected.")

    def delete_item(self, item_id: int):
        self.stock_model.delete_stock_item(item_id)

    # ──────────────────────────────────────────────
    #  Batch operations
    # ──────────────────────────────────────────────

    def open_batch_window(self, stock_id):
        if self.batch_view is not None:
            self.stack.removeWidget(self.batch_view)
            self.batch_view.deleteLater()
            self.batch_view = None
            self.batch_model_instance = None

        stock_name = self.stock_model.get_stock_name(stock_id)
        self.batch_model_instance = StockBatchModel()
        batch_model = self.batch_model_instance.get_batch_model(stock_id)
        self.batch_view = StockBatchWindow(stock_id, stock_name, batch_model)

        self.batch_view.back_requested.connect(self.close_batch_window)
        self.batch_view.add_batch_requested.connect(self.open_add_batch_window)
        self.batch_view.edit_batch_requested.connect(self.open_edit_batch_window)
        self.batch_view.delete_batch_requested.connect(self.delete_batch)
        self.batch_view.toggle_status_requested.connect(self.toggle_batch_status)

        # Relay batch changes to the Order page (this instance is transient,
        # so the connections are made here each time it's created).
        self.batch_model_instance.batch_inserted_successfully.connect(self.data_changed.emit)
        self.batch_model_instance.batch_updated_successfully.connect(self.data_changed.emit)
        self.batch_model_instance.batch_deleted_successfully.connect(self.data_changed.emit)
        self.batch_model_instance.batch_status_toggled.connect(self.data_changed.emit)

        self.stack.addWidget(self.batch_view)
        self.stack.setCurrentWidget(self.batch_view)

    def close_batch_window(self):
        self.stack.setCurrentWidget(self.item_view)
        if self.batch_view is not None:
            self.stack.removeWidget(self.batch_view)
            self.batch_view.deleteLater()
            self.batch_view = None
            self.batch_model_instance = None

    def open_add_batch_window(self):
        self.add_batch_window = AddBatchWindow(BatchMode.INSERT.value)
        self.add_batch_window.show()
        self.add_batch_window.batch_data_signal.connect(self.handle_add_batch)
        self.batch_model_instance.batch_inserted_successfully.connect(
            self.add_batch_window.close
        )

    def handle_add_batch(self, data: StockBatch):
        if validate_stock_batch(data):
            data.stock_id = self.batch_view.stock_id
            self.batch_model_instance.insert_batch(data)
        else:
            self.add_batch_window.show_warning("Validation Error", "Price and quantity must be positive, expiration must be after production date.")

    def open_edit_batch_window(self, batch_id: int):
        batch = self.batch_model_instance.get_batch(batch_id)
        if batch is None:
            return

        self.add_batch_window = AddBatchWindow(BatchMode.UPDATE.value)
        self.add_batch_window.load_data(batch)
        self.add_batch_window.show()
        self.add_batch_window.batch_update_data.connect(self.handle_edit_batch)
        self.batch_model_instance.batch_updated_successfully.connect(
            self.add_batch_window.close
        )

    def handle_edit_batch(self, data: StockBatch):
        if validate_stock_batch(data):
            data.stock_id = self.batch_view.stock_id
            self.batch_model_instance.update_batch(data)
        else:
            self.add_batch_window.show_warning("Validation Error", "Price and quantity must be positive, expiration must be after production date.")

    def delete_batch(self, batch_id: int):
        self.batch_model_instance.delete_batch(batch_id)

    def toggle_batch_status(self, batch_id: int):
        self.batch_model_instance.toggle_status(batch_id)

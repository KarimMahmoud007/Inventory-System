from PySide6.QtCore import QObject, Signal

from views.stock_batch_window import StockBatchWindow
from views.add_batch_window import AddBatchWindow, BatchMode
from models.entities import StockBatch
from Utilities.validate_data import validate_stock_batch


class BatchController(QObject):

    # Relayed up through StockController so the Order page refreshes on any batch change.
    data_changed = Signal()

    def __init__(self, batch_model, stack, item_view):
        super().__init__()

        # The shared StockBatchModel (also injected into OrderModel) — persistent,
        # not per-window. Navigation collaborators (stack + item_view) are owned by
        # StockController and passed in so this controller can manage the batch page.
        self.batch_model_instance = batch_model
        self.stack = stack
        self.item_view = item_view

        self.batch_view = None
        self.batch_form_window = None

        # Relay batch changes to the Order page. The batch model is persistent
        # (shared/injected), so these are wired once here rather than per batch window.
        self.batch_model_instance.batch_inserted_successfully.connect(self.data_changed.emit)
        self.batch_model_instance.batch_updated_successfully.connect(self.data_changed.emit)
        self.batch_model_instance.batch_deleted_successfully.connect(self.data_changed.emit)
        self.batch_model_instance.batch_status_toggled.connect(self.data_changed.emit)

    def open_batch_window(self, stock_id, stock_name):
        if self.batch_view is not None:
            self.stack.removeWidget(self.batch_view)
            self.batch_view.deleteLater()
            self.batch_view = None

        # Rebuild the shared batch model's filtered table model for this stock item.
        batch_model = self.batch_model_instance.get_batch_model(stock_id)
        self.batch_view = StockBatchWindow(stock_id, stock_name, batch_model)

        self.batch_view.add_batch_requested.connect(self.open_add_batch_window)
        self.batch_view.edit_batch_requested.connect(self.open_edit_batch_window)
        self.batch_view.delete_batch_requested.connect(self.delete_batch)
        self.batch_view.toggle_status_requested.connect(self.toggle_batch_status)

        self.batch_view.back_requested.connect(self.close_batch_window)

        self.stack.addWidget(self.batch_view)
        self.stack.setCurrentWidget(self.batch_view)

    def close_batch_window(self):
        self.stack.setCurrentWidget(self.item_view)

        if self.batch_view is not None:
            self.stack.removeWidget(self.batch_view)
            self.batch_view.deleteLater()
            self.batch_view = None

    def open_add_batch_window(self):
        self.batch_form_window = AddBatchWindow(BatchMode.INSERT.value)
        self.batch_form_window.show()

        self.batch_form_window.batch_data_signal.connect(self.handle_add_batch)
        self.batch_model_instance.batch_inserted_successfully.connect(self.batch_form_window.close)

    def handle_add_batch(self, data: StockBatch):
        if validate_stock_batch(data):
            data.stock_id = self.batch_view.stock_id
            self.batch_model_instance.insert_batch(data)
        else:
            self.batch_form_window.show_warning("Validation Error", "Price and quantity must be positive, expiration must be after production date.")

    def open_edit_batch_window(self, batch_id: int):
        batch = self.batch_model_instance.get_batch(batch_id)
        if batch is None:
            return

        self.batch_form_window = AddBatchWindow(BatchMode.UPDATE.value)
        self.batch_form_window.load_data(batch)
        self.batch_form_window.show()

        self.batch_form_window.batch_update_data.connect(self.handle_edit_batch)
        self.batch_model_instance.batch_updated_successfully.connect(self.batch_form_window.close)

    def handle_edit_batch(self, data: StockBatch):
        if validate_stock_batch(data):
            data.stock_id = self.batch_view.stock_id
            self.batch_model_instance.update_batch(data)
        else:
            self.batch_form_window.show_warning("Validation Error", "Price and quantity must be positive, expiration must be after production date.")

    def delete_batch(self, batch_id: int):
        self.batch_model_instance.delete_batch(batch_id)

    def toggle_batch_status(self, batch_id: int):
        self.batch_model_instance.toggle_status(batch_id)

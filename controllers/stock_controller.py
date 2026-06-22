from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QStackedWidget

from views.stock_window import StockWindow
from views.add_stock_item_window import AddStockItemWindow, StockMode
from models.entities import StockItem
from Utilities.validate_data import validate_stock_item
from controllers.batch_controller import BatchController


class StockController(QObject):

    # Relayed to OrderController so the Order page refreshes on any stock change.
    data_changed = Signal()

    def __init__(self, stock_model, batch_model):
        super().__init__()

        self.stack = QStackedWidget()

        self.stock_form_window = None

        # ---- Level 1: Stock items ----
        self.stock_model = stock_model
        self.table_model = self.stock_model.get_stock_model()

        self.item_view = StockWindow(self.table_model)
        self.stack.addWidget(self.item_view)

        # ---- Level 2: Batches (owned child controller) ----
        # batch_model is the single shared StockBatchModel (also injected into
        # OrderModel) — persistent, not per-window. The batch page lives in this
        # controller's stack and returns to item_view, so both are passed in.
        self.batch_controller = BatchController(batch_model, self.stack, self.item_view)
        self.batch_controller.data_changed.connect(self.data_changed.emit)

        self.item_view.add_item_requested.connect(self.open_add_item_window)
        self.item_view.edit_item_requested.connect(self.open_edit_item_window)
        self.item_view.delete_item_requested.connect(self.handle_delete_item)

        self.item_view.view_batches_requested.connect(self.open_batch_window)

        self.stock_model.item_delete_rejected.connect(
            lambda msg: self.item_view.show_warning("Cannot Delete", msg))
        self.stock_model.item_insert_rejected.connect(
            lambda msg: self.stock_form_window and self.stock_form_window.show_warning("Duplicate Name", msg))

        # Relay stock-item changes to the Order page.
        self.stock_model.item_inserted_successfully.connect(self.data_changed.emit)
        self.stock_model.item_updated_successfully.connect(self.data_changed.emit)
        self.stock_model.item_deleted_successfully.connect(self.data_changed.emit)

        self.stock_view = self.stack

    # ──────────────────────────────────────────────
    #  Item operations
    # ──────────────────────────────────────────────

    def open_add_item_window(self):
        self.stock_form_window = AddStockItemWindow(StockMode.INSERT.value, units=self.stock_model.units)
        self.stock_form_window.show()

        self.stock_form_window.stock_item_data_signal.connect(self.handle_add_item)
        self.stock_model.item_inserted_successfully.connect(self.stock_form_window.close)

    def handle_add_item(self, data):
        if validate_stock_item(data):
            self.stock_model.insert_stock_item(data)
        else:
            self.stock_form_window.show_warning("Validation Error", "Name is required and unit must be selected.")

    def open_edit_item_window(self, item_id: int):
        item = self.stock_model.get_stock_item(item_id)

        if item is None:
            return

        self.stock_form_window = AddStockItemWindow(StockMode.UPDATE.value, units=self.stock_model.units)
        self.stock_form_window.load_data(item)
        self.stock_form_window.show()

        self.stock_form_window.stock_item_update_data.connect(self.handle_edit_item)
        self.stock_model.item_updated_successfully.connect(self.stock_form_window.close)

    def handle_edit_item(self, data):
        if validate_stock_item(data):
            self.stock_model.update_stock_item(data)
        else:
            self.stock_form_window.show_warning("Validation Error", "Name is required and unit must be selected.")

    def handle_delete_item(self, item_id: int):
        self.stock_model.delete_stock_item(item_id)

    # ──────────────────────────────────────────────
    #  Batch navigation (delegated to BatchController)
    # ──────────────────────────────────────────────

    def open_batch_window(self, stock_id):
        stock_name = self.stock_model.get_stock_name(stock_id)
        self.batch_controller.open_batch_window(stock_id, stock_name)

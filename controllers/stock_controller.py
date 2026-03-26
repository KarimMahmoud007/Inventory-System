from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from models.stock_model import StockModel
from views.stock_window import StockWindow
from views.addstock_window import AddStockWindow
from Utilities.validate_data import *


class StockController(QObject):

    def __init__(self):
        super().__init__()

        self.add_stock_window = None

        self.model = StockModel()

        self.table_model = self.model.get_stock_model()

        self.stock_view = StockWindow(self.table_model)

        self.stock_view.insert_request_signal.connect(self.open_add_stock_window)

        self.stock_view.delete_request_signal.connect(self.delete_item)

        self.stock_view.edit_request_signal.connect(self.open_edit_stock_window)

    #ADD STOCK START
    def open_add_stock_window(self):
        self.add_stock_window = AddStockWindow(1)
        self.add_stock_window.show()

        self.add_stock_window.stock_item_data_signal.connect(self.handle_add_stock_request)

        self.model.item_inserted_successfully.connect(self.add_stock_window.close)

    def handle_add_stock_request(self, data):
        if validate_data(data):
            self.model.post_data(data)
        else:
            QMessageBox.warning(self.add_stock_window, "Validation Error", "Please fill all fields correctly.")
    #ADD STOCK END

    #EDIT STOCK START
    def open_edit_stock_window(self, selected_row):
        stock_item = self.model.get_stock_data(selected_row)
        self.add_stock_window = AddStockWindow(2)
        self.add_stock_window.load_data(stock_item)
        self.add_stock_window.show()

        self.add_stock_window.stock_item_update_data.connect(
            lambda value: self.handle_edit_stock_request(value, selected_row),self
        )
        self.model.item_updated_successfully.connect(self.add_stock_window.close)

    def handle_edit_stock_request(self, wrapped_data, selected_row):
        if validate_data(wrapped_data):
            self.model.update_stock_data(wrapped_data, selected_row)
        else:
            QMessageBox.warning(self.add_stock_window, "Update Error", "Please fill all fields correctly.")
    #EDIT STOCK END

    #DELETE STOCK START
    def delete_item(self, selected_list):
        self.model.delete_stock_item(selected_list)
    #DELETE STOCK END

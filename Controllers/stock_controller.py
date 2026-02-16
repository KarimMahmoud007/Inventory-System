from PySide6.QtCore import QObject, Signal

from Model.stock_model import StockModel
from views.stock_window import StockWindow
from views.addstock_window import AddStockWindow


class StockController(QObject):


    def __init__(self):
        super().__init__()

        self.model = StockModel()

        self.table_model = self.model.get_stock_model()

        self.stock_view =StockWindow(self.table_model)

        self.stock_view.insert_view_signal.connect(self.insertView)

    def insertView(self):
        self.insert_view = AddStockWindow()
        self.insert_view.show()
        self.insert_view.data_received_signal.connect(self.dataInsert)

    def dataInsert(self,data):
        self.model.postData(data)











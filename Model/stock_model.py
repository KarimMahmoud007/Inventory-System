from PySide6.QtCore import QObject
from PySide6.QtSql import QSqlQuery
from Utilities.utilities import create_QtConnection
from PySide6.QtSql import QSqlTableModel

class StockModel (QObject):
    def __init__(self):
        super().__init__()
        self.db = create_QtConnection()


    def postData(self,data):

        row = self.model.rowCount()
        self.model.insertRow(row)

        self.model.setData(self.model.index(row, 1), data[0])
        self.model.setData(self.model.index(row, 2), data[1])
        self.model.setData(self.model.index(row, 3), float(data[2]))
        self.model.setData(self.model.index(row, 4), data[3])
        self.model.setData(self.model.index(row, 5), data[4])
        self.model.setData(self.model.index(row, 6), int(data[5]))

        if not self.model.submitAll():
            print("Submit failed:", self.model.lastError().text())
        else:
            print("Inserted into SQLite successfully")

    def get_stock_model(self):
        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("stock")
        self.model.select()
        return self.model









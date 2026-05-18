from PySide6.QtCore import QObject, Signal
from PySide6.QtSql import QSqlRelationalTableModel, QSqlRelation
from Utilities.utilities import create_QtConnection, get_catalog

class StockModel (QObject):
    item_deleted_successfully = Signal()
    item_updated_successfully = Signal()
    item_inserted_successfully = Signal()
    def __init__(self):
        super().__init__()
        self.db = create_QtConnection()
        self.model = None

    def get_stock_model(self):
        self.model = QSqlRelationalTableModel(self, self.db)
        self.model.setTable("stock")
        self.model.setRelation(2, QSqlRelation("units", "id", "name"))
        self.model.select()
        return self.model

    def refresh_model (self):
        self.model.refresh()

    def insert_stock_item(self, data):
        row = self.model.rowCount()
        self.model.insertRow(row)

        self.model.setData(self.model.index(row, 1), data[0])
        self.model.setData(self.model.index(row, 2), data[1])
        self.model.setData(self.model.index(row, 3), float(data[2]))            #CREATE
        self.model.setData(self.model.index(row, 4), data[3])
        self.model.setData(self.model.index(row, 5), data[4])
        self.model.setData(self.model.index(row, 6), int(data[5]))

        if not self.model.submitAll():
            print("Submit failed:", self.model.lastError().text())

        else:
            print("Inserted into SQLite successfully")
            get_catalog.cache_clear()
            self.item_inserted_successfully.emit()

    def get_stock_item(self, selected_row):
        data = []

        for col in range(1, self.model.columnCount()):
            index = self.model.index(selected_row, col)                         #READ
            data.append(self.model.data(index))

        return data

    def update_stock_item(self, data_list, selected_row):
        try:
            for col_index, value in enumerate(data_list , start=1):
                index = self.model.index(selected_row, col_index)

                self.model.setData(index, value)
            if not self.model.submitAll():
                print("Update failed:", self.model.lastError().text())          #UPDATE
            else:
                get_catalog.cache_clear()
                self.model.refresh()
                self.item_updated_successfully.emit()
        except IndexError:
            print(f"Error: Row {0} does not exist.")
        except Exception as e:
            print(f"An error occurred while updating stock data: {e}")



    def delete_stock_item(self,selected_list):
        for item in selected_list:
            self.model.removeRow(item.row())

        if not self.model.submitAll():
            print("Submit failed:", self.model.lastError().text())              #DELETE
        else:
            get_catalog.cache_clear()
            self.refresh_model()
            self.item_deleted_successfully.emit()

            print("Deleted successfully")



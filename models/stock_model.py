from PySide6.QtCore import QObject, Signal
from PySide6.QtSql import QSqlRelationalTableModel, QSqlRelation
from Utilities.utilities import create_QtConnection, get_catalog
from models.entities import StockItem

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

    def insert_stock_item(self, item: StockItem):
        row = self.model.rowCount()
        self.model.insertRow(row)

        self.model.setData(self.model.index(row, 1), item.name)
        self.model.setData(self.model.index(row, 2), item.unit_id)
        self.model.setData(self.model.index(row, 3), float(item.price))
        self.model.setData(self.model.index(row, 4), item.production_date)
        self.model.setData(self.model.index(row, 5), item.expiration_date)
        self.model.setData(self.model.index(row, 6), float(item.quantity))

        if not self.model.submitAll():
            print("Submit failed:", self.model.lastError().text())

        else:
            print("Inserted into SQLite successfully")
            get_catalog.cache_clear()
            self.item_inserted_successfully.emit()

    def get_stock_item(self, selected_row) -> StockItem:
        return StockItem(
            name=self.model.data(self.model.index(selected_row, 1)),
            unit_id=self.model.data(self.model.index(selected_row, 2)),
            price=float(self.model.data(self.model.index(selected_row, 3))),
            production_date=self.model.data(self.model.index(selected_row, 4)),
            expiration_date=self.model.data(self.model.index(selected_row, 5)),
            quantity=float(self.model.data(self.model.index(selected_row, 6))),
        )

    def update_stock_item(self, item: StockItem, selected_row):
        try:
            self.model.setData(self.model.index(selected_row, 1), item.name)
            self.model.setData(self.model.index(selected_row, 2), item.unit_id)
            self.model.setData(self.model.index(selected_row, 3), float(item.price))
            self.model.setData(self.model.index(selected_row, 4), item.production_date)
            self.model.setData(self.model.index(selected_row, 5), item.expiration_date)
            self.model.setData(self.model.index(selected_row, 6), float(item.quantity))
            if not self.model.submitAll():
                print("Update failed:", self.model.lastError().text())
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

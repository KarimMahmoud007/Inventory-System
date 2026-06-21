from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlRelationalTableModel, QSqlRelation, QSqlQuery
from models.entities import StockItem
from models.base_model import BaseModel


class StockModel(BaseModel):
    item_inserted_successfully = Signal()
    item_updated_successfully = Signal()
    item_deleted_successfully = Signal()
    item_insert_rejected = Signal(str)
    item_delete_rejected = Signal(str)

    def __init__(self):
        super().__init__()
        self.model = None

    def sync_model(self):
        self.model.select()
        self.invalidate_catalog()
        self.invalidate_recipe_requirements()
        self.model.refresh()

    def get_stock_model(self):
        self.model = QSqlRelationalTableModel(self, self.db)
        self.model.setTable("stock")
        self.model.setRelation(2, QSqlRelation("units", "id", "name"))
        self.model.select()
        return self.model

    def get_stock_name(self, stock_id: int) -> str:
        query = self.db.exec(f"SELECT name FROM stock WHERE id = {stock_id}")
        if query.next():
            return query.value(0)
        return ""

    def _stock_name_exists(self, name: str) -> bool:
        query = QSqlQuery(self.db)
        query.prepare("SELECT 1 FROM stock WHERE name = ? COLLATE NOCASE LIMIT 1")
        query.addBindValue(name.strip())
        query.exec()
        return query.next()

    def insert_stock_item(self, item: StockItem):
        if self._stock_name_exists(item.name):
            self.item_insert_rejected.emit(
                f"A stock item named '{item.name.strip()}' already exists."
            )
            return

        row = self.model.rowCount()
        self.model.insertRow(row)
        self.model.setData(self.model.index(row, 1), item.name)
        self.model.setData(self.model.index(row, 2), item.unit_id)

        if not self.model.submitAll():
            print("Submit failed:", self.model.lastError().text())
        else:
            self.sync_model()
            self.item_inserted_successfully.emit()

    def get_stock_item(self, item_id: int) -> StockItem | None:
        query = QSqlQuery(self.db)
        query.prepare("SELECT id, name, unit_of_measure FROM stock WHERE id = ?")
        query.addBindValue(item_id)
        query.exec()
        if query.next():
            return StockItem(
                id=query.value(0),
                name=query.value(1),
                unit_id=query.value(2),
            )
        return None

    def update_stock_item(self, item: StockItem):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE stock SET name=?, unit_of_measure=? WHERE id=?")
        query.addBindValue(item.name)
        query.addBindValue(item.unit_id)
        query.addBindValue(item.id)
        if not query.exec():
            print("Update failed:", query.lastError().text())
        else:
            self.sync_model()
            self.item_updated_successfully.emit()

    def delete_stock_item(self, item_id: int):
        query = QSqlQuery(self.db)
        query.prepare("DELETE FROM stock WHERE id=?")
        query.addBindValue(item_id)
        if not query.exec():
            if query.lastError().nativeErrorCode() in ("787", "19"):
                self.item_delete_rejected.emit(
                    "Cannot delete this stock item because it still has batches. "
                    "Delete its batches first."
                )
            else:
                print("Delete failed:", query.lastError().text())
        else:
            self.sync_model()
            self.item_deleted_successfully.emit()
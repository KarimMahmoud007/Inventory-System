from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlRelationalTableModel, QSqlRelation, QSqlQuery
from models.entities import StockItem
from models.base_model import BaseModel


# setRelation replaces the related column's field name (unit_of_measure becomes
# 'units_name_2'), so fieldIndex() can't find it and the position has to be named
# here — once, next to the setRelation call that creates the coupling.
UNIT_COLUMN = 2


class StockModel(BaseModel):
    item_inserted_successfully = Signal()
    item_updated_successfully = Signal()
    item_deleted_successfully = Signal()
    item_insert_rejected = Signal(str)
    item_delete_rejected = Signal(str)
    # Any write that failed for a reason we don't have a specific rejection for.
    # Without this a failed save is indistinguishable from a successful one.
    operation_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.table = None

    @staticmethod
    def _is_fk_violation(error) -> bool:
        """Whether a failed write was blocked by the stock_batch foreign key.

        Codes rather than one code: a plain FK violation is SQLITE_CONSTRAINT_
        FOREIGNKEY (787), but ON DELETE RESTRICT is enforced through an internal
        trigger and surfaces as 1811 instead. The message check is the backstop,
        since the extended codes vary by SQLite build.
        """
        return (error.nativeErrorCode() in ("19", "787", "1811")
                or "FOREIGN KEY" in error.text().upper())

    def _failed(self, action: str, error) -> None:
        print(f"{action} failed:", error.text())
        self.operation_failed.emit(f"{action} failed: {error.text()}")

    def sync_model(self):
        self.table.select()
        self.invalidate_catalog()
        self.invalidate_recipe_requirements()
        self.table.refresh()

    def get_stock_table(self):
        self.table = QSqlRelationalTableModel(self, self.db)
        self.table.setTable("stock")
        self.table.setRelation(UNIT_COLUMN, QSqlRelation("units", "id", "name"))
        self.table.select()
        return self.table

    def get_stock_name(self, stock_id: int) -> str:
        query = QSqlQuery(self.db)
        query.prepare("SELECT name FROM stock WHERE id = ?")
        query.addBindValue(stock_id)
        query.exec()
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

        row = self.table.rowCount()
        self.table.insertRow(row)
        # By field name where possible; the unit column is the relation, so it
        # goes through UNIT_COLUMN (see the constant).
        self.table.setData(self.table.index(row, self.table.fieldIndex("name")), item.name)
        self.table.setData(self.table.index(row, UNIT_COLUMN), item.unit_id)

        if not self.table.submitAll():
            self.table.revertAll()
            self._failed("Adding the stock item", self.table.lastError())
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
            self._failed("Updating the stock item", query.lastError())
        else:
            self.sync_model()
            self.item_updated_successfully.emit()

    def delete_stock_item(self, item_id: int):
        query = QSqlQuery(self.db)
        query.prepare("DELETE FROM stock WHERE id=?")
        query.addBindValue(item_id)
        if not query.exec():
            if self._is_fk_violation(query.lastError()):
                self.item_delete_rejected.emit(
                    "Cannot delete this stock item because it still has batches. "
                    "Delete its batches first."
                )
            else:
                self._failed("Deleting the stock item", query.lastError())
        else:
            self.sync_model()
            self.item_deleted_successfully.emit()
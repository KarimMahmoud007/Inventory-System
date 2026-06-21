from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlTableModel, QSqlQuery
from models.entities import StockBatch
from models.base_model import BaseModel


class StockBatchModel(BaseModel):
    batch_inserted_successfully = Signal()
    batch_updated_successfully = Signal()
    batch_deleted_successfully = Signal()
    batch_status_toggled = Signal()

    def __init__(self):
        super().__init__()
        self.model = None

    def get_batch_model(self, stock_id: int):
        self.model = QSqlTableModel(self, self.db)
        self.model.setTable("stock_batch")
        self.model.setFilter(f"stock_id = {stock_id}")
        self.model.select()
        return self.model

    def insert_batch(self, batch: StockBatch):
        row = self.model.rowCount()
        self.model.insertRow(row)
        self.model.setData(self.model.index(row, 1), batch.stock_id)
        self.model.setData(self.model.index(row, 2), float(batch.price))
        self.model.setData(self.model.index(row, 3), batch.production_date)
        self.model.setData(self.model.index(row, 4), batch.expiration_date)
        self.model.setData(self.model.index(row, 5), float(batch.quantity))

        if not self.model.submitAll():
            print("Batch insert failed:", self.model.lastError().text())
        else:
            self.model.select()
            self.model.refresh()
            self.invalidate_available_stock()
            self.batch_inserted_successfully.emit()

    def get_batch(self, batch_id: int) -> StockBatch | None:
        query = QSqlQuery(self.db)
        query.prepare("SELECT id, stock_id, price, production_date, expiration_date, quantity, status FROM stock_batch WHERE id=?")
        query.addBindValue(batch_id)
        query.exec()
        if query.next():
            return StockBatch(
                id=query.value(0),
                stock_id=query.value(1),
                price=query.value(2),
                production_date=query.value(3),
                expiration_date=query.value(4),
                quantity=query.value(5),
                status=query.value(6),
            )
        return None

    def update_batch(self, batch: StockBatch):
        query = QSqlQuery(self.db)
        query.prepare("UPDATE stock_batch SET price=?, production_date=?, expiration_date=?, quantity=? WHERE id=?")
        query.addBindValue(float(batch.price))
        query.addBindValue(batch.production_date)
        query.addBindValue(batch.expiration_date)
        query.addBindValue(float(batch.quantity))
        query.addBindValue(batch.id)
        if not query.exec():
            print("Batch update failed:", query.lastError().text())
        else:
            self.model.select()
            self.model.refresh()
            self.invalidate_available_stock()
            self.batch_updated_successfully.emit()

    def delete_batch(self, batch_id: int):
        query = QSqlQuery(self.db)
        query.prepare("DELETE FROM stock_batch WHERE id=?")
        query.addBindValue(batch_id)
        if not query.exec():
            print("Batch delete failed:", query.lastError().text())
        else:
            self.model.select()
            self.model.refresh()
            self.invalidate_available_stock()
            self.batch_deleted_successfully.emit()

    def toggle_status(self, batch_id: int):
        query = QSqlQuery(self.db)
        query.prepare("SELECT status FROM stock_batch WHERE id=?")
        query.addBindValue(batch_id)
        query.exec()
        if not query.next():
            return

        current = query.value(0)
        new_status = "out_of_stock" if current == "available" else "available"

        query.prepare("UPDATE stock_batch SET status=? WHERE id=?")
        query.addBindValue(new_status)
        query.addBindValue(batch_id)
        if not query.exec():
            print("Status toggle failed:", query.lastError().text())
        else:
            self.model.select()
            self.model.refresh()
            self.invalidate_available_stock()
            self.batch_status_toggled.emit()

    # ──────────────────────────────────────────────
    #  Public batch API for the order path (no UI model / no signals)
    # ──────────────────────────────────────────────
    def get_available_batches(self, stock_id: int) -> list[tuple]:
        """Available batches for a stock item, oldest-first (FIFO by added_at).

        Returns a list of (id, quantity, price) tuples (quantity/price as float).
        Pure read — does not touch the UI table model. Shared by OrderModel's cost
        projection and FIFO deduction so they price batches identically."""
        query = QSqlQuery(self.db)
        query.prepare(
            "SELECT id, quantity, price FROM stock_batch "
            "WHERE stock_id = ? AND status = 'available' AND quantity > 0 "
            "ORDER BY added_at ASC, id ASC"
        )
        query.addBindValue(stock_id)
        query.exec()
        rows = []
        while query.next():
            rows.append((
                query.value(0),
                float(query.value(1)),
                float(query.value(2)),
            ))
        return rows

    def deduct_batch(self, batch_id: int, amount: float) -> bool:
        """Subtract `amount` from a batch's remaining quantity, flipping it to
        out_of_stock (and clamping quantity to exactly 0) when depleted.

        Runs on the shared DB connection, so it participates in any transaction the
        caller (OrderModel.place_order) has already opened. Does not refresh the UI
        table model or emit signals. Returns whether the UPDATE succeeded."""
        query = QSqlQuery(self.db)
        query.prepare(
            "UPDATE stock_batch "
            "SET quantity = CASE WHEN quantity - ? <= 1e-9 THEN 0 ELSE quantity - ? END, "
            "    status = CASE WHEN quantity - ? <= 1e-9 THEN 'out_of_stock' ELSE status END "
            "WHERE id = ?"
        )
        query.addBindValue(amount)   # quantity CASE test
        query.addBindValue(amount)   # quantity CASE else (decrement)
        query.addBindValue(amount)   # status CASE test
        query.addBindValue(batch_id)
        return query.exec()



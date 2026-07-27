from functools import lru_cache
from PySide6.QtSql import QSqlQuery
from models.base_model import BaseModel, _db
from models.entities import BatchConsumption


def total_cost(consumptions: list[BatchConsumption]) -> float:
    """Cost of a set of consumed batches. Pure — no DB, no Qt."""
    return sum(c.amount * c.unit_price for c in consumptions)


class FinanceModel(BaseModel):
    """Owns the money side of an order: the per-batch consumption ledger, the
    orders.cost column, and the cached reporting reads behind the Finance page.

    OrderModel creates the order with cost 0 and hands over the batches it
    deducted; apply_order_cost prices them and fills the column. It runs on the
    shared connection with no transaction of its own, so it joins whatever
    transaction the caller has open."""

    # ──────────────────────────────────────────────
    #  Write path (inside OrderModel.place_order's transaction)
    # ──────────────────────────────────────────────
    def apply_order_cost(self, order_id: int, consumptions: list[BatchConsumption]):
        """Persist the ledger rows and set orders.cost to their total.
        Returns the cost, or None on any failure (caller rolls back)."""
        query = QSqlQuery(self.db)

        for c in consumptions:
            query.prepare(
                "INSERT INTO order_batch_consumption "
                "(order_id, stock_batch_id, amount, unit_price) VALUES (?, ?, ?, ?)"
            )
            query.addBindValue(order_id)
            query.addBindValue(c.stock_batch_id)
            query.addBindValue(float(c.amount))
            query.addBindValue(float(c.unit_price))
            if not query.exec():
                print("Failed to insert consumption row:", query.lastError().text())
                return None

        cost = total_cost(consumptions)
        query.prepare("UPDATE orders SET cost = ? WHERE id = ?")
        query.addBindValue(cost)
        query.addBindValue(order_id)
        if not query.exec():
            print("Failed to store order cost:", query.lastError().text())
            return None

        return cost

    # ──────────────────────────────────────────────
    #  Cached reporting reads (Finance page)
    # ──────────────────────────────────────────────
    @staticmethod
    @lru_cache
    def get_orders_summary():
        """One row per non-draft order, newest first, as a tuple of dicts with
        profit computed here. Cached — cleared by invalidate_finance() after a
        placement."""
        query = QSqlQuery(_db())
        query.exec(
            "SELECT id, created_at, subtotal, cost FROM orders "
            "WHERE status != 'draft' ORDER BY id DESC"
        )
        rows = []
        while query.next():
            subtotal = float(query.value(2))
            cost = float(query.value(3))
            rows.append({
                "id": query.value(0),
                "created_at": query.value(1),
                "subtotal": subtotal,
                "cost": cost,
                "profit": subtotal - cost,
            })
        return tuple(rows)

    @staticmethod
    @lru_cache
    def get_totals():
        """(revenue, cost, profit) across all non-draft orders."""
        query = QSqlQuery(_db())
        query.exec(
            "SELECT COALESCE(SUM(subtotal), 0), COALESCE(SUM(cost), 0) FROM orders "
            "WHERE status != 'draft'"
        )
        if query.next():
            revenue = float(query.value(0))
            cost = float(query.value(1))
            return revenue, cost, revenue - cost
        return 0.0, 0.0, 0.0

    @staticmethod
    @lru_cache
    def get_order_cost_breakdown(order_id):
        """Per-batch cost detail for one order, as a tuple of
        (stock_name, unit, batch_id, amount, unit_price, line_cost) tuples."""
        query = QSqlQuery(_db())
        query.prepare("""
            SELECT s.name, u.name, c.stock_batch_id, c.amount, c.unit_price,
                   c.amount * c.unit_price
            FROM order_batch_consumption c
            JOIN stock_batch b ON c.stock_batch_id = b.id
            JOIN stock s       ON b.stock_id = s.id
            JOIN units u       ON s.unit_of_measure = u.id
            WHERE c.order_id = ?
            ORDER BY s.name, c.id
        """)
        query.addBindValue(order_id)
        query.exec()
        rows = []
        while query.next():
            rows.append((
                query.value(0),          # stock name
                query.value(1),          # stock unit
                query.value(2),          # batch id
                float(query.value(3)),   # amount consumed
                float(query.value(4)),   # per-unit price
                float(query.value(5)),   # line cost
            ))
        return tuple(rows)

    def invalidate_finance(self):
        """Clear every finance cache. Called post-commit by OrderModel.place_order."""
        FinanceModel.get_orders_summary.cache_clear()
        FinanceModel.get_totals.cache_clear()
        FinanceModel.get_order_cost_breakdown.cache_clear()

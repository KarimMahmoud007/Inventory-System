from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlQuery
from models.base_model import BaseModel
from models.entities import Order, Shortage, ValidationResult
from Utilities.units import convert


class OrderModel(BaseModel):
    order_placed_successfully = Signal(int)
    order_place_rejected = Signal(str)

    # ──────────────────────────────────────────────
    #  Recipe → ingredient requirements
    # ──────────────────────────────────────────────
    def _recipe_requirements(self, item_id: int):
        """Return the ingredient rows for a recipe (items) row.

        Each tuple is (stock_id, stock_name, amount, recipe_unit, stock_unit).
        An empty list means the recipe has no ingredient mapping — the caller
        must fail loudly rather than silently treating it as available.
        """
        query = QSqlQuery(self.db)
        query.prepare("""
            SELECT ir.stock_id, s.name, ir.amount, ru.name, su.name
            FROM items_recipe ir
            JOIN stock s  ON ir.stock_id = s.id
            JOIN units ru ON ir.unit = ru.id
            JOIN units su ON s.unit_of_measure = su.id
            WHERE ir.item_id = ?
        """)
        query.addBindValue(item_id)
        query.exec()
        rows = []
        while query.next():
            rows.append((
                query.value(0),          # stock_id
                query.value(1),          # stock name
                float(query.value(2)),   # amount
                query.value(3),          # recipe unit name
                query.value(4),          # stock unit name
            ))
        return rows

    # ──────────────────────────────────────────────
    #  Dry-run validation (no real stock touched)
    # ──────────────────────────────────────────────
    def validate_stock(self, order: Order) -> ValidationResult:
        """Expand each order item into its recipe ingredient requirements, sum the
        required amount per stock item (in that item's unit), and compare against the
        cached available stock. Returns which ingredients are short and any fail-loud
        errors (missing mapping / incompatible units). Touches no real stock."""
        errors: list[str] = []
        # stock_id -> [stock_name, stock_unit, required_total]
        required: dict[int, list] = {}

        for item in order.items:
            if item.quantity <= 0:
                continue
            reqs = self._recipe_requirements(item.recipe_id)
            if not reqs:
                errors.append(
                    f"Recipe '{item.recipe_name}' has no ingredient mapping."
                )
                continue
            for stock_id, stock_name, amount, recipe_unit, stock_unit in reqs:
                try:
                    in_stock_unit = convert(amount, recipe_unit, stock_unit)
                except ValueError as exc:
                    errors.append(
                        f"Recipe '{item.recipe_name}', ingredient '{stock_name}': {exc}"
                    )
                    continue
                entry = required.setdefault(stock_id, [stock_name, stock_unit, 0.0])
                entry[2] += in_stock_unit * item.quantity

        shortages: list[Shortage] = []
        for stock_id, (stock_name, stock_unit, total_required) in required.items():
            available = self.get_available_stock(stock_id)
            if total_required > available + 1e-9:
                shortages.append(Shortage(
                    stock_id=stock_id,
                    stock_name=stock_name,
                    required=round(total_required, 4),
                    available=round(available, 4),
                    unit=stock_unit,
                ))

        ok = not shortages and not errors
        return ValidationResult(ok=ok, shortages=shortages, errors=errors)

    # ──────────────────────────────────────────────
    #  Place order (persist + deduct, transactional)
    # ──────────────────────────────────────────────
    def place_order(self, order: Order):
        result = self.validate_stock(order)
        if not result.ok:
            msg_parts = list(result.errors)
            for s in result.shortages:
                msg_parts.append(
                    f"{s.stock_name}: need {s.required} {s.unit}, "
                    f"have {s.available} {s.unit}"
                )
            self.order_place_rejected.emit("\n".join(msg_parts))
            return

        self.db.transaction()
        query = QSqlQuery(self.db)

        query.prepare("INSERT INTO orders (status) VALUES ('placed')")
        if not query.exec():
            print("Failed to insert order:", query.lastError().text())
            self.db.rollback()
            self.order_place_rejected.emit("Could not create the order.")
            return
        order_id = query.lastInsertId()

        for item in order.items:
            if item.quantity <= 0:
                continue
            query.prepare(
                "INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)"
            )
            query.addBindValue(order_id)
            query.addBindValue(item.recipe_id)
            query.addBindValue(item.quantity)
            if not query.exec():
                print("Failed to insert order item:", query.lastError().text())
                self.db.rollback()
                self.order_place_rejected.emit("Could not save order items.")
                return

        if not self._deduct_for_order(order, query):
            self.db.rollback()
            self.order_place_rejected.emit("Stock deduction failed; order rolled back.")
            return

        self.db.commit()
        self.invalidate_available_stock()
        self.order_placed_successfully.emit(order_id)
        print(f"Order {order_id} placed successfully")

    # ──────────────────────────────────────────────
    #  FIFO deduction (oldest batch first)
    # ──────────────────────────────────────────────
    def _deduct_for_order(self, order: Order, query: QSqlQuery) -> bool:
        """Deduct each required ingredient amount from its available batches,
        oldest-first (FIFO by added_at). Rolls the remainder over to the next batch
        and flips a depleted batch to out_of_stock. Runs inside place_order's
        transaction; returns False on any failure so the caller can roll back."""
        # Sum requirements per stock item, in that item's unit.
        required: dict[int, list] = {}  # stock_id -> [stock_unit, amount]
        for item in order.items:
            if item.quantity <= 0:
                continue
            for stock_id, _name, amount, recipe_unit, stock_unit in self._recipe_requirements(item.recipe_id):
                in_stock_unit = convert(amount, recipe_unit, stock_unit)
                entry = required.setdefault(stock_id, [stock_unit, 0.0])
                entry[1] += in_stock_unit * item.quantity

        for stock_id, (_stock_unit, remaining) in required.items():
            batches = QSqlQuery(self.db)
            batches.prepare(
                "SELECT id, quantity FROM stock_batch "
                "WHERE stock_id = ? AND status = 'available' AND quantity > 0 "
                "ORDER BY added_at ASC, id ASC"
            )
            batches.addBindValue(stock_id)
            batches.exec()

            batch_rows = []
            while batches.next():
                batch_rows.append((batches.value(0), float(batches.value(1))))

            for batch_id, batch_qty in batch_rows:
                if remaining <= 1e-9:
                    break
                take = min(batch_qty, remaining)
                new_qty = batch_qty - take
                remaining -= take

                if new_qty <= 1e-9:
                    query.prepare(
                        "UPDATE stock_batch SET quantity = 0, status = 'out_of_stock' WHERE id = ?"
                    )
                    query.addBindValue(batch_id)
                else:
                    query.prepare("UPDATE stock_batch SET quantity = ? WHERE id = ?")
                    query.addBindValue(new_qty)
                    query.addBindValue(batch_id)
                if not query.exec():
                    print("Batch deduction failed:", query.lastError().text())
                    return False

            if remaining > 1e-9:
                # Should not happen — validate_stock ran first — but never over-commit.
                print(f"Insufficient stock for stock_id={stock_id} during deduction")
                return False

        return True
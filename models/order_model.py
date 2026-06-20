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

    def _required_by_stock(self, order: Order):
        """Sum the required amount per stock item (converted into that item's own
        unit), across every order item. Returns (required, errors) where
        required maps stock_id -> [stock_name, stock_unit, amount]. Shared by the
        dry-run, cost projection, and the real deduction so they never diverge."""
        errors: list[str] = []
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

        return required, errors

    # ──────────────────────────────────────────────
    #  Money: subtotal (selling price) + cost (batch price)
    # ──────────────────────────────────────────────
    def _recipe_price(self, item_id: int) -> float:
        """Selling price of a recipe (items.price)."""
        query = QSqlQuery(self.db)
        query.prepare("SELECT price FROM items WHERE id = ?")
        query.addBindValue(item_id)
        query.exec()
        if query.next():
            return float(query.value(0))
        return 0.0

    def _order_subtotal(self, order: Order) -> float:
        """Revenue: sum of recipe selling price × quantity."""
        return sum(
            self._recipe_price(item.recipe_id) * item.quantity
            for item in order.items if item.quantity > 0
        )

    def _project_cost(self, required: dict) -> float:
        """Estimate ingredient cost by walking each stock item's batches oldest-first
        and pricing the consumed amount at each batch's per-unit price — WITHOUT
        mutating stock. Mirrors the real FIFO deduction so the live estimate matches
        the finalized cost. `required` is the dict from _required_by_stock."""
        total = 0.0
        for stock_id, entry in required.items():
            remaining = entry[2]
            if remaining <= 1e-9:
                continue
            batches = QSqlQuery(self.db)
            batches.prepare(
                "SELECT quantity, price FROM stock_batch "
                "WHERE stock_id = ? AND status = 'available' AND quantity > 0 "
                "ORDER BY added_at ASC, id ASC"
            )
            batches.addBindValue(stock_id)
            batches.exec()
            while remaining > 1e-9 and batches.next():
                batch_qty = float(batches.value(0))
                price = float(batches.value(1))
                take = min(batch_qty, remaining)
                total += take * price
                remaining -= take
        return total

    # ──────────────────────────────────────────────
    #  Dry-run validation (no real stock touched)
    # ──────────────────────────────────────────────
    def validate_stock(self, order: Order) -> ValidationResult:
        """Compare required stock per ingredient against the cached available stock,
        and attach the live subtotal + estimated cost. Returns which ingredients are
        short and any fail-loud errors (missing mapping / incompatible units).
        Touches no real stock."""
        required, errors = self._required_by_stock(order)

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
        return ValidationResult(
            ok=ok,
            shortages=shortages,
            errors=errors,
            subtotal=self._order_subtotal(order),
            est_cost=self._project_cost(required),
        )

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

        cost = self._deduct_for_order(order, query)
        if cost is None:
            self.db.rollback()
            self.order_place_rejected.emit("Stock deduction failed; order rolled back.")
            return

        subtotal = self._order_subtotal(order)
        query.prepare("UPDATE orders SET subtotal = ?, cost = ? WHERE id = ?")
        query.addBindValue(subtotal)
        query.addBindValue(cost)
        query.addBindValue(order_id)
        if not query.exec():
            print("Failed to store order totals:", query.lastError().text())
            self.db.rollback()
            self.order_place_rejected.emit("Could not store order totals.")
            return

        self.db.commit()
        self.invalidate_available_stock()
        order.id = order_id
        order.subtotal = subtotal
        order.cost = cost
        self.order_placed_successfully.emit(order_id)
        print(f"Order {order_id} placed: subtotal={subtotal}, cost={cost}")

    # ──────────────────────────────────────────────
    #  FIFO deduction (oldest batch first), returns total cost
    # ──────────────────────────────────────────────
    def _deduct_for_order(self, order: Order, query: QSqlQuery):
        """Deduct each required ingredient amount from its available batches,
        oldest-first (FIFO by added_at), pricing consumed amounts at each batch's
        per-unit price. Rolls the remainder over to the next batch and flips a
        depleted batch to out_of_stock. Runs inside place_order's transaction.
        Returns the total ingredient cost, or None on any failure (caller rolls back)."""
        required, _errors = self._required_by_stock(order)
        total_cost = 0.0

        for stock_id, entry in required.items():
            remaining = entry[2]
            batches = QSqlQuery(self.db)
            batches.prepare(
                "SELECT id, quantity, price FROM stock_batch "
                "WHERE stock_id = ? AND status = 'available' AND quantity > 0 "
                "ORDER BY added_at ASC, id ASC"
            )
            batches.addBindValue(stock_id)
            batches.exec()

            batch_rows = []
            while batches.next():
                batch_rows.append((
                    batches.value(0),
                    float(batches.value(1)),
                    float(batches.value(2)),
                ))

            for batch_id, batch_qty, price in batch_rows:
                if remaining <= 1e-9:
                    break
                take = min(batch_qty, remaining)
                new_qty = batch_qty - take
                remaining -= take
                total_cost += take * price

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
                    return None

            if remaining > 1e-9:
                # Should not happen — validate_stock ran first — but never over-commit.
                print(f"Insufficient stock for stock_id={stock_id} during deduction")
                return None

        return total_cost

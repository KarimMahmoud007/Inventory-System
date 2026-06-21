from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlQuery
from models.base_model import BaseModel
from models.entities import Order, Shortage, ValidationResult
from Utilities.units import convert


class OrderModel(BaseModel):
    order_placed_successfully = Signal(int)
    order_place_rejected = Signal(str)

    def __init__(self, batch_model):
        """`batch_model` is the shared StockBatchModel injected by MainWindow — used
        for all stock_batch access during FIFO deduction (read available batches,
        write the deducted quantities)."""
        super().__init__()
        self.batches = batch_model

    # ──────────────────────────────────────────────
    #  Recipe → ingredient requirements
    # ──────────────────────────────────────────────
    def _recipe_requirements(self, item_id: int):
        """Cached ingredient rows for a recipe (items) row — thin wrapper over
        BaseModel.get_recipe_requirements. Returns a tuple of
        (stock_id, stock_name, amount, recipe_unit, stock_unit) tuples; an empty
        tuple means no ingredient mapping (caller must fail loudly)."""
        return self.get_recipe_requirements(item_id)

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
    def _order_subtotal(self, order: Order) -> float:
        """Revenue: sum of recipe selling price × quantity. Prices come from the cached
        recipes catalog (BaseModel.get_recipes_catalog) — no per-item DB query. A recipe
        absent from the catalog has no ingredient mapping and is rejected by
        validate_stock anyway, so a 0.0 fallback never reaches a placed order."""
        price_by_id = {r["id"]: float(r["price"]) for r in self.recipes_catalog}
        return sum(
            price_by_id.get(item.recipe_id, 0.0) * item.quantity
            for item in order.items if item.quantity > 0
        )

    # ──────────────────────────────────────────────
    #  Dry-run validation (no real stock touched)
    # ──────────────────────────────────────────────
    def validate_stock(self, order: Order) -> ValidationResult:
        """Compare required stock per ingredient against the cached available stock,
        and attach the live subtotal. Returns which ingredients are short and any
        fail-loud errors (missing mapping / incompatible units). Touches no real
        stock. Cost/profit are not estimated here — they are computed exactly at
        placement (see _deduct_for_order)."""
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

        cost = self._deduct_for_order(order)
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
    def _deduct_for_order(self, order: Order):
        """Deduct each required ingredient amount from its available batches,
        oldest-first (FIFO by added_at), pricing consumed amounts at each batch's
        per-unit price. Rolls the remainder over to the next batch and flips a
        depleted batch to out_of_stock (via StockBatchModel.deduct_batch). Runs inside
        place_order's transaction — deduct_batch shares the same DB connection.
        Returns the total ingredient cost, or None on any failure (caller rolls back)."""
        required, _errors = self._required_by_stock(order)
        total_cost = 0.0

        for stock_id, entry in required.items():
            remaining = entry[2]

            for batch_id, batch_qty, price in self.batches.get_available_batches(stock_id):
                if remaining <= 1e-9:
                    break
                take = min(batch_qty, remaining)
                remaining -= take
                total_cost += take * price

                if not self.batches.deduct_batch(batch_id, take):
                    print("Batch deduction failed for batch", batch_id)
                    return None

            if remaining > 1e-9:
                # Should not happen — validate_stock ran first — but never over-commit.
                print(f"Insufficient stock for stock_id={stock_id} during deduction")
                return None

        return total_cost

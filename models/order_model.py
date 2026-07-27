from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlQuery
from models.base_model import BaseModel
from models.entities import BatchConsumption, Order, Shortage, ValidationResult
from Utilities.units import convert


class OrderFailed(Exception):
    """Raised inside place_order's transaction block to abort and roll back.

    Carries the user-facing message; the caller emits it as order_place_rejected.
    """


def _abort(message: str, detail=None):
    """Log the technical detail, raise the user-facing message."""
    if detail is not None:
        print(f"{message} — {detail}")
    raise OrderFailed(message)


class OrderModel(BaseModel):
    order_placed_successfully = Signal(int)
    order_place_rejected = Signal(str)

    def __init__(self, batch_model, finance_model):
        """`batch_model` is the shared StockBatchModel injected by MainWindow — used
        for all stock_batch access during FIFO deduction (read available batches,
        write the deducted quantities). `finance_model` owns costing: this model
        creates the order with cost 0 and hands it the batches it consumed."""
        super().__init__()
        self.batches = batch_model
        self.finance = finance_model

    # ──────────────────────────────────────────────
    #  Recipe → ingredient requirements
    # ──────────────────────────────────────────────
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
            reqs = self.get_recipe_requirements(item.recipe_id)
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
        placement by FinanceModel from the consumed batches."""
        required, errors = self._required_by_stock(order)
        return self._check_availability(required, errors, self._order_subtotal(order))

    def _check_availability(self, required, errors, subtotal) -> ValidationResult:
        """The shortage comparison, split out so place_order can reuse one
        requirement computation instead of redoing the expansion."""
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

        return ValidationResult(
            ok=not shortages and not errors,
            shortages=shortages,
            errors=errors,
            subtotal=subtotal,
        )

    # ──────────────────────────────────────────────
    #  Place order (persist + deduct, transactional)
    # ──────────────────────────────────────────────
    def place_order(self, order: Order):
        """Persist the order and deduct its stock, or nothing at all.

        Re-validates first — this is NOT redundant with the controller's dry-run,
        which is debounced and can be stale by the time Place is clicked. The
        requirement expansion is computed once here and threaded through to the
        deduction, so the two can't disagree."""
        required, errors = self._required_by_stock(order)
        subtotal = self._order_subtotal(order)
        result = self._check_availability(required, errors, subtotal)
        if not result.ok:
            msg_parts = list(result.errors)
            for s in result.shortages:
                msg_parts.append(
                    f"{s.stock_name}: need {s.required} {s.unit}, "
                    f"have {s.available} {s.unit}"
                )
            self.order_place_rejected.emit("\n".join(msg_parts))
            return

        try:
            with self.transaction():
                order_id = self._persist_order(order, subtotal)
                consumptions = self._deduct_for_order(required)
                # Finance owns the cost column; it shares this connection, so its
                # writes join this transaction and roll back with it.
                cost = self.finance.apply_order_cost(order_id, consumptions)
                if cost is None:
                    _abort("Could not record order cost.")
        except OrderFailed as exc:
            self.order_place_rejected.emit(str(exc))
            return

        self.invalidate_available_stock()
        self.finance.invalidate_finance()
        order.id = order_id
        order.subtotal = subtotal
        order.cost = cost
        self.order_placed_successfully.emit(order_id)
        print(f"Order {order_id} placed: subtotal={subtotal}, cost={cost}")

    def _persist_order(self, order: Order, subtotal: float) -> int:
        """Write the order header and its items. Raises OrderFailed on any error,
        which rolls the caller's transaction back."""
        query = QSqlQuery(self.db)

        # cost stays at the schema default 0 — FinanceModel fills it in.
        query.prepare("INSERT INTO orders (status, subtotal) VALUES ('placed', ?)")
        query.addBindValue(subtotal)
        if not query.exec():
            _abort("Could not create the order.", query.lastError().text())
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
                _abort("Could not save order items.", query.lastError().text())

        return order_id

    # ──────────────────────────────────────────────
    #  FIFO deduction (oldest batch first), returns what was consumed
    # ──────────────────────────────────────────────
    def _deduct_for_order(self, required: dict):
        """Deduct each required ingredient amount from its available batches,
        oldest-first (FIFO by added_at). Rolls the remainder over to the next batch
        and flips a depleted batch to out_of_stock (via StockBatchModel.deduct_batch).

        Takes the ALREADY-VALIDATED requirements map from place_order rather than
        recomputing it, so deducting against unchecked requirements isn't
        expressible. Runs inside place_order's transaction — deduct_batch shares
        the same DB connection. Returns the list of BatchConsumption records
        (batch, amount taken, that batch's per-unit price) for FinanceModel to
        price, and raises OrderFailed on any failure. No money is computed here."""
        consumptions: list[BatchConsumption] = []

        for stock_id, entry in required.items():
            remaining = entry[2]

            for batch_id, batch_qty, price in self.batches.get_available_batches(stock_id):
                if remaining <= 1e-9:
                    break
                take = min(batch_qty, remaining)
                remaining -= take

                if not self.batches.deduct_batch(batch_id, take):
                    _abort("Stock deduction failed; order rolled back.",
                           f"batch {batch_id}")

                consumptions.append(BatchConsumption(
                    stock_batch_id=batch_id,
                    stock_id=stock_id,
                    amount=take,
                    unit_price=price,
                ))

            if remaining > 1e-9:
                # Should not happen — availability was checked first — but never
                # over-commit.
                _abort("Stock deduction failed; order rolled back.",
                       f"insufficient stock for stock_id={stock_id}")

        return consumptions

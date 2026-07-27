from PySide6.QtCore import QObject, QTimer
from views.order_window import OrderWindow
from models.entities import Order, OrderItem


class OrderController(QObject):
    """Owns the order view + model, keeps the in-progress draft in memory, and runs a
    debounced dry-run check on every counter change. The draft is never persisted —
    only place_order writes to the database."""

    DEBOUNCE_MS = 150

    def __init__(self, order_model):
        super().__init__()

        self.model = order_model

        # draft: recipe_id -> (name, qty); 0 removes the item.
        self.draft: dict[int, tuple[str, int]] = {}
        self._last_order = None  # the Order most recently sent to place_order

        self.order_view = OrderWindow()
        self._refresh_recipes()

        self.order_view.quantity_changed.connect(self._on_quantity_changed)
        self.order_view.place_order_requested.connect(self._on_place_requested)

        self.model.order_placed_successfully.connect(self._on_order_placed)
        self.model.order_place_rejected.connect(
            lambda msg: self.order_view.show_warning("Cannot Place Order", msg))

        # single-shot debounce so rapid clicks don't re-validate on every tick
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(self.DEBOUNCE_MS)
        self._debounce.timeout.connect(self._run_dry_run)

    # ──────────────────────────────────────────────
    #  Draft handling
    # ──────────────────────────────────────────────
    def _on_quantity_changed(self, recipe_id: int, qty: int):
        if qty <= 0:
            self.draft.pop(recipe_id, None)
        else:
            name = self._recipe_name(recipe_id)
            self.draft[recipe_id] = (name, qty)

        self.order_view.update_summary(self.draft)
        self._debounce.start()

    def _build_order(self) -> Order:
        items = [
            OrderItem(recipe_id=rid, recipe_name=name, quantity=qty)
            for rid, (name, qty) in self.draft.items()
        ]
        return Order(items=items)

    def _run_dry_run(self):
        if not self.draft:
            self.order_view.show_shortages([], [])
            self.order_view.set_place_enabled(False)
            return

        result = self.model.validate_stock(self._build_order())
        self.order_view.update_summary(self.draft, result.subtotal)
        self.order_view.show_shortages(result.shortages, result.errors)
        self.order_view.set_place_enabled(result.ok)

    # ──────────────────────────────────────────────
    #  Place order
    # ──────────────────────────────────────────────
    def _on_place_requested(self):
        if not self.draft:
            return
        self._last_order = self._build_order()
        self.model.place_order(self._last_order)

    def _on_order_placed(self, order_id: int):
        order = self._last_order
        self.draft.clear()
        self.order_view.reset_counters()

        message = f"Order #{order_id} placed and stock deducted."
        if order:
            # subtotal/cost were written back onto the Order by place_order
            message += (
                f"\n\nSubtotal: {order.subtotal:.2f}"
                f"\nCost: {order.cost:.2f}"
                f"\nProfit: {order.subtotal - order.cost:.2f}"
            )
        self.order_view.show_info("Order Placed", message)

    # ──────────────────────────────────────────────
    #  Helpers
    # ──────────────────────────────────────────────
    def _names_by_id(self) -> dict:
        return {recipe["id"]: recipe["title"] for recipe in self.model.get_recipes_catalog()}

    def _recipe_name(self, recipe_id: int) -> str:
        return self._names_by_id().get(recipe_id, str(recipe_id))

    def _refresh_recipes(self):
        self.draft.clear()
        self.order_view.set_recipes(self.model.get_recipes_catalog())

    def refresh_current_order(self):
        """React to an external stock/recipe edit: rebuild the recipe list, reconcile
        the in-progress draft (drop recipes that no longer exist, refresh names), and
        re-run the dry-run so shortages/cost reflect the change. Preserves the draft."""
        catalog = self.model.get_recipes_catalog()
        name_by_id = self._names_by_id()
        self.draft = {
            rid: (name_by_id[rid], qty)
            for rid, (name, qty) in self.draft.items()
            if rid in name_by_id
        }
        self.order_view.set_recipes(catalog, self.draft)
        self._run_dry_run()

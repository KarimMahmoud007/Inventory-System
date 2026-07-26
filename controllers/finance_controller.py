from PySide6.QtCore import QObject
from views.finance_window import FinanceWindow


class FinanceController(QObject):
    """Owns the Finance page. Pure read side — the cost itself is written by
    FinanceModel inside OrderModel.place_order's transaction."""

    def __init__(self, finance_model):
        super().__init__()

        self.model = finance_model
        self.finance_view = FinanceWindow()
        self.finance_view.order_selected.connect(self._on_order_selected)

        self.refresh()

    def refresh(self):
        """Repopulate totals + order list from the (cached) finance reads. Wired in
        MainWindow to OrderModel.order_placed_successfully."""
        self.finance_view.set_totals(*self.model.get_totals())
        self.finance_view.set_orders(self.model.get_orders_summary())
        self.finance_view.clear_breakdown()

    def _on_order_selected(self, order_id: int):
        self.finance_view.show_breakdown(
            self.model.get_order_cost_breakdown(order_id)
        )

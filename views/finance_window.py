from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QWidget, QLabel, QFrame, QVBoxLayout, QHBoxLayout,
    QTableView, QHeaderView, QAbstractItemView, QMessageBox
)


class FinanceWindow(QWidget):
    """Finance page: revenue/cost/profit totals, one row per placed order, and the
    per-batch cost breakdown of the selected order.

    Read-only and DB-free — all data is pushed in by FinanceController.
    """

    order_selected = Signal(int)

    ORDER_HEADERS = ["ID", "Date", "Subtotal", "Cost", "Profit"]
    BREAKDOWN_HEADERS = ["Ingredient", "Batch", "Amount", "Unit", "Unit price", "Line cost"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Finance")
        self.setMinimumSize(800, 600)
        self._build_ui()

    # -- layout --------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        title = QLabel("Finance")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        # totals strip
        totals = QHBoxLayout()
        totals.setSpacing(12)
        for caption in ("Revenue", "Cost", "Profit"):
            card, value_label = self._totals_card(caption)
            setattr(self, f"{caption.lower()}_label", value_label)
            totals.addWidget(card)
        root.addLayout(totals)

        root.addWidget(self._section_label("Orders"))
        self.orders_table = self._make_table(self.ORDER_HEADERS)
        self.orders_table.selectionModel().selectionChanged.connect(self._on_selection)
        root.addWidget(self.orders_table, 2)

        root.addWidget(self._section_label("Cost breakdown"))
        self.breakdown_table = self._make_table(self.BREAKDOWN_HEADERS)
        root.addWidget(self.breakdown_table, 1)

    def _totals_card(self, caption: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("totalsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)

        caption_label = QLabel(caption)
        caption_label.setObjectName("totalsCaption")
        value_label = QLabel("0.00")
        value_label.setObjectName("totalsValue")

        layout.addWidget(caption_label)
        layout.addWidget(value_label)
        return card, value_label

    def _section_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _make_table(self, headers: list[str]) -> QTableView:
        model = QStandardItemModel(0, len(headers), self)
        model.setHorizontalHeaderLabels(headers)

        table = QTableView()
        table.setModel(model)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    def _fill(self, table: QTableView, headers: list[str], rows: list[list]):
        model = table.model()
        model.removeRows(0, model.rowCount())
        for row in rows:
            model.appendRow([QStandardItem(str(value)) for value in row])
        model.setHorizontalHeaderLabels(headers)


    # -- events --------------------------------------------------------
    def _on_selection(self):
        indexes = self.orders_table.selectionModel().selectedRows()
        if not indexes:
            return
        order_id = self.orders_table.model().item(indexes[0].row(), 0).text()
        self.order_selected.emit(int(order_id))

    # -- public API ----------------------------------------------------
    def set_totals(self, revenue: float, cost: float, profit: float):
        self.revenue_label.setText(f"{revenue:.2f}")
        self.cost_label.setText(f"{cost:.2f}")
        self.profit_label.setText(f"{profit:.2f}")

    def set_orders(self, rows):
        """rows: sequence of dicts with id/created_at/subtotal/cost/profit."""
        self._fill(self.orders_table, self.ORDER_HEADERS, [
            [r["id"], r["created_at"], f"{r['subtotal']:.2f}",
             f"{r['cost']:.2f}", f"{r['profit']:.2f}"]
            for r in rows
        ])

    def show_breakdown(self, rows):
        """rows: sequence of (stock_name, unit, batch_id, amount, unit_price, line_cost)."""
        self._fill(self.breakdown_table, self.BREAKDOWN_HEADERS, [
            [name, batch_id, f"{amount:g}", unit, f"{price:.2f}", f"{line:.2f}"]
            for name, unit, batch_id, amount, price, line in rows
        ])

    def clear_breakdown(self):
        self._fill(self.breakdown_table, self.BREAKDOWN_HEADERS, [])

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

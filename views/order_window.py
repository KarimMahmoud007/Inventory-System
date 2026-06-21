from PySide6.QtWidgets import (
    QWidget, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QHBoxLayout, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Signal


# ------------------------------------------------------------------ #
#  Single recipe row with a +/- counter
# ------------------------------------------------------------------ #
class RecipeOrderRow(QFrame):
    """One recipe line: name (+ price) and a [- qty +] counter.

    Emits quantity_changed(recipe_id, qty) on every change.
    """

    quantity_changed = Signal(int, int)

    def __init__(self, recipe_id: int, title: str, price=None, parent=None):
        super().__init__(parent)
        self.recipe_id = recipe_id
        self.title = title
        self.price = price
        self.qty = 0
        self.setObjectName("orderRow")
        self._build_ui()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        name = self.title
        if self.price is not None:
            name = f"{self.title}   —   {self.price}"
        self.name_label = QLabel(name)
        self.name_label.setObjectName("orderRowName")

        self.minus_btn = QPushButton("−")
        self.minus_btn.setObjectName("counterBtn")
        self.minus_btn.setFixedSize(30, 30)
        self.minus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.minus_btn.clicked.connect(self._decrement)

        self.qty_label = QLabel("0")
        self.qty_label.setObjectName("qtyLabel")
        self.qty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_label.setFixedWidth(36)

        self.plus_btn = QPushButton("+")
        self.plus_btn.setObjectName("counterBtn")
        self.plus_btn.setFixedSize(30, 30)
        self.plus_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.plus_btn.clicked.connect(self._increment)

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.minus_btn)
        layout.addWidget(self.qty_label)
        layout.addWidget(self.plus_btn)

    def _increment(self):
        self.qty += 1
        self._sync()

    def _decrement(self):
        if self.qty > 0:
            self.qty -= 1
            self._sync()

    def _sync(self):
        self.qty_label.setText(str(self.qty))
        self.quantity_changed.emit(self.recipe_id, self.qty)

    def reset(self):
        self.qty = 0
        self.qty_label.setText("0")

    def set_quantity(self, qty: int):
        """Set the counter silently (no quantity_changed emit) — used when the
        list is rebuilt and the in-progress draft is restored onto fresh rows."""
        self.qty = qty
        self.qty_label.setText(str(qty))


# ------------------------------------------------------------------ #
#  Order page
# ------------------------------------------------------------------ #
class OrderWindow(QWidget):
    """Recipe list with counters + running summary + Place Order button.

    No direct DB access — recipes are injected via set_recipes(), and validation
    feedback comes back through show_shortages()/set_place_enabled() from the
    controller.
    """

    quantity_changed = Signal(int, int)      # (recipe_id, qty)
    place_order_requested = Signal()

    def __init__(self, recipes: list[dict] | None = None, parent=None):
        super().__init__(parent)
        self.recipes = recipes or []
        self.rows: dict[int, RecipeOrderRow] = {}
        self.setWindowTitle("Place Order")
        self.setMinimumSize(800, 600)
        self._build_ui()
        self._apply_style()
        self._populate_rows()

    # -- layout --------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        title = QLabel("Place Order")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        root.addWidget(sep)

        body = QHBoxLayout()
        body.setSpacing(16)

        # left: scrollable recipe list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setObjectName("scrollArea")

        self.list_container = QWidget()
        self.list_container.setObjectName("listContainer")
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.list_layout.setSpacing(8)
        self.scroll.setWidget(self.list_container)
        body.addWidget(self.scroll, 2)

        # right: summary panel
        self.summary_panel = QFrame()
        self.summary_panel.setObjectName("summaryPanel")
        self.summary_panel.setFixedWidth(280)
        summary_layout = QVBoxLayout(self.summary_panel)
        summary_layout.setContentsMargins(14, 14, 14, 14)
        summary_layout.setSpacing(8)

        summary_title = QLabel("Order Summary")
        summary_title.setObjectName("summaryTitle")
        summary_layout.addWidget(summary_title)

        self.summary_label = QLabel("No items selected.")
        self.summary_label.setObjectName("summaryBody")
        self.summary_label.setWordWrap(True)
        self.summary_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        summary_layout.addWidget(self.summary_label)

        totals_sep = QFrame()
        totals_sep.setFrameShape(QFrame.Shape.HLine)
        totals_sep.setObjectName("separator")
        summary_layout.addWidget(totals_sep)

        self.totals_label = QLabel("")
        self.totals_label.setObjectName("totalsBody")
        self.totals_label.setTextFormat(Qt.TextFormat.RichText)
        self.totals_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        summary_layout.addWidget(self.totals_label)

        self.warning_label = QLabel("")
        self.warning_label.setObjectName("warningBody")
        self.warning_label.setWordWrap(True)
        self.warning_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        summary_layout.addWidget(self.warning_label)

        summary_layout.addStretch()

        self.place_btn = QPushButton("Place Order")
        self.place_btn.setObjectName("placeBtn")
        self.place_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.place_btn.setEnabled(False)
        self.place_btn.clicked.connect(self.place_order_requested.emit)
        summary_layout.addWidget(self.place_btn)

        body.addWidget(self.summary_panel)
        root.addLayout(body, 1)

    # -- populate ------------------------------------------------------
    def _populate_rows(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.rows.clear()

        if not self.recipes:
            empty = QLabel("No recipes available. Add recipes first.")
            empty.setObjectName("emptyLabel")
            self.list_layout.addWidget(empty)
            return

        for recipe in self.recipes:
            row = RecipeOrderRow(
                recipe_id=recipe["id"],
                title=recipe.get("title", ""),
                price=recipe.get("price"),
            )
            row.quantity_changed.connect(self.quantity_changed.emit)
            self.rows[recipe["id"]] = row
            self.list_layout.addWidget(row)

    # -- style ---------------------------------------------------------
    def _apply_style(self):
        self.setStyleSheet("""
            OrderWindow { background: #FFF8F0; }
            QLabel#pageTitle {
                font-family: 'Palatino Linotype', 'Book Antiqua', Georgia, serif;
                font-size: 32px; font-weight: bold; color: #8B4FCB;
            }
            QFrame#separator { color: #E8C4B0; max-height: 1px; }
            QScrollArea#scrollArea { background: transparent; }
            QWidget#listContainer { background: transparent; }
            QFrame#orderRow {
                background: #FFFDF7;
                border: 1px solid #E8C4B0;
                border-radius: 8px;
            }
            QLabel#orderRowName {
                font-family: Georgia; font-size: 13px; color: #2C1810;
            }
            QPushButton#counterBtn {
                font-size: 18px; font-weight: bold; color: #2C1810;
                background: #FAE8E0; border: 1px solid #D64545; border-radius: 6px;
            }
            QPushButton#counterBtn:hover { background: #D64545; color: #FFFDF7; }
            QLabel#qtyLabel {
                font-size: 14px; font-weight: bold; color: #2C1810;
            }
            QFrame#summaryPanel {
                background: #FFFDF7; border: 2px solid #D64545; border-radius: 10px;
            }
            QLabel#summaryTitle {
                font-family: Georgia; font-size: 16px; font-weight: bold; color: #8B4FCB;
            }
            QLabel#summaryBody { font-family: Georgia; font-size: 12px; color: #4A3728; }
            QLabel#totalsBody { font-family: Georgia; font-size: 13px; color: #2C1810; }
            QLabel#warningBody { font-family: Georgia; font-size: 12px; color: #C0392B; }
            QLabel#emptyLabel { font-family: Georgia; font-size: 13px; color: #8A7A6A; }
            QPushButton#placeBtn {
                font-family: Georgia; font-size: 14px; font-weight: bold; color: #FFFFFF;
                background: #27874E; border: none; border-radius: 6px; padding: 10px;
            }
            QPushButton#placeBtn:hover { background: #1E6B3E; }
            QPushButton#placeBtn:disabled { background: #B7B7B7; color: #EEEEEE; }
        """)

    # -- public API ----------------------------------------------------
    def set_recipes(self, recipes: list[dict], draft: dict | None = None):
        """Rebuild the recipe rows. If `draft` (recipe_id -> (name, qty)) is given,
        restore those quantities onto the fresh rows (silently); the controller then
        re-runs the dry-run to refresh totals/warnings/Place state."""
        self.recipes = recipes
        self._populate_rows()
        self.warning_label.setText("")
        if draft:
            for rid, (name, qty) in draft.items():
                row = self.rows.get(rid)
                if row is not None:
                    row.set_quantity(qty)
            self.update_summary(draft)
        else:
            self.update_summary({})
            self.set_place_enabled(False)

    def update_summary(self, draft: dict, subtotal: float = 0.0):
        """draft: recipe_id -> (name, qty). subtotal is the live revenue total.
        Cost/profit are not shown live — they appear in the post-placement popup."""
        if not draft:
            self.summary_label.setText("No items selected.")
            self.totals_label.setText("")
            return
        lines = [f"{name} × {qty}" for name, qty in draft.values()]
        total = sum(qty for _name, qty in draft.values())
        self.summary_label.setText("\n".join(lines) + f"\n\nTotal items: {total}")

        self.totals_label.setText(
            f"Subtotal:&nbsp;&nbsp;<b>{subtotal:.2f}</b>"
        )

    def show_shortages(self, shortages: list, errors: list):
        parts = []
        for err in errors:
            parts.append(f"⚠ {err}")
        for s in shortages:
            parts.append(
                f"⚠ {s.stock_name}: need {s.required} {s.unit}, have {s.available} {s.unit}"
            )
        self.warning_label.setText("\n".join(parts))

    def set_place_enabled(self, enabled: bool):
        self.place_btn.setEnabled(enabled)

    def reset_counters(self):
        for row in self.rows.values():
            row.reset()
        self.update_summary({})
        self.warning_label.setText("")
        self.set_place_enabled(False)

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)

    def show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)

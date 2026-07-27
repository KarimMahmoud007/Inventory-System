"""Self-check for form-field validation and write-failure reporting.

    python Database/seed.py && python test_form_validation.py

These are the two paths that used to fail silently: a bad numeric field raised
inside a Qt slot, and a failed write printed to a console nobody reads.
"""
from PySide6.QtWidgets import QApplication
from PySide6.QtSql import QSqlQuery

from Utilities.validate_data import parse_float
from views.batch_form_window import BatchFormWindow, BatchMode
from views.recipe_form_window import RecipeFormWindow, RecipeMode
from models.entities import StockBatch
from models.stock_batch_model import StockBatchModel


def capture_warnings(window):
    """Replace show_warning so a rejected submit is observable without a dialog."""
    seen = []
    window.show_warning = lambda title, message: seen.append(message)
    return seen


if __name__ == "__main__":
    app = QApplication([])

    # ── parse_float ────────────────────────────────────────────────────
    assert parse_float("2.5", "Price") == (2.5, None)
    assert parse_float("", "Price")[0] is None
    assert "Price" in parse_float("", "Price")[1]
    assert parse_float("abc", "Quantity")[0] is None
    assert parse_float(None, "Quantity")[0] is None

    # ── batch form: bad numeric fields warn instead of raising ─────────
    for price, qty, why in [("", "5", "empty price"),
                            ("3.0", "", "empty quantity"),
                            ("abc", "5", "non-numeric price"),
                            ("3.0", "xyz", "non-numeric quantity")]:
        form = BatchFormWindow(BatchMode.INSERT)
        warnings = capture_warnings(form)
        emitted = []
        form.batch_submitted.connect(emitted.append)
        form.entries["Price"].setText(price)
        form.entries["Quantity"].setText(qty)
        form.save()                     # must not raise
        assert warnings, f"{why} should warn"
        assert not emitted, f"{why} must not submit"

    # a valid batch still submits
    form = BatchFormWindow(BatchMode.INSERT)
    capture_warnings(form)
    emitted = []
    form.batch_submitted.connect(emitted.append)
    form.entries["Price"].setText("3.0")
    form.entries["Quantity"].setText("5")
    form.save()
    assert len(emitted) == 1 and isinstance(emitted[0], StockBatch), emitted
    assert emitted[0].price == 3.0 and emitted[0].quantity == 5.0

    # ── recipe form: name, price, and at least one ingredient ─────────
    def recipe_form():
        f = RecipeFormWindow(RecipeMode.INSERT, catalog=[(1, "Flour")], units=[(1, "kg")])
        return f, capture_warnings(f), []

    form, warnings, emitted = recipe_form()
    form.recipe_submitted.connect(lambda *a: emitted.append(a))
    form.recipe_name_edit.setText("   ")
    form.recipe_price_edit.setText("10")
    form.save = form._on_submit_recipe_clicked
    form.save()
    assert warnings and not emitted, "blank name must be rejected"

    form, warnings, emitted = recipe_form()
    form.recipe_submitted.connect(lambda *a: emitted.append(a))
    form.recipe_name_edit.setText("Bread")
    form.recipe_price_edit.setText("")
    form._on_submit_recipe_clicked()
    assert warnings and not emitted, "empty price must be rejected"

    form, warnings, emitted = recipe_form()
    form.recipe_submitted.connect(lambda *a: emitted.append(a))
    form.recipe_name_edit.setText("Bread")
    form.recipe_price_edit.setText("10")
    form._on_submit_recipe_clicked()
    assert warnings and not emitted, "zero ingredients must be rejected"

    form, warnings, emitted = recipe_form()
    form.recipe_submitted.connect(lambda *a: emitted.append(a))
    form.recipe_name_edit.setText("Bread")
    form.recipe_price_edit.setText("10")
    form._on_add_ingredient_clicked()
    form.ingredient_rows[0][2].setText("")        # blank quantity
    form._on_submit_recipe_clicked()
    assert warnings and not emitted, "blank ingredient quantity must be rejected"

    form, warnings, emitted = recipe_form()
    form.recipe_submitted.connect(lambda *a: emitted.append(a))
    form.recipe_name_edit.setText("Bread")
    form.recipe_price_edit.setText("10")
    form._on_add_ingredient_clicked()
    form.ingredient_rows[0][2].setText("500")
    form._on_submit_recipe_clicked()
    assert not warnings and len(emitted) == 1, (warnings, emitted)
    assert emitted[0][0] == "Bread" and emitted[0][1] == 10.0

    # ── a failed write reports instead of printing into the void ──────
    batches = StockBatchModel()
    failures = []
    batches.operation_failed.connect(failures.append)

    # FK violation: no stock row with this id, and foreign_keys is ON.
    q = QSqlQuery(batches.db)
    q.prepare("INSERT INTO stock_batch (stock_id, price, production_date, "
              "expiration_date, quantity) VALUES (99999, 1.0, '2026-01-01', '2027-01-01', 1)")
    assert not q.exec(), "FK enforcement is off — the check below proves nothing"

    batches.get_batch_table(1)
    batches.insert_batch(StockBatch(stock_id=99999, price=1.0,
                                    production_date="2026-01-01",
                                    expiration_date="2027-01-01", quantity=1.0))
    assert failures, "a failed insert must emit operation_failed"
    assert failures[0].strip(), "the failure message must not be empty"

    print("form validation + failure reporting OK")

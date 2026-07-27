from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget, QLineEdit, QFormLayout,
    QPushButton, QComboBox, QVBoxLayout, QHBoxLayout, QMessageBox
)
from enum import Enum
from models.entities import Recipe
from Utilities.validate_data import parse_float


class RecipeMode(Enum):
    INSERT = 1
    EDIT = 2


class RecipeFormWindow(QWidget):

    recipe_submitted = Signal(str, float, list)
    recipe_edit_submitted = Signal(int, str, float, list)

    def __init__(self, mode, catalog, units):
        super().__init__()
        self.mode = mode
        self.catalog = catalog
        self.units = units
        self._editing_id = None

        self.ingredient_rows: list[tuple[int | None, QComboBox, QLineEdit, QComboBox]] = []

        # Main layout
        self.main_layout = QVBoxLayout()

        # Ingredient form layout
        self.form_layout = QFormLayout()

        # Recipe Name (static row, always present)
        self.recipe_name_edit = QLineEdit()
        self.form_layout.addRow("Recipe Name", self.recipe_name_edit)

        # Recipe Price (static row, always present)
        self.recipe_price_edit = QLineEdit()
        self.form_layout.addRow("Recipe Price", self.recipe_price_edit)

        self.main_layout.addLayout(self.form_layout)

        # Bottom layout (for buttons)
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addStretch()

        # "+" button
        self.addBtn = QPushButton("+")
        self.addBtn.setFixedSize(40, 40)
        self.addBtn.clicked.connect(self._on_add_ingredient_clicked)

        self.submitBtn = QPushButton("Submit")
        self.submitBtn.clicked.connect(self._on_submit_recipe_clicked)

        self.bottom_layout.addWidget(self.addBtn)
        self.bottom_layout.addWidget(self.submitBtn)

        self.main_layout.addLayout(self.bottom_layout)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Add Recipe Window")

    def _on_add_ingredient_clicked(self):
        ingredient_combo = QComboBox()
        for item_id, item_name in self.catalog:
            ingredient_combo.addItem(item_name, item_id)

        quantity_edit = QLineEdit()

        unit_combo = QComboBox()
        for unit_id, unit_name in self.units:
            unit_combo.addItem(unit_name, unit_id)

        self.ingredient_rows.append((None, ingredient_combo, quantity_edit, unit_combo))

        self.form_layout.addRow("Ingredient", ingredient_combo)
        self.form_layout.addRow("Quantity", quantity_edit)
        self.form_layout.addRow("Unit", unit_combo)

    def _on_submit_recipe_clicked(self):
        name = self.recipe_name_edit.text().strip()
        if not name:
            self.show_warning("Validation Error", "Recipe name is required.")
            return

        price, error = parse_float(self.recipe_price_edit.text(), "Recipe price")
        if error:
            self.show_warning("Validation Error", error)
            return

        if not self.ingredient_rows:
            # A recipe with no ingredients cannot be ordered (the order flow fails
            # loudly on it) and cannot be reopened for editing. Reject it here.
            self.show_warning("Validation Error", "A recipe needs at least one ingredient.")
            return

        items = []
        for ir_id, ing_combo, qty_edit, unit_combo in self.ingredient_rows:
            amount, error = parse_float(qty_edit.text(), "Ingredient quantity")
            if error:
                self.show_warning("Validation Error", error)
                return
            items.append((
                ir_id,
                ing_combo.currentData(),
                amount,
                unit_combo.currentData()
            ))

        if self.mode == RecipeMode.EDIT:
            self.recipe_edit_submitted.emit(self._editing_id, name, price, items)
        else:
            self.recipe_submitted.emit(name, price, items)

    def load_data(self, recipe: Recipe):
        self._editing_id = recipe.id
        self.recipe_name_edit.setText(recipe.name)
        self.recipe_price_edit.setText(str(recipe.price))

        for ri in recipe.recipe_items:
            ingredient_combo = QComboBox()
            for item_id, item_name in self.catalog:
                ingredient_combo.addItem(item_name, item_id)
            for i in range(ingredient_combo.count()):
                if ingredient_combo.itemData(i) == ri.stock_id:
                    ingredient_combo.setCurrentIndex(i)
                    break

            quantity_edit = QLineEdit()
            quantity_edit.setText(str(ri.amount))

            unit_combo = QComboBox()
            for unit_id, unit_name in self.units:
                unit_combo.addItem(unit_name, unit_id)
            for i in range(unit_combo.count()):
                if unit_combo.itemData(i) == ri.unit_id:
                    unit_combo.setCurrentIndex(i)
                    break

            self.ingredient_rows.append((ri.id, ingredient_combo, quantity_edit, unit_combo))

            self.form_layout.addRow("Ingredient", ingredient_combo)
            self.form_layout.addRow("Quantity", quantity_edit)
            self.form_layout.addRow("Unit", unit_combo)

    def show_warning(self, title: str, message: str):
        QMessageBox.warning(self, title, message)
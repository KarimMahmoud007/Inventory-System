from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QWidget, QDateEdit, QLineEdit, QFormLayout,
    QPushButton, QComboBox, QVBoxLayout, QHBoxLayout
)
from enum import Enum

from Utilities.utilities import create_QtConnection, get_units, get_catalog


class AddRecipeWindow(QWidget):

    def __init__(self):
        super().__init__()

        self.entries = {}
        self.data = []

        # Main layout
        self.main_layout = QVBoxLayout()

        # Ingredient form layout
        self.form_layout = QFormLayout()

        # Recipe Name (static row, always present)
        self.recipe_name_edit = QLineEdit()
        self.form_layout.addRow("Recipe Name", self.recipe_name_edit)

        # Pre-populated combos for ingredient rows
        self.catalog = get_catalog()
        self.units = get_units()

        self.main_layout.addLayout(self.form_layout)

        # Bottom layout (for button)
        self.bottom_layout = QHBoxLayout()
        self.bottom_layout.addStretch()

        # "+" button
        self.addBtn = QPushButton("+")
        self.addBtn.setFixedSize(40, 40)
        self.addBtn.clicked.connect(self.add_ingredient)

        self.bottom_layout.addWidget(self.addBtn)

        self.main_layout.addLayout(self.bottom_layout)

        self.setLayout(self.main_layout)
        self.setWindowTitle("Add Recipe Window")

    def add_ingredient(self):
        ingredient_combo = QComboBox()
        for item in self.catalog:
            ingredient_combo.addItem(item)

        quantity_edit = QLineEdit()

        unit_combo = QComboBox()
        for unit_id, unit_name in self.units:
            unit_combo.addItem(unit_name, unit_id)

        self.form_layout.addRow("Ingredient", ingredient_combo)
        self.form_layout.addRow("Quantity", quantity_edit)
        self.form_layout.addRow("Unit", unit_combo)
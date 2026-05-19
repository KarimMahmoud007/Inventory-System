from PySide6.QtCore import QObject
from PySide6.QtWidgets import QMessageBox
from views.recipes_window import RecipesPage
from views.add_recipe_window import AddRecipeWindow
from models.recipes_model import RecipesModel
from models.entities import Recipe, RecipeItem
from Utilities.validate_data import validate_recipe_item


class RecipesController(QObject):

    def __init__(self):
        super().__init__()

        self.add_recipe_window = None

        self.model = RecipesModel()

        self.recipes_view = RecipesPage()
        self.recipes_view.add_recipe_requested.connect(self.open_add_recipe_window)

    def open_add_recipe_window(self):
        self.add_recipe_window = AddRecipeWindow()
        self.add_recipe_window.show()

        self.add_recipe_window.recipe_submitted.connect(self.handle_recipe_submitted)
        self.model.recipe_saved_successfully.connect(self.add_recipe_window.close)

    def handle_recipe_submitted(self, name, price, items):
        recipe_items = []
        for stock_id, amount, unit_id in items:
            if not validate_recipe_item(amount):
                QMessageBox.warning(self.add_recipe_window, "Validation Error", "Quantity must be greater than zero.")
                return
            recipe_items.append(RecipeItem(stock_id=stock_id, amount=amount, unit_id=unit_id))

        recipe = Recipe(name=name, price=price, recipe_items=recipe_items)
        self.model.save_recipe(recipe)

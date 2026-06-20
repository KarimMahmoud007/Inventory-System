from PySide6.QtCore import QObject, Signal
from views.recipes_window import RecipesPage
from views.add_recipe_window import AddRecipeWindow, RecipeMode
from models.recipes_model import RecipesModel
from models.entities import Recipe, RecipeItem
from Utilities.validate_data import validate_recipe_item


class RecipesController(QObject):

    # Relayed to OrderController so the Order page refreshes on any recipe change.
    data_changed = Signal()

    def __init__(self):
        super().__init__()

        self.add_recipe_window = None

        self.model = RecipesModel()

        self.recipes_view = RecipesPage()
        self.recipes_view.add_recipe_requested.connect(self.open_add_recipe_window)
        self.recipes_view.edit_recipe_requested.connect(self.open_edit_recipe_window)
        self.model.recipe_saved_successfully.connect(self._refresh_recipes)
        self.model.recipe_updated_successfully.connect(self._refresh_recipes)
        self.model.recipe_saved_successfully.connect(self.data_changed.emit)
        self.model.recipe_updated_successfully.connect(self.data_changed.emit)
        self._refresh_recipes()

    def open_add_recipe_window(self):
        self.add_recipe_window = AddRecipeWindow(RecipeMode.INSERT, catalog=self.model.catalog, units=self.model.units)
        self.add_recipe_window.show()

        self.add_recipe_window.recipe_submitted.connect(self.handle_recipe_submitted)
        self.model.recipe_saved_successfully.connect(self.add_recipe_window.close)

    def handle_recipe_submitted(self, name, price, items):
        recipe_items = []
        for id,stock_id, amount, unit_id in items:
            if not validate_recipe_item(amount):
                self.add_recipe_window.show_warning("Validation Error", "Quantity must be greater than zero.")
                return
            recipe_items.append(RecipeItem(id=None,stock_id=stock_id, amount=amount, unit_id=unit_id))

        recipe = Recipe(name=name, price=price, recipe_items=recipe_items)
        self.model.save_recipe(recipe)

    def open_edit_recipe_window(self, recipe_id: int):
        recipe = self.model.get_recipe(recipe_id)
        if recipe is None:
            return

        self.add_recipe_window = AddRecipeWindow(RecipeMode.EDIT, catalog=self.model.catalog, units=self.model.units)
        self.add_recipe_window.load_data(recipe)
        self.add_recipe_window.show()

        self.add_recipe_window.recipe_edit_submitted.connect(self.handle_recipe_edit_submitted)
        self.model.recipe_updated_successfully.connect(self.add_recipe_window.close)

    def handle_recipe_edit_submitted(self, recipe_id, name, price, items):
        recipe_items = []
        for ir_id, stock_id, amount, unit_id in items:
            if not validate_recipe_item(amount):
                self.add_recipe_window.show_warning("Validation Error", "Quantity must be greater than zero.")
                return
            recipe_items.append(RecipeItem(id=ir_id, stock_id=stock_id, amount=amount, unit_id=unit_id))

        recipe = Recipe(id=recipe_id, name=name, price=price, recipe_items=recipe_items)
        self.model.update_recipe(recipe)

    def _refresh_recipes(self):
        self.recipes_view.set_recipes(self.model.get_recipes_catalog())

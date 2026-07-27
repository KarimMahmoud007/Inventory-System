from PySide6.QtCore import QObject, Signal
from views.recipes_window import RecipesWindow
from views.recipe_form_window import RecipeFormWindow, RecipeMode
from models.entities import Recipe, RecipeItem
from Utilities.validate_data import validate_recipe_item


class RecipesController(QObject):

    # Relayed to OrderController so the Order page refreshes on any recipe change.
    data_changed = Signal()

    def __init__(self, recipes_model):
        super().__init__()

        self.recipe_form_window = None

        self.model = recipes_model

        self.recipes_view = RecipesWindow()

        self.recipes_view.add_recipe_requested.connect(self.open_add_recipe_form)
        self.recipes_view.edit_recipe_requested.connect(self.open_edit_recipe_form)

        self.model.recipe_inserted_successfully.connect(self._refresh_recipes)
        self.model.recipe_updated_successfully.connect(self._refresh_recipes)

        self.model.recipe_inserted_successfully.connect(self.data_changed.emit)
        self.model.recipe_updated_successfully.connect(self.data_changed.emit)

        self._refresh_recipes()

    def open_add_recipe_form(self):
        self.recipe_form_window = RecipeFormWindow(RecipeMode.INSERT, catalog=self.model.catalog, units=self.model.units)
        self.recipe_form_window.show()

        self.recipe_form_window.recipe_submitted.connect(self.handle_recipe_submitted)
        self.model.recipe_inserted_successfully.connect(self.recipe_form_window.close)

    def open_edit_recipe_form(self, recipe_id: int):
        recipe = self.model.get_recipe(recipe_id)
        if recipe is None:
            return

        self.recipe_form_window = RecipeFormWindow(RecipeMode.EDIT, catalog=self.model.catalog, units=self.model.units)
        self.recipe_form_window.load_data(recipe)
        self.recipe_form_window.show()

        self.recipe_form_window.recipe_edit_submitted.connect(self.handle_recipe_edit_submitted)
        self.model.recipe_updated_successfully.connect(self.recipe_form_window.close)

    def _build_recipe_items(self, items) -> list[RecipeItem] | None:
        recipe_items = []
        for ir_id, stock_id, amount, unit_id in items:
            if not validate_recipe_item(amount):
                self.recipe_form_window.show_warning("Validation Error", "Quantity must be greater than zero.")
                return None
            recipe_items.append(RecipeItem(id=ir_id, stock_id=stock_id, amount=amount, unit_id=unit_id))
        return recipe_items

    def handle_recipe_submitted(self, name, price, items):
        recipe_items = self._build_recipe_items(items)
        if recipe_items is None:
            return
        self.model.insert_recipe(Recipe(name=name, price=price, recipe_items=recipe_items))

    def handle_recipe_edit_submitted(self, recipe_id, name, price, items):
        recipe_items = self._build_recipe_items(items)
        if recipe_items is None:
            return
        self.model.update_recipe(Recipe(id=recipe_id, name=name, price=price, recipe_items=recipe_items))

    def _refresh_recipes(self):
        self.recipes_view.set_recipes(self.model.get_recipes_catalog())
from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlQuery
from models.base_model import BaseModel
from models.entities import Recipe, RecipeItem


class RecipeWriteFailed(Exception):
    """Raised inside a transaction block to abort and roll back a recipe write."""

    def __init__(self, action, detail):
        super().__init__(f"{action}: {detail}")


class RecipesModel(BaseModel):
    recipe_inserted_successfully = Signal()
    recipe_updated_successfully = Signal()

    def _invalidate_recipe_caches(self):
        """Everything a recipe write can stale: the stock catalog, the recipe
        cards, and the recipe→ingredient expansion behind the order dry-run."""
        self.invalidate_catalog()
        self.invalidate_recipes_catalog()
        self.invalidate_recipe_requirements()

    def insert_recipe(self, recipe: Recipe) -> bool:
        try:
            with self.transaction():
                query = QSqlQuery(self.db)
                query.prepare("INSERT INTO items (name, available, price) VALUES (?, 1, ?)")
                query.addBindValue(recipe.name)
                query.addBindValue(recipe.price)
                if not query.exec():
                    raise RecipeWriteFailed("insert recipe", query.lastError().text())

                item_id = query.lastInsertId()

                for ri in recipe.recipe_items:
                    query.prepare("INSERT INTO items_recipe (item_id, stock_id, amount, unit) VALUES (?, ?, ?, ?)")
                    query.addBindValue(item_id)
                    query.addBindValue(ri.stock_id)
                    query.addBindValue(ri.amount)
                    query.addBindValue(ri.unit_id)
                    if not query.exec():
                        raise RecipeWriteFailed("insert recipe item", query.lastError().text())
        except RecipeWriteFailed as exc:
            print("Failed to", exc)
            return False

        self._invalidate_recipe_caches()
        self.recipe_inserted_successfully.emit()
        print("Recipe saved successfully")
        return True

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        query = QSqlQuery(self.db)
        query.prepare("""
            SELECT i.id, i.name, i.price,
                   ir.id, ir.stock_id, ir.amount, ir.unit
            FROM items i
            LEFT JOIN items_recipe ir ON ir.item_id = i.id
            WHERE i.id = ?
            ORDER BY ir.id
        """)
        query.addBindValue(recipe_id)
        query.exec()

        # LEFT JOIN, so a recipe with no ingredients still comes back (with an
        # empty items list) instead of looking identical to "not found" — that
        # recipe is exactly the one the user needs to open in order to fix it.
        recipe = None
        items = []
        while query.next():
            if recipe is None:
                recipe = Recipe(
                    id=query.value(0),
                    name=query.value(1),
                    price=query.value(2),
                    recipe_items=[]
                )
            if query.isNull(3):
                continue   # the LEFT JOIN's null ingredient row (Qt maps SQL
                           # NULL to '', not None, so isNull is the only reliable test)
            items.append(RecipeItem(
                id=query.value(3),
                stock_id=query.value(4),
                amount=query.value(5),
                unit_id=query.value(6)
            ))
        if recipe is not None:
            recipe.recipe_items = items
        return recipe

    def update_recipe(self, recipe: Recipe) -> bool:
        try:
            with self.transaction():
                query = QSqlQuery(self.db)
                query.prepare("UPDATE items SET name=?, price=? WHERE id=?")
                query.addBindValue(recipe.name)
                query.addBindValue(recipe.price)
                query.addBindValue(recipe.id)
                if not query.exec():
                    raise RecipeWriteFailed("update recipe header", query.lastError().text())

                query.prepare("SELECT id FROM items_recipe WHERE item_id=?")
                query.addBindValue(recipe.id)
                query.exec()
                existing_ids = set()
                while query.next():
                    existing_ids.add(query.value(0))

                submitted_ids = set()
                for ri in recipe.recipe_items:
                    if ri.id is not None:
                        submitted_ids.add(ri.id)
                        query.prepare("UPDATE items_recipe SET stock_id=?, amount=?, unit=? WHERE id=?")
                        query.addBindValue(ri.stock_id)
                        query.addBindValue(ri.amount)
                        query.addBindValue(ri.unit_id)
                        query.addBindValue(ri.id)
                    else:
                        query.prepare("INSERT INTO items_recipe (item_id, stock_id, amount, unit) VALUES (?, ?, ?, ?)")
                        query.addBindValue(recipe.id)
                        query.addBindValue(ri.stock_id)
                        query.addBindValue(ri.amount)
                        query.addBindValue(ri.unit_id)
                    if not query.exec():
                        raise RecipeWriteFailed("upsert recipe item", query.lastError().text())

                for ir_id in existing_ids - submitted_ids:
                    query.prepare("DELETE FROM items_recipe WHERE id=?")
                    query.addBindValue(ir_id)
                    if not query.exec():
                        raise RecipeWriteFailed("delete removed recipe item",
                                                query.lastError().text())
        except RecipeWriteFailed as exc:
            print("Failed to", exc)
            return False

        self._invalidate_recipe_caches()
        self.recipe_updated_successfully.emit()
        print("Recipe updated successfully")
        return True

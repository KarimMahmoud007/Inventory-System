from PySide6.QtCore import Signal
from PySide6.QtSql import QSqlQuery
from models.base_model import BaseModel
from models.entities import Recipe, RecipeItem

class RecipesModel(BaseModel):
    recipe_saved_successfully = Signal()
    recipe_updated_successfully = Signal()

    def save_recipe(self, recipe):

        self.db.transaction()

        query = QSqlQuery(self.db)
        query.prepare("INSERT INTO items (name, available, price) VALUES (?, 1, ?)")
        query.addBindValue(recipe.name)
        query.addBindValue(recipe.price)
        if not query.exec():
            print("Failed to insert recipe:", query.lastError().text())
            self.db.rollback()
            return False

        item_id = query.lastInsertId()

        for ri in recipe.recipe_items:
            query.prepare("INSERT INTO items_recipe (item_id, stock_id, amount, unit) VALUES (?, ?, ?, ?)")
            query.addBindValue(item_id)
            query.addBindValue(ri.stock_id)
            query.addBindValue(ri.amount)
            query.addBindValue(ri.unit_id)
            if not query.exec():
                print("Failed to insert recipe item:", query.lastError().text())
                self.db.rollback()
                return False

        self.db.commit()
        self.invalidate_catalog()
        self.invalidate_recipes_catalog()
        self.invalidate_recipe_requirements()
        self.recipe_saved_successfully.emit()
        print("Recipe saved successfully")
        return True

    def get_recipe(self, recipe_id: int) -> Recipe | None:
        query = QSqlQuery(self.db)
        query.prepare("""
            SELECT i.id, i.name, i.price,
                   ir.id, ir.stock_id, ir.amount, ir.unit
            FROM items i
            JOIN items_recipe ir ON ir.item_id = i.id
            WHERE i.id = ?
            ORDER BY ir.id
        """)
        query.addBindValue(recipe_id)
        query.exec()

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
            items.append(RecipeItem(
                id=query.value(3),
                stock_id=query.value(4),
                amount=query.value(5),
                unit_id=query.value(6)
            ))
        if recipe is not None:
            recipe.recipe_items = items
        return recipe

    def update_recipe(self, recipe: Recipe):
        self.db.transaction()

        query = QSqlQuery(self.db)
        query.prepare("UPDATE items SET name=?, price=? WHERE id=?")
        query.addBindValue(recipe.name)
        query.addBindValue(recipe.price)
        query.addBindValue(recipe.id)
        if not query.exec():
            print("Failed to update recipe header:", query.lastError().text())
            self.db.rollback()
            return False

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
                print("Failed to upsert recipe item:", query.lastError().text())
                self.db.rollback()
                return False

        to_delete = existing_ids - submitted_ids
        for ir_id in to_delete:
            query.prepare("DELETE FROM items_recipe WHERE id=?")
            query.addBindValue(ir_id)
            if not query.exec():
                print("Failed to delete removed recipe item:", query.lastError().text())
                self.db.rollback()
                return False

        self.db.commit()
        self.invalidate_catalog()
        self.invalidate_recipes_catalog()
        self.invalidate_recipe_requirements()
        self.recipe_updated_successfully.emit()
        print("Recipe updated successfully")
        return True

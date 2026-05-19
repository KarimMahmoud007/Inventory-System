from PySide6.QtCore import QObject, Signal
from PySide6.QtSql import QSqlQuery
from Utilities.utilities import create_QtConnection, get_catalog as cached_catalog

class RecipesModel(QObject):
    recipe_saved_successfully = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_connect = create_QtConnection()

    def get_catalog(self):
        return cached_catalog()

    def save_recipe(self, recipe):
        db = self.db_connect
        db.transaction()

        query = QSqlQuery(db)
        query.prepare("INSERT INTO items (name, available, price) VALUES (?, 1, ?)")
        query.addBindValue(recipe.name)
        query.addBindValue(recipe.price)
        if not query.exec():
            print("Failed to insert recipe:", query.lastError().text())
            db.rollback()
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
                db.rollback()
                return False

        db.commit()
        cached_catalog.cache_clear()
        self.recipe_saved_successfully.emit()
        print("Recipe saved successfully")
        return True

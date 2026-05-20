from functools import lru_cache
from PySide6.QtCore import QObject
from PySide6.QtSql import QSqlQuery
from Utilities.utilities import create_QtConnection


class BaseModel(QObject):
    _shared_db = None

    def __init__(self, parent=None):
        super().__init__(parent)
        if BaseModel._shared_db is None:
            BaseModel._shared_db = create_QtConnection()
        self.db = BaseModel._shared_db

    @property
    def units(self):
        return BaseModel.get_units()

    @property
    def catalog(self):
        return BaseModel.get_catalog()

    @property
    def recipes_catalog(self):
        return BaseModel.get_recipes_catalog()

    @staticmethod
    @lru_cache
    def get_units():
        db = BaseModel._shared_db or create_QtConnection()
        query = QSqlQuery(db)
        query.exec("SELECT id, name FROM units ORDER BY id")
        units = []
        while query.next():
            units.append((query.value(0), query.value(1)))
        return units

    @staticmethod
    @lru_cache
    def get_catalog():
        db = BaseModel._shared_db or create_QtConnection()
        query = QSqlQuery(db)
        query.exec("SELECT id, name FROM stock")
        catalog = []
        while query.next():
            catalog.append((query.value(0), query.value(1)))
        return catalog

    @staticmethod
    @lru_cache
    def get_recipes_catalog():
        db = BaseModel._shared_db or create_QtConnection()
        query = QSqlQuery(db)
        query.exec("""
            SELECT i.id, i.name, i.price,
                   ir.amount, s.name, u.name
            FROM items i
            JOIN items_recipe ir ON ir.item_id = i.id
            JOIN stock s ON ir.stock_id = s.id
            JOIN units u ON ir.unit = u.id
            ORDER BY i.id
        """)
        recipes = []
        current_id = None
        current = None
        while query.next():
            rid = query.value(0)
            if rid != current_id:
                current_id = rid
                current = {
                    "id": rid,
                    "title": query.value(1),
                    "price": query.value(2),
                    "ingredients": []
                }
                recipes.append(current)
            current["ingredients"].append(
                f"{query.value(4)}: {query.value(3)} {query.value(5)}"
            )
        return recipes

    def invalidate_catalog(self):
        type(self).get_catalog.cache_clear()

    def invalidate_recipes_catalog(self):
        type(self).get_recipes_catalog.cache_clear()

    def invalidate_units(self):
        type(self).get_units.cache_clear()

from contextlib import contextmanager
from functools import lru_cache
from PySide6.QtCore import QObject
from PySide6.QtSql import QSqlQuery
from Utilities.utilities import create_qt_connection


def _db():
    """The shared connection, opening it if a cached static read runs before any
    model was constructed."""
    return BaseModel._shared_db or create_qt_connection()


class BaseModel(QObject):
    _shared_db = None

    def __init__(self, parent=None):
        super().__init__(parent)
        if BaseModel._shared_db is None:
            BaseModel._shared_db = create_qt_connection()
        self.db = BaseModel._shared_db

    @contextmanager
    def transaction(self):
        """Run a write inside a DB transaction: commit on success, roll back on
        any exception (which then propagates).

        Every model shares one connection, so anything called inside the block
        joins this transaction — that is how FinanceModel's ledger writes roll
        back with OrderModel.place_order. SQLite has no nested transactions, so
        blocks must not be nested.
        """
        self.db.transaction()
        try:
            yield
        except Exception:
            self.db.rollback()
            raise
        else:
            self.db.commit()

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
        query = QSqlQuery(_db())
        query.exec("SELECT id, name FROM units ORDER BY id")
        units = []
        while query.next():
            units.append((query.value(0), query.value(1)))
        return units

    @staticmethod
    @lru_cache
    def get_catalog():
        query = QSqlQuery(_db())
        query.exec("SELECT id, name FROM stock")
        catalog = []
        while query.next():
            catalog.append((query.value(0), query.value(1)))
        return catalog

    @staticmethod
    @lru_cache
    def get_recipes_catalog():
        query = QSqlQuery(_db())
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

    @staticmethod
    @lru_cache
    def get_available_stock(stock_id):
        """Total available quantity for a stock item, summed across its available
        batches, expressed in that item's own unit_of_measure.

        lru_cache-wrapped so repeated dry-run checks during interactive counter
        clicks don't re-hit the database. Invalidate via invalidate_available_stock()
        after any committed stock mutation (order deduction or batch edit)."""
        query = QSqlQuery(_db())
        query.prepare(
            "SELECT COALESCE(SUM(quantity), 0) FROM stock_batch "
            "WHERE stock_id = ? AND status = 'available'"
        )
        query.addBindValue(stock_id)
        query.exec()
        if query.next():
            return float(query.value(0))
        return 0.0

    @staticmethod
    @lru_cache
    def get_recipe_requirements(item_id):
        """Ingredient rows for a recipe (items) row, as a tuple of
        (stock_id, stock_name, amount, recipe_unit, stock_unit) tuples. An empty
        tuple means the recipe has no ingredient mapping — the caller must fail
        loudly rather than treat it as available.

        lru_cache-wrapped so repeated dry-runs during interactive counter clicks
        don't re-run the 4-table JOIN. Invalidate via invalidate_recipe_requirements()
        whenever items_recipe changes (recipe save/update) or a stock item's
        name/unit changes (affects stock_name / stock_unit, the latter feeding
        unit conversion during deduction)."""
        query = QSqlQuery(_db())
        query.prepare("""
            SELECT ir.stock_id, s.name, ir.amount, ru.name, su.name
            FROM items_recipe ir
            JOIN stock s  ON ir.stock_id = s.id
            JOIN units ru ON ir.unit = ru.id
            JOIN units su ON s.unit_of_measure = su.id
            WHERE ir.item_id = ?
        """)
        query.addBindValue(item_id)
        query.exec()
        rows = []
        while query.next():
            rows.append((
                query.value(0),          # stock_id
                query.value(1),          # stock name
                float(query.value(2)),   # amount
                query.value(3),          # recipe unit name
                query.value(4),          # stock unit name
            ))
        return tuple(rows)

    def invalidate_available_stock(self):
        BaseModel.get_available_stock.cache_clear()

    def invalidate_recipe_requirements(self):
        BaseModel.get_recipe_requirements.cache_clear()

    def invalidate_catalog(self):
        BaseModel.get_catalog.cache_clear()

    def invalidate_recipes_catalog(self):
        BaseModel.get_recipes_catalog.cache_clear()

    def invalidate_units(self):
        BaseModel.get_units.cache_clear()

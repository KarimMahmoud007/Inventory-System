from PySide6.QtSql import QSqlQuery
from Utilities.utilities import create_QtConnection, get_catalog as cached_catalog

class RecipesModel:
    def __init__(self, parent=None):
        self.db_connect = create_QtConnection()

    def get_catalog(self):
        return cached_catalog()

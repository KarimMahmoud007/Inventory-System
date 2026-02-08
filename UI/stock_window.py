from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableView
from PySide6.QtSql import QSqlTableModel,QSql
from PySide6.QtSql import QSqlDatabase
from Utilities.utilities import create_QtConnection
import os


class StockWindow(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        table = QTableView()
        layout.addWidget(table)

        model = QSqlTableModel(self)
        model.setTable("stock")
        model.select()

        table.setModel(model)
        table.setSortingEnabled(True)
        table.resizeColumnsToContents()

        db = create_QtConnection()



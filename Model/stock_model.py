from PySide6.QtSql import QSqlQuery
from Utilities.utilities import create_QtConnection
from PySide6.QtSql import QSqlTableModel



def post_data (data):
    db = create_QtConnection()
    query = QSqlQuery(db)

    query.prepare("INSERT INTO stock (name,unit_of_measure,price,production_date,expiration_date,quantity) "
                "VALUES (?,?,?,?,?,?)")

    query.addBindValue(data[0])          # name
    query.addBindValue(data[1])          # unit
    query.addBindValue(float(data[2]))   # price
    query.addBindValue(data[3])          # production_date
    query.addBindValue(data[4])          # expiration_date
    query.addBindValue(int(data[5]))     # quantity

    if query.exec():
        print("Record inserted successfully.")
    else:
        print(f"Error inserting record: {query.lastError().text()}")


def get_stock_model(parent):
    db = create_QtConnection()
    model = QSqlTableModel(parent, db)
    model.setTable("stock")
    model.select()
    return model
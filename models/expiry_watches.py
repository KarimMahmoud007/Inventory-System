"""The two expiry watches, as InventoryInspectors.

Monitoring is kept out of StockBatchModel: it shares nothing with batch CRUD or
the order-path deduction API except the database connection, and StockBatchModel
is the class the order engine calls.

Both queries look only at stock that could still be sold — an out_of_stock or
empty batch expiring is not news. Dates are 'YYYY-MM-DD' text, which sorts and
compares correctly against SQLite's date(). 'localtime' keeps "today" the same
day the inspector's scheduler means by it (date.today() is local, while a bare
date('now') is UTC).
"""
from models.inventory_inspector import InventoryInspector

_EXPIRY_SELECT = (
    "SELECT b.id, s.name, b.quantity, b.expiration_date "
    "FROM stock_batch b JOIN stock s ON s.id = b.stock_id "
    "WHERE b.status = 'available' AND b.quantity > 0 "
)
EXPIRED_SQL = _EXPIRY_SELECT + (
    "AND b.expiration_date < date('now', 'localtime') "
    "ORDER BY b.expiration_date ASC"
)
EXPIRING_SOON_SQL = _EXPIRY_SELECT + (
    "AND b.expiration_date >= date('now', 'localtime') "
    "AND b.expiration_date <= date('now', 'localtime', ?) "
    "ORDER BY b.expiration_date ASC"
)

EXPIRY_WARNING_WINDOW = "+7 day"   # how far ahead "expiring soon" looks
EXPIRY_CHECK_DAYS = 1              # both watches run once per calendar day


def create_expiry_inspectors() -> list[InventoryInspector]:
    """Build both watches. They check on construction, so a batch that expired
    while the app was closed is reported at the next startup.

    The caller MUST keep the returned list alive — a dropped inspector takes its
    QTimer with it and the watch stops silently.
    """
    return [
        InventoryInspector(
            "expired-batches", EXPIRED_SQL,
            period_days=EXPIRY_CHECK_DAYS,
        ),
        InventoryInspector(
            "expiring-soon-batches", EXPIRING_SOON_SQL,
            period_days=EXPIRY_CHECK_DAYS,
            params=(EXPIRY_WARNING_WINDOW,),
        ),
    ]

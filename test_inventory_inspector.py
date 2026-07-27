"""Self-check for InventoryInspector. Run after seeding:

    python Database/seed.py && python test_inventory_inspector.py

Schedule checks write last_run_on directly — no sleeping, no clock mocking.
"""
from datetime import date, timedelta

from PySide6.QtCore import QCoreApplication
from PySide6.QtSql import QSqlQuery

from models.inventory_inspector import InventoryInspector
from models.expiry_watches import create_expiry_inspectors

STOCK_SQL = "SELECT id, name FROM stock ORDER BY id"
EMPTY_SQL = "SELECT id FROM stock WHERE id < 0"
BAD_SQL = "SELECT nope FROM nowhere"

TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


def stamp(db, name, when):
    q = QSqlQuery(db)
    q.prepare("INSERT INTO inspector_state (name, last_run_on) VALUES (?, ?) "
              "ON CONFLICT(name) DO UPDATE SET last_run_on = excluded.last_run_on")
    q.addBindValue(name)
    q.addBindValue(when.isoformat())
    assert q.exec(), q.lastError().text()


def clear(db, name):
    q = QSqlQuery(db)
    q.prepare("DELETE FROM inspector_state WHERE name = ?")
    q.addBindValue(name)
    q.exec()


def fresh(db, name, sql, period_days=1, params=()):
    """A stopped inspector with no schedule history — check_due() by hand."""
    clear(db, name)
    insp = InventoryInspector(name, sql, period_days=period_days, params=params)
    insp.stop()
    return insp


if __name__ == "__main__":
    app = QCoreApplication([])

    # 1. manual mode: no timer, no schedule, run() still works
    manual = InventoryInspector("manual", STOCK_SQL)
    assert manual._timer is None
    assert manual.check_due() is False
    rows = manual.run()
    assert len(rows) == 5, rows
    assert rows[0] == (1, "Flour"), rows[0]

    db = manual.db

    # 2. no recorded run -> due immediately, at construction
    insp = fresh(db, "sched", STOCK_SQL)
    assert insp._last_run_on == TODAY, "construction should have caught up"

    fired = []
    insp.triggered.connect(lambda name, r: fired.append(r))

    # 3. already ran today -> not due
    assert insp.check_due() is False

    # 4. ran yesterday, daily -> due, and the stored date advances
    stamp(db, "sched", YESTERDAY)
    insp._last_run_on = YESTERDAY
    assert insp.check_due() is True
    assert insp._last_run_on == TODAY
    assert fired, "rows exist, so triggered should have fired"

    # 5. ran yesterday, weekly -> not due (multi-day periods actually wait)
    weekly = fresh(db, "weekly", STOCK_SQL, period_days=7)
    weekly._last_run_on = YESTERDAY
    assert weekly.check_due() is False

    # 6. last run in the future (clock moved backwards) -> due, not stuck
    weekly._last_run_on = TOMORROW
    assert weekly.check_due() is True

    # 7. survives restart: a fresh instance reads the persisted date
    restarted = InventoryInspector("sched", STOCK_SQL, period_days=1)
    restarted.stop()
    assert restarted._last_run_on == TODAY
    assert restarted.check_due() is False, "should not re-fire on the same day"

    # 8. empty result counts as a run: stamps, reports nothing
    quiet_fired = []
    quiet = fresh(db, "quiet", EMPTY_SQL)
    quiet.triggered.connect(lambda name, r: quiet_fired.append(r))
    stamp(db, "quiet", YESTERDAY)
    quiet._last_run_on = YESTERDAY
    assert quiet.check_due() is True
    assert quiet._last_run_on == TODAY
    assert quiet_fired == [], "empty result must stay silent"

    # 9. a failed query returns None, does NOT stamp, and prints only once
    broken = fresh(db, "broken", BAD_SQL)
    assert broken.run() is None, "failure must not look like an empty result"
    assert broken._last_run_on is None, "a broken query must stay due"
    assert broken.check_due() is False
    assert broken._last_run_on is None
    broken.run()   # silent: same error, already reported

    # ── the expiry watches on StockBatchModel ──────────────────────────────
    # Batches placed either side of every boundary: yesterday, today, the last
    # day of the window, the day after it, plus two that are expired but not
    # sellable (so they are nobody's problem).
    fixtures = [
        (9001, "-1 day", 5.0, "available"),      # expired
        (9002, "+0 day", 5.0, "available"),      # today -> soon, not expired
        (9003, "+7 day", 5.0, "available"),      # last day in the window
        (9004, "+8 day", 5.0, "available"),      # just outside
        (9005, "-1 day", 5.0, "out_of_stock"),   # expired but not sellable
        (9006, "-1 day", 0.0, "available"),      # expired but empty
    ]
    for bid, offset, qty, status in fixtures:
        q = QSqlQuery(db)
        q.prepare("INSERT INTO stock_batch (id, stock_id, price, production_date, "
                  "expiration_date, quantity, status) VALUES "
                  "(?, 1, 1.0, date('now','localtime','-1 year'), "
                  "date('now', 'localtime', ?), ?, ?)")
        for v in (bid, offset, qty, status):
            q.addBindValue(v)
        assert q.exec(), q.lastError().text()

    expired_watch, soon_watch = create_expiry_inspectors()
    expired_watch.stop()
    soon_watch.stop()

    expired_ids = {r[0] for r in expired_watch.run()}
    soon_ids = {r[0] for r in soon_watch.run()}

    assert 9001 in expired_ids, expired_ids
    assert {9002, 9003, 9004, 9005, 9006} & expired_ids == set(), expired_ids
    assert {9002, 9003} <= soon_ids, soon_ids
    assert {9001, 9004} & soon_ids == set(), soon_ids
    assert not (expired_ids & soon_ids), "a batch must not be in both"

    QSqlQuery(db).exec("DELETE FROM stock_batch WHERE id >= 9001")
    for name in ("manual", "sched", "weekly", "quiet", "broken",
                 "expired-batches", "expiring-soon-batches"):
        clear(db, name)

    print("inventory inspector OK")

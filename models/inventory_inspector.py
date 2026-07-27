from datetime import date

from PySide6.QtCore import QTimer, Signal
from PySide6.QtSql import QSqlQuery

from models.base_model import BaseModel


class InventoryInspector(BaseModel):
    """A daily (or manual) watch over the inventory.

    One instance = one watch. It holds a SQL query and, optionally, a period in
    days. With a period it re-runs itself on a calendar schedule; without one it
    does nothing until someone calls run() by hand.

        # once per calendar day, self-scheduling
        low_stock = InventoryInspector("low-stock", SQL, period_days=1)

        # manual only
        expiring = InventoryInspector("expiring", SQL)
        rows = expiring.run()

    The schedule is calendar days, not elapsed seconds: the last-run *date* is
    persisted in `inspector_state`, so a daily watch fires once per day no matter
    what time the app happens to be opened — no drift across the day and no
    skipped days. On construction it checks immediately (catching up on anything
    missed while closed), then re-checks every `check_seconds` in case the app is
    left open across midnight. A tick is a date subtraction against in-memory
    state — no query.

    Results are reported on `triggered(name, rows)`, and only when the query
    returned something. Keep a reference to the instance: drop it and the QTimer
    is garbage-collected and the watch silently stops.
    """

    triggered = Signal(str, list)

    def __init__(self, name, sql, period_days=None, params=(),
                 check_seconds=10, parent=None):
        super().__init__(parent)
        self.name = name
        self.sql = sql
        self.params = tuple(params)
        self.period_days = period_days
        self._last_run_on = None   # date, mirrored from inspector_state
        self._last_error = None    # dedupes the error print of a broken query
        self._timer = None

        if period_days is None:
            return

        self._ensure_state_table()
        self._last_run_on = self._load_last_run_on()
        self.check_due()                       # catch up on what was missed
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.check_due)
        self._timer.start(int(check_seconds * 1000))

    # ──────────────────────────────────────────────
    #  The trigger
    # ──────────────────────────────────────────────
    def run(self) -> list[tuple] | None:
        """Execute the query and return its rows, or None if the query failed.

        None and [] mean opposite things — broken vs. nothing to report — so they
        do not share a return value. Callable at any time; does no stamping, so
        poking a scheduled inspector by hand never disturbs its schedule.

        A failing query prints once rather than on every poll, and prints again
        if the error changes."""
        query = QSqlQuery(self.db)
        query.prepare(self.sql)
        for value in self.params:
            query.addBindValue(value)

        if not query.exec():
            error = query.lastError().text()
            if error != self._last_error:
                self._last_error = error
                print(f"[inspector:{self.name}] query failed:", error)
            return None

        self._last_error = None
        columns = query.record().count()
        rows = []
        while query.next():
            rows.append(tuple(query.value(i) for i in range(columns)))
        return rows

    def check_due(self) -> bool:
        """Run if the period has elapsed since the last run. Returns whether it ran.

        A failed query does NOT stamp, so a broken watch retries on the next tick
        instead of going quiet for a day. On success the stamp is written before
        reporting, so a crash mid-report can at worst repeat a run, never skip
        one. An empty result still counts as a run — it just reports nothing."""
        if self.period_days is None or not self._is_due():
            return False

        today = date.today()
        rows = self.run()
        if rows is None:
            return False

        self._stamp(today)
        if rows:
            # ponytail: console is the sink until notifications exist — then the
            # consumer connects to triggered and these prints go away.
            print(f"[inspector:{self.name}] {len(rows)} row(s)")
            for row in rows:
                print("   ", row)
            self.triggered.emit(self.name, rows)
        return True

    def start(self):
        if self._timer:
            self._timer.start()

    def stop(self):
        if self._timer:
            self._timer.stop()

    # ──────────────────────────────────────────────
    #  Persisted schedule
    # ──────────────────────────────────────────────
    def _is_due(self):
        """Never run, period elapsed, or the system clock moved backwards (a
        last run in the future would otherwise park the watch until real time
        caught up)."""
        if self._last_run_on is None:
            return True
        elapsed = (date.today() - self._last_run_on).days
        return elapsed < 0 or elapsed >= self.period_days

    def _ensure_state_table(self):
        """Created on demand so an existing Inventory.db needs no migration.

        Early versions stored epoch seconds in `last_run_at`; CREATE TABLE IF NOT
        EXISTS won't reshape those, so they are dropped. The table holds nothing
        but "when did this last run" — discarding it costs one extra run."""
        columns = QSqlQuery(self.db)
        columns.exec("PRAGMA table_info(inspector_state)")
        names = []
        while columns.next():
            names.append(columns.value(1))
        if names and "last_run_on" not in names:
            QSqlQuery(self.db).exec("DROP TABLE inspector_state")

        QSqlQuery(self.db).exec(
            "CREATE TABLE IF NOT EXISTS inspector_state ("
            "    name TEXT PRIMARY KEY,"
            "    last_run_on TEXT NOT NULL"
            ")"
        )

    def _load_last_run_on(self):
        query = QSqlQuery(self.db)
        query.prepare("SELECT last_run_on FROM inspector_state WHERE name = ?")
        query.addBindValue(self.name)
        query.exec()
        if query.next():
            return date.fromisoformat(query.value(0))
        return None

    def _stamp(self, when):
        self._last_run_on = when
        query = QSqlQuery(self.db)
        query.prepare(
            "INSERT INTO inspector_state (name, last_run_on) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET last_run_on = excluded.last_run_on"
        )
        query.addBindValue(self.name)
        query.addBindValue(when.isoformat())
        if not query.exec():
            print(f"[inspector:{self.name}] stamp failed:", query.lastError().text())

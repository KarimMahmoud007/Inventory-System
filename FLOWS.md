# OPERATION FLOWS

How each operation runs end-to-end. Markers: **[DB]** a database query,
**[cache]** an lru_cache read or clear, **[signal]** a Qt signal,
**[lifetime]** an object being created or destroyed.

See `brief.txt` for structure and patterns; this file is the runtime trace.

---

## 1. App startup & infrastructure

- `MainWindow.__init__` creates the 5 models once (`StockModel`,
  `StockBatchModel`, `RecipesModel`, `FinanceModel`, `OrderModel`) and injects them
  into the 4 controllers (dependency injection). `FinanceModel` goes into both
  `OrderModel` (which hands it the deducted batches to cost) and `FinanceController`. The single `StockBatchModel` goes into both
  `OrderModel` and the `BatchController` that `StockController` creates and owns
  (`StockController` receives the injected instance and forwards it to the child).
- It wires each controller's `data_changed` **[signal]** to
  `OrderController.refresh_current_order` and
  `OrderModel.order_placed_successfully` → `FinanceController.refresh`, then builds
  the sidebar and a
  `QStackedWidget` holding one widget per page (`page_map`).
- It then builds the two expiry watches via
  `expiry_watches.create_expiry_inspectors()` and holds the list — a dropped
  inspector takes its `QTimer` with it. Both check on construction (§10).
- **[lifetime]** Models, controllers, page widgets and inspectors are created at
  startup and live for the whole app. Batch windows and all form windows are the
  exception (created/destroyed on demand — see below).
- **DB connection:** the first `BaseModel()` calls `create_qt_connection()`, which
  opens one named `QSqlDatabase` ("inventory_connection") and runs
  `PRAGMA foreign_keys = ON`. It **raises** if the open fails — it does not
  `exit()`. `BaseModel._shared_db` is a class attribute, so every model reuses
  that one connection.
- **Shutdown:** `MainWindow.closeEvent` stops every inspector and calls
  `close_qt_connection()`.
- **Caches** (`BaseModel`, all `@staticmethod @lru_cache`): `get_units`,
  `get_catalog` (stock id+name), `get_recipes_catalog` (recipe cards),
  `get_available_stock(stock_id)`, `get_recipe_requirements(item_id)`. Each fills
  on first read and is cleared by an `invalidate_*` call after the matching
  mutation (see §9).

## 2. Navigation

- Sidebar button → `MainWindow.show_page(name)` →
  `QStackedWidget.setCurrentWidget`. No DB, no cache, no new objects.

## 3. Stock item — add / edit / delete

**Add**
1. `StockWindow.add_item_requested` **[signal]** → `open_add_item_window`
   **[lifetime]** creates `StockItemFormWindow`, reading `stock_model.units`
   **[cache]** to fill the unit combo.
2. Form submit → `save()` checks the raw fields first (nothing to parse here —
   Name is text, Unit is a combo) → `handle_add_item` validates
   (`validate_stock_item`) → `insert_stock_item`.
3. `_stock_name_exists` **[DB]** case-insensitive check. If taken →
   `item_insert_rejected` **[signal]** → form warning, stop.
4. Else insert via `QSqlRelationalTableModel.submitAll` **[DB]** → `sync_model()`
   clears `catalog` + `recipe_requirements` **[cache]** → `item_inserted_successfully`
   **[signal]** closes the form, and `data_changed` refreshes the Order page.

**Edit**
1. `edit_item_requested` → `get_stock_item` **[DB]** → `StockItemFormWindow`
   (UPDATE mode) **[lifetime]**, prefilled.
2. Submit → `handle_edit_item` validate → `update_stock_item` **[DB]** →
   `sync_model` **[cache]** → `item_updated_successfully` **[signal]** closes form
   + `data_changed`.

**Delete**
1. `delete_item_requested` → `delete_stock_item` runs DELETE **[DB]**.
2. FK RESTRICT (item still has batches) → `_is_fk_violation` → `item_delete_rejected`
   **[signal]** → warning. RESTRICT is enforced by an internal trigger, so the
   native code is **1811**, not the 787 a direct FK violation gives.
3. Else `sync_model` **[cache]** + `item_deleted_successfully` **[signal]** +
   `data_changed`.

## 4. Stock batch — view / add / edit / delete / toggle

Level 2 lives on the child `BatchController` (owned by `StockController`, sharing
its stack + item_view). All batch work below runs there, via the shared
`batch_model`.

**View batches (level 2)**
1. `view_batches_requested(stock_id)` → `StockController.open_batch_window`, which
   looks up `get_stock_name` **[DB]** and delegates to
   `BatchController.open_batch_window(stock_id, stock_name)`.
2. **[lifetime]** any previous `batch_view` is removed from the stack and
   `deleteLater`'d.
3. `get_batch_table(stock_id)` builds a `QSqlTableModel` filtered to that stock
   **[DB]** (header uses the passed-in `stock_name`).
4. New `StockBatchWindow` is created, added to the (shared) stack, and shown.
   **Back** → `BatchController.close_batch_window` returns to `item_view` and
   disposes it **[lifetime]**.

**Add / Edit / Delete / Toggle** (all on `BatchController`, via the shared `batch_model`)
- Add: form `save()` → `_field_error()` parses Price/Quantity and warns on bad
  input **before** the `StockBatch` is built → `handle_add_batch` validates →
  `insert_batch` **[DB]** (writes by `fieldIndex`, and takes `stock_id` from
  `BatchController.stock_id`, not from the view).
- Edit: `get_batch` **[DB]** → form → `update_batch` **[DB]**.
- Delete: `delete_batch` **[DB]**. Toggle: `toggle_status` **[DB]**.
- Every mutator calls `invalidate_available_stock()` **[cache]**, refreshes the
  table model, and emits its `batch_*` **[signal]**, which closes the form and
  fires `BatchController.data_changed`.
- **Failure path:** any failed write emits `operation_failed(str)` **[signal]** →
  `BatchController._on_operation_failed` → warning on the open form, or the batch
  page if no form is open. Previously these only reached the console.
- These `batch_*` relays are wired **once** in `BatchController.__init__` (not per
  window) because the batch model is persistent/shared. `StockController` relays
  `BatchController.data_changed` up through its own `data_changed` → Order refresh.

## 5. Recipe — add / edit

**Add**
1. `add_recipe_requested` → `open_add_recipe_form` **[lifetime]** creates
   `RecipeFormWindow`, reading `model.catalog` + `model.units` **[cache]**.
2. Submit → the form checks name, price, at-least-one-ingredient and every
   ingredient quantity (`parse_float`), warning and stopping on the first
   problem → `recipe_submitted` → `handle_recipe_submitted` validates each amount
   (`validate_recipe_item`), builds `Recipe` → `insert_recipe`.
3. `with self.transaction():` → INSERT into `items` then `items_recipe` rows **[DB]** →
   commit → clears `catalog` + `recipes_catalog` + `recipe_requirements`
   **[cache]** → `recipe_inserted_successfully` **[signal]** refreshes the cards,
   closes the form, and fires `data_changed`.

**Edit**
1. `edit_recipe_requested` → `get_recipe` **[DB]**, a **LEFT JOIN** so a recipe
   with no ingredients still loads (empty items list) instead of looking like
   "not found" — that is exactly the recipe the user opened in order to fix it →
   `RecipeFormWindow` (EDIT mode) **[lifetime]**, prefilled.
2. `recipe_edit_submitted` → `handle_recipe_edit_submitted` → `update_recipe`.
3. Transactional **[DB]**: UPDATE the `items` header, then UPSERT `items_recipe`
   (UPDATE existing ids, INSERT new ones, DELETE removed) → commit → same cache
   clears + `recipe_updated_successfully` **[signal]**.

## 6. Order — counter change → debounced dry-run

1. `RecipeOrderRow` +/- → `quantity_changed(recipe_id, qty)` **[signal]** →
   `_on_quantity_changed` updates the in-memory `draft` (qty 0 removes), updates
   the summary (subtotal text only), and (re)starts a 150ms `QTimer`.
   **[lifetime]** the draft is memory-only — no DB, nothing persisted.
2. On timeout → `_run_dry_run` → `validate_stock(order)`:
   - `_required_by_stock` → `get_recipe_requirements` **[cache]** per recipe →
     `convert()` each ingredient into the stock unit → sums required per stock item.
   - Compares each total against `get_available_stock(stock_id)` **[cache]**.
   - Returns shortages + fail-loud errors + `subtotal`. **No real stock touched.**
3. View shows subtotal + any shortages/errors and enables/disables Place Order.

## 7. Order — place order (transactional)

1. `place_order_requested` **[signal]** → `_on_place_requested` builds the `Order`
   → `place_order`.
2. `_required_by_stock` + `_order_subtotal` run **once**, then
   `_check_availability` re-validates. On failure → `order_place_rejected`
   **[signal]** → warning, stop. This re-validation is not redundant with §6 —
   that dry-run is debounced 150 ms and can be stale when Place is clicked.
3. `with self.transaction():` → `_persist_order` INSERTs `orders` with the
   subtotal (**cost stays 0** — the schema default) + one `order_items` row each
   **[DB]**.
4. `_deduct_for_order(required)` — the **already-validated** requirements dict,
   not a recomputation. For each stock item, `get_available_batches` **[DB]**
   oldest-first, then `deduct_batch(batch_id, take)` **[DB]** subtracts the
   consumed amount, clamps a depleted batch to 0 and flips it to `out_of_stock`.
   It shares the connection, so it joins this transaction. Returns a
   `list[BatchConsumption]` — no money math here.
5. `FinanceModel.apply_order_cost(order_id, consumptions)`: INSERT one
   `order_batch_consumption` row per consumed batch **[DB]**, then
   `UPDATE orders SET cost = ?` **[DB]** with `Σ amount × unit_price`. Same shared
   connection → same transaction. Returns the cost, or `None` → abort.
6. Block exits cleanly → commit → `invalidate_available_stock()` +
   `finance.invalidate_finance()` **[cache]** → `order_placed_successfully`
   **[signal]**. **Any failure** raises `OrderFailed`, which the context manager
   turns into `db.rollback()` and the caller emits as `order_place_rejected` —
   one exit path instead of the five hand-rolled rollback blocks this used to
   have (no partial deduction, no order left at cost 0).
7. `_on_order_placed`: profit = subtotal − cost (read off the `Order` dataclass that
   `place_order` wrote back), clears the draft, resets the counters, shows the
   Subtotal/Cost/Profit popup. (Cost/profit exist only after placement — the dry-run
   shows subtotal only.)

## 8. Cross-page live refresh

- Any stock or recipe mutation emits `data_changed` **[signal]**; MainWindow
  relays it to `OrderController.refresh_current_order`.
- That rebuilds the recipe list from `get_recipes_catalog` **[cache]**,
  reconciles the in-progress draft (drops recipes that no longer exist, refreshes
  names, keeps quantities), and re-runs the dry-run.
- `RecipeOrderRow.set_quantity` restores counters **silently** (no
  `quantity_changed` emit) to avoid a feedback loop.

## 9. Finance page

- **[lifetime]** `FinanceController` + `FinanceWindow` are created once at startup
  (like the other pages) and `refresh()` runs in the constructor.
- `refresh()` reads `get_totals()` + `get_orders_summary()` **[cache]** and pushes
  them into the view (totals cards + orders table); the breakdown panel is cleared.
- Selecting an order row → `order_selected(id)` **[signal]** →
  `get_order_cost_breakdown(id)` **[cache]** → `show_breakdown` fills the lower table
  (one row per batch consumed: ingredient, batch, amount, unit, unit price, line cost).
- After a placement, `OrderModel.order_placed_successfully` **[signal]** →
  `FinanceController.refresh` — and because `place_order` cleared the finance caches
  post-commit, that refresh re-queries **[DB]** and re-fills them.

## 10. Inventory inspector (periodic watch)

Whoever constructs one must keep the reference alive, or the `QTimer` is
collected and the watch stops silently.

**Expiry watches** — `expiry_watches.create_expiry_inspectors()` builds two and
`MainWindow` holds them, so they come up with the app:
- `"expired-batches"` — batches already past `expiration_date` **[DB]**.
- `"expiring-soon-batches"` — batches due within `EXPIRY_WARNING_WINDOW`
  (`+7 day`, bound as a parameter) **[DB]**.
Both are restricted to `status = 'available' AND quantity > 0`, run once per
calendar day, and report on startup if the day rolled over while the app was
closed. Both compare against `date('now', 'localtime')`, matching the scheduler's
local `date.today()`. Today's date counts as "soon", never "expired", so the two
sets never overlap.

**Manual mode** (`period_days=None`)
- No timer, no state row, nothing at construction. `run()` executes the injected
  SQL **[DB]** and returns `list[tuple]`. That's the whole object.

**Scheduled mode** (`period_days` given)
1. `__init__` ensures `inspector_state` **[DB]** (dropping an older
   `last_run_at REAL` table if it finds one), loads `last_run_on` **[DB]** into
   memory, then calls `check_due()` straight away — so a restart fires anything
   that came due while the app was closed.
2. `check_due` compares `date.today()` against the in-memory `last_run_on` — **no
   query**. Not enough days elapsed → returns `False`, done. A last run in the
   *future* (clock moved backwards) counts as due.
3. Due → `run()` **[DB]** first. Failure (`None`) → returns `False` **without
   stamping**, so the next tick retries instead of the watch going quiet for a
   day. The error prints once, not every tick.
4. Success → stamp the date **[DB]** (and in memory), then report: rows found →
   prints them and emits `triggered(name, rows)` **[signal]**; empty → silent,
   but it still counted as a run and the stamp still moved.
5. **[lifetime]** a `QTimer` then re-calls `check_due` every `check_seconds`
   (default 10) — cheap, since a tick that isn't due touches no DB. The period is
   never a timer duration, only a date comparison, so the app never has to stay
   open across a day boundary.
- Manual `run()` on a scheduled inspector does **not** stamp, so poking it by
  hand never shifts its schedule.

## 11. Caches & invalidation

| Cache (`BaseModel`) | Filled by | Cleared by |
|---|---|---|
| `get_units` | first read (units combo) | `invalidate_units` (not currently called — units are seed data) |
| `get_catalog` | stock id+name reads | `sync_model` on stock insert/update/delete |
| `get_recipes_catalog` | recipe cards / order rows | `insert_recipe`, `update_recipe` |
| `get_available_stock(stock_id)` | dry-run + place_order | every `StockBatchModel` mutator; `place_order` post-commit |
| `get_recipe_requirements(item_id)` | dry-run + deduction | `insert_recipe`, `update_recipe`, and `sync_model` (stock name/unit affects it) |
| `FinanceModel.get_orders_summary` | Finance page refresh | `invalidate_finance()` — `place_order` post-commit |
| `FinanceModel.get_totals` | Finance page refresh | same |
| `FinanceModel.get_order_cost_breakdown(order_id)` | Finance row selection | same |

All stock writes go through `StockBatchModel` or `OrderModel`, so the
available-stock cache is the single serialized mutation path and cannot go stale.

# OPERATION FLOWS

How each operation runs end-to-end. Markers: **[DB]** a database query,
**[cache]** an lru_cache read or clear, **[signal]** a Qt signal,
**[lifetime]** an object being created or destroyed.

See `brief.txt` for structure and patterns; this file is the runtime trace.

---

## 1. App startup & infrastructure

- `MainWindow.__init__` creates the 4 models once (`StockModel`,
  `StockBatchModel`, `RecipesModel`, `OrderModel`) and injects them into the 3
  controllers (dependency injection). The single `StockBatchModel` goes into both
  `OrderModel` and the `BatchController` that `StockController` creates and owns
  (`StockController` receives the injected instance and forwards it to the child).
- It wires each controller's `data_changed` **[signal]** to
  `OrderController.refresh_current_order`, then builds the sidebar and a
  `QStackedWidget` holding one widget per page (`page_map`).
- **[lifetime]** Models, controllers, and page widgets are created at startup and
  live for the whole app. Batch windows and all form windows are the exception
  (created/destroyed on demand — see below).
- **DB connection:** the first `BaseModel()` calls `create_QtConnection()`, which
  opens one named `QSqlDatabase` ("inventory_connection") and runs
  `PRAGMA foreign_keys = ON`. `BaseModel._shared_db` is a class attribute, so
  every model reuses that one connection.
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
   **[lifetime]** creates `AddStockItemWindow`, reading `stock_model.units`
   **[cache]** to fill the unit combo.
2. Form submit → `handle_add_item` validates (`validate_stock_item`) →
   `insert_stock_item`.
3. `_stock_name_exists` **[DB]** case-insensitive check. If taken →
   `item_insert_rejected` **[signal]** → form warning, stop.
4. Else insert via `QSqlRelationalTableModel.submitAll` **[DB]** → `sync_model()`
   clears `catalog` + `recipe_requirements` **[cache]** → `item_inserted_successfully`
   **[signal]** closes the form, and `data_changed` refreshes the Order page.

**Edit**
1. `edit_item_requested` → `get_stock_item` **[DB]** → `AddStockItemWindow`
   (UPDATE mode) **[lifetime]**, prefilled.
2. Submit → `handle_edit_item` validate → `update_stock_item` **[DB]** →
   `sync_model` **[cache]** → `item_updated_successfully` **[signal]** closes form
   + `data_changed`.

**Delete**
1. `delete_item_requested` → `delete_stock_item` runs DELETE **[DB]**.
2. FK RESTRICT (item still has batches, native code 787/19) →
   `item_delete_rejected` **[signal]** → warning.
3. Else `sync_model` **[cache]** + `item_deleted_successfully` **[signal]** +
   `data_changed`.

## 4. Stock batch — view / add / edit / delete / toggle

Level 2 lives on the child `BatchController` (owned by `StockController`, sharing
its stack + item_view). All batch work below runs there, via the shared
`batch_model_instance`.

**View batches (level 2)**
1. `view_batches_requested(stock_id)` → `StockController.open_batch_window`, which
   looks up `get_stock_name` **[DB]** and delegates to
   `BatchController.open_batch_window(stock_id, stock_name)`.
2. **[lifetime]** any previous `batch_view` is removed from the stack and
   `deleteLater`'d.
3. `get_batch_model(stock_id)` builds a `QSqlTableModel` filtered to that stock
   **[DB]** (header uses the passed-in `stock_name`).
4. New `StockBatchWindow` is created, added to the (shared) stack, and shown.
   **Back** → `BatchController.close_batch_window` returns to `item_view` and
   disposes it **[lifetime]**.

**Add / Edit / Delete / Toggle** (all on `BatchController`, via the shared `batch_model_instance`)
- Add: form → `handle_add_batch` validate → `insert_batch` **[DB]**.
- Edit: `get_batch` **[DB]** → form → `update_batch` **[DB]**.
- Delete: `delete_batch` **[DB]**. Toggle: `toggle_status` **[DB]**.
- Every mutator calls `invalidate_available_stock()` **[cache]**, refreshes the
  table model, and emits its `batch_*` **[signal]**, which closes the form and
  fires `BatchController.data_changed`.
- These `batch_*` relays are wired **once** in `BatchController.__init__` (not per
  window) because the batch model is persistent/shared. `StockController` relays
  `BatchController.data_changed` up through its own `data_changed` → Order refresh.

## 5. Recipe — add / edit

**Add**
1. `add_recipe_requested` → `open_add_recipe_form` **[lifetime]** creates
   `AddRecipeWindow`, reading `model.catalog` + `model.units` **[cache]**.
2. `recipe_submitted` → `handle_recipe_submitted` validates each amount
   (`validate_recipe_item`), builds `Recipe` → `save_recipe`.
3. `db.transaction()` → INSERT into `items` then `items_recipe` rows **[DB]** →
   commit → clears `catalog` + `recipes_catalog` + `recipe_requirements`
   **[cache]** → `recipe_saved_successfully` **[signal]** refreshes the cards,
   closes the form, and fires `data_changed`.

**Edit**
1. `edit_recipe_requested` → `get_recipe` **[DB]** → `AddRecipeWindow` (EDIT mode)
   **[lifetime]**, prefilled.
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
   - `_required_by_stock` → `_recipe_requirements` = `get_recipe_requirements`
     **[cache]** per recipe → `convert()` each ingredient into the stock unit →
     sums required per stock item.
   - Compares each total against `get_available_stock(stock_id)` **[cache]**.
   - Returns shortages + fail-loud errors + `subtotal`. **No real stock touched.**
3. View shows subtotal + any shortages/errors and enables/disables Place Order.

## 7. Order — place order (transactional)

1. `place_order_requested` **[signal]** → `_on_place_requested` builds the `Order`
   → `place_order`.
2. Re-runs `validate_stock`; on failure → `order_place_rejected` **[signal]** →
   warning, stop.
3. `db.transaction()` → INSERT `orders` + one `order_items` row each **[DB]**.
4. `_deduct_for_order`: for each required stock item, `get_available_batches`
   **[DB]** oldest-first, then `deduct_batch(batch_id, take)` **[DB]** subtracts
   the consumed amount, clamps a depleted batch to 0 and flips it to
   `out_of_stock`. It shares the connection, so it joins this transaction.
   Accumulates the exact FIFO cost.
5. UPDATE `orders` with subtotal + cost **[DB]** → commit →
   `invalidate_available_stock()` **[cache]** → `order_placed_successfully`
   **[signal]**. Any failure → `db.rollback()` (no partial deduction).
6. `_on_order_placed`: profit = subtotal − cost, clears the draft, resets the
   counters, shows the Subtotal/Cost/Profit popup. (Cost/profit are computed only
   here — the dry-run shows subtotal only.)

## 8. Cross-page live refresh

- Any stock or recipe mutation emits `data_changed` **[signal]**; MainWindow
  relays it to `OrderController.refresh_current_order`.
- That rebuilds the recipe list from `get_recipes_catalog` **[cache]**,
  reconciles the in-progress draft (drops recipes that no longer exist, refreshes
  names, keeps quantities), and re-runs the dry-run.
- `RecipeOrderRow.set_quantity` restores counters **silently** (no
  `quantity_changed` emit) to avoid a feedback loop.

## 9. Caches & invalidation

| Cache (`BaseModel`) | Filled by | Cleared by |
|---|---|---|
| `get_units` | first read (units combo) | `invalidate_units` (not currently called — units are seed data) |
| `get_catalog` | stock id+name reads | `sync_model` on stock insert/update/delete |
| `get_recipes_catalog` | recipe cards / order rows | `save_recipe`, `update_recipe` |
| `get_available_stock(stock_id)` | dry-run + place_order | every `StockBatchModel` mutator; `place_order` post-commit |
| `get_recipe_requirements(item_id)` | dry-run + deduction | `save_recipe`, `update_recipe`, and `sync_model` (stock name/unit affects it) |

All stock writes go through `StockBatchModel` or `OrderModel`, so the
available-stock cache is the single serialized mutation path and cannot go stale.

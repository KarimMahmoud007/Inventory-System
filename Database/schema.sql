PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

INSERT OR IGNORE INTO units (id, name) VALUES
(1, 'kg'), (2, 'mL'), (3, 'L'), (4, 'g');


CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    unit_of_measure INTEGER NOT NULL REFERENCES units(id)
);


CREATE TABLE IF NOT EXISTS stock_batch (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER NOT NULL REFERENCES stock(id) ON DELETE RESTRICT,
    price NUMERIC NOT NULL,
    production_date TEXT,
    expiration_date TEXT,
    quantity NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available', 'out_of_stock')),
    added_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    available INTEGER,
    price NUMERIC NOT NULL
);


CREATE TABLE IF NOT EXISTS items_recipe (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES items(id),
    stock_id INTEGER NOT NULL REFERENCES stock(id),
    amount NUMERIC NOT NULL,
    unit INTEGER NOT NULL REFERENCES units(id)
);


CREATE TABLE IF NOT EXISTS wasted_stock (
    id INTEGER PRIMARY KEY,
    stock_batch_id INTEGER NOT NULL REFERENCES stock_batch(id),
    wasted_amount NUMERIC NOT NULL,
    unit INTEGER NOT NULL REFERENCES units(id),
    price NUMERIC NOT NULL,
    waste_type TEXT NOT NULL,
    wasted_at TEXT NOT NULL DEFAULT (datetime('now'))
);


CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'placed', 'cancelled', 'fulfilled')),
    subtotal NUMERIC NOT NULL DEFAULT 0,
    cost NUMERIC NOT NULL DEFAULT 0
);


CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id INTEGER NOT NULL REFERENCES items(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0)
);


-- Finance ledger: one row per batch consumed by an order (FIFO deduction).
-- orders.cost is the sum of amount * unit_price over these rows.
CREATE TABLE IF NOT EXISTS order_batch_consumption (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    stock_batch_id INTEGER NOT NULL REFERENCES stock_batch(id),
    amount NUMERIC NOT NULL CHECK (amount > 0),
    unit_price NUMERIC NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_obc_order ON order_batch_consumption(order_id);


-- Calendar schedule for InventoryInspector: the date each named watch last ran,
-- as 'YYYY-MM-DD'. Survives restarts, so a daily watch fires once per calendar
-- day regardless of when the app happens to be opened.
CREATE TABLE IF NOT EXISTS inspector_state (
    name TEXT PRIMARY KEY,
    last_run_on TEXT NOT NULL
);
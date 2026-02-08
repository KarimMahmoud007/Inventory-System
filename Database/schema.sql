CREATE TABLE IF NOT EXISTS stock (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    unit_of_measure TEXT NOT NULL,
    price NUMERIC NOT NULL,
    production_date TEXT,
    expiration_date TEXT,
    quantity NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS items(
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    available INTEGER,
    price NUMERIC NOT NULL
);

CREATE TABLE IF NOT EXISTS items_recipe(
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL,
    stock_id INTEGER NOT NULL,
    amount NUMERIC NOT NULL,
    unit TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES items(id),
    FOREIGN KEY (stock_id) REFERENCES stock(id)
);

CREATE TABLE IF NOT EXISTS wasted_stock (
    id INTEGER PRIMARY KEY,
    stock_id INTEGER NOT NULL,
    wasted_amount NUMERIC NOT NULL,
    unit TEXT NOT NULL,
    price NUMERIC NOT NULL,
    waste_type TEXT NOT NULL,
    FOREIGN KEY (stock_id) REFERENCES stock(id)
);





CREATE TABLE IF NOT EXISTS price_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id TEXT NOT NULL,
    product_url TEXT NOT NULL,
    price REAL NOT NULL,
    mrp REAL,
    timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
);

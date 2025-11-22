import hashlib
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "price_history.sqlite")
DB_PATH = os.path.abspath(DB_PATH)

def get_product_id(url):
    return hashlib.md5(url.encode()).hexdigest()


class PriceTracker:

    def _connect(self):
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    def save_price(self, url, price, mrp=None):
        pid = get_product_id(url)

        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO price_history (product_id, product_url, price, mrp)
            VALUES (?, ?, ?, ?)
        """, (pid, url, price, mrp))

        conn.commit()
        conn.close()

        return {"status": "saved"}

    def get_history(self, url):
        pid = get_product_id(url)

        conn = self._connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT price, mrp, timestamp
            FROM price_history
            WHERE product_id = ?
            ORDER BY timestamp ASC
        """, (pid,))

        rows = cur.fetchall()
        conn.close()

        return {
            "product_id": pid,
            "history": [
                {"price": r[0], "mrp": r[1], "timestamp": r[2]}
                for r in rows
            ]
        }

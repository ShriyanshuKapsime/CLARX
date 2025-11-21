import hashlib
import sqlite3
import os

# Path to DB inside backend/database/
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "database", "price_history.sqlite")
DB_PATH = os.path.abspath(DB_PATH)


def get_product_id(url: str) -> str:
    """Consistent hashed product ID."""
    return hashlib.md5(url.encode()).hexdigest()


class PriceTracker:

    def _connect(self):
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    def save_price(self, product_url: str, price: float, mrp: float = None):
        """
        Insert a new price entry into the database.
        """
        product_id = get_product_id(product_url)

        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO price_history (product_id, product_url, price, mrp)
            VALUES (?, ?, ?, ?)
            """,
            (product_id, product_url, price, mrp)
        )

        conn.commit()
        conn.close()

        return {
            "status": "saved",
            "product_id": product_id,
            "price": price,
            "mrp": mrp
        }

    def get_history(self, product_url: str):
        """
        Fetch the entire price history of the product.
        """
        product_id = get_product_id(product_url)

        conn = self._connect()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT price, mrp, timestamp
            FROM price_history
            WHERE product_id = ?
            ORDER BY timestamp ASC
            """,
            (product_id,)
        )

        rows = cursor.fetchall()
        conn.close()

        return {
            "product_id": product_id,
            "history": [
                {"price": r[0], "mrp": r[1], "timestamp": r[2]}
                for r in rows
            ]
        }


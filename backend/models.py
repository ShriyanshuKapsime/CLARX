"""
SQLite database models for ClearBuy/ClearCart/TruthLens
"""
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
import json


class Database:
    def __init__(self, db_path: str = "clarx.db"):
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        """Initialize database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # URLs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                domain TEXT,
                last_scraped_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_id INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (url_id) REFERENCES urls(id),
                UNIQUE(url_id, timestamp)
            )
        """)

        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                result_json TEXT,
                error_message TEXT
            )
        """)

        conn.commit()
        conn.close()

    def get_or_create_url(self, url: str) -> int:
        """Get URL ID or create if doesn't exist"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Extract domain
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        cursor.execute(
            "SELECT id FROM urls WHERE url = ?",
            (url,)
        )
        row = cursor.fetchone()

        if row:
            url_id = row[0]
        else:
            cursor.execute(
                "INSERT INTO urls (url, domain, last_scraped_at) VALUES (?, ?, ?)",
                (url, domain, datetime.now().isoformat())
            )
            url_id = cursor.lastrowid

        conn.commit()
        conn.close()
        return url_id

    def update_url_scraped(self, url: str):
        """Update last_scraped_at timestamp"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE urls SET last_scraped_at = ? WHERE url = ?",
            (datetime.now().isoformat(), url)
        )
        conn.commit()
        conn.close()

    def insert_price(self, url: str, price: float):
        """Insert price record"""
        url_id = self.get_or_create_url(url)
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO prices (url_id, price, timestamp) VALUES (?, ?, ?)",
                (url_id, price, datetime.now().isoformat())
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # Already exists for this timestamp
            pass
        finally:
            conn.close()

    def get_price_history(self, url: str, limit: int = 30) -> List[Dict]:
        """Get price history for a URL"""
        url_id = self.get_or_create_url(url)
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT price, timestamp 
            FROM prices 
            WHERE url_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (url_id, limit))

        rows = cursor.fetchall()
        conn.close()

        return [
            {"price": row[0], "ts": row[1]}
            for row in reversed(rows)  # Return in chronological order
        ]

    def create_job(self, url: str) -> int:
        """Create a new analysis job"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (url, status) VALUES (?, 'pending')",
            (url,)
        )
        job_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return job_id

    def update_job(self, job_id: int, status: str, result_json: Optional[Dict] = None, error_message: Optional[str] = None):
        """Update job status and result"""
        conn = self.get_connection()
        cursor = conn.cursor()

        result_str = json.dumps(result_json) if result_json else None
        finished_at = datetime.now().isoformat() if status in ('done', 'failed') else None

        cursor.execute("""
            UPDATE jobs 
            SET status = ?, result_json = ?, error_message = ?, finished_at = ?
            WHERE id = ?
        """, (status, result_str, error_message, finished_at, job_id))

        conn.commit()
        conn.close()

    def get_job(self, job_id: int) -> Optional[Dict]:
        """Get job by ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, url, status, created_at, finished_at, result_json, error_message FROM jobs WHERE id = ?",
            (job_id,)
        )
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "url": row[1],
            "status": row[2],
            "created_at": row[3],
            "finished_at": row[4],
            "result": json.loads(row[5]) if row[5] else None,
            "error_message": row[6]
        }


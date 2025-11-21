"""
Database initialization helper
Run this script to initialize/reset the database
"""
from models import Database

if __name__ == '__main__':
    print("Initializing database...")
    db = Database()
    print("Database initialized successfully!")
    print("Database file: clarx.db")


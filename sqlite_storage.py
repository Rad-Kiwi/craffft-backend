import sqlite3
import os
from typing import Optional

class SQLiteStorage:
    def __init__(self, db_path: str = "data/airtable_data.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('''
                CREATE TABLE IF NOT EXISTS table_data (
                    table_name TEXT PRIMARY KEY,
                    csv_data TEXT,
                    json_data TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def save_csv(self, table_name: str, csv_data: str):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO table_data (table_name, csv_data, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (table_name, csv_data))
            except sqlite3.IntegrityError:
                c.execute('''
                    UPDATE table_data SET csv_data=?, updated_at=CURRENT_TIMESTAMP WHERE table_name=?
                ''', (csv_data, table_name))
            conn.commit()

    def save_json(self, table_name: str, json_data: str):
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            try:
                c.execute('''
                    INSERT INTO table_data (table_name, json_data, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (table_name, json_data))
            except sqlite3.IntegrityError:
                c.execute('''
                    UPDATE table_data SET json_data=?, updated_at=CURRENT_TIMESTAMP WHERE table_name=?
                ''', (json_data, table_name))
            conn.commit()

    def get_csv(self, table_name: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT csv_data FROM table_data WHERE table_name=?', (table_name,))
            row = c.fetchone()
            return row[0] if row else None

    def get_json(self, table_name: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute('SELECT json_data FROM table_data WHERE table_name=?', (table_name,))
            row = c.fetchone()
            return row[0] if row else None

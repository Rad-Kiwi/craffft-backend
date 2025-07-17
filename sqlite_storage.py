import os
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class TableData(Base):
    __tablename__ = 'table_data'
    table_name = Column(String, primary_key=True)
    csv_data = Column(Text)
    json_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SQLiteStorage:
    def __init__(self, db_path: str = "data/airtable_data.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False, future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)


    def import_dict_rows(self, table_name: str, dict_rows: list):
        """
        Import a list of dictionaries (records) directly into the specified SQLite table.
        Each dict should have the same keys (column names).
        This bypasses CSV serialization and is robust to commas, quotes, etc.
        """
        if not dict_rows:
            return
        fieldnames = list(dict_rows[0].keys())
        # Check for special characters in column names
        import re
        special_char_pattern = re.compile(r'[^a-zA-Z0-9_]')
        for col in fieldnames:
            if special_char_pattern.search(col):
                print(f"Warning: Column name '{col}' in table '{table_name}' contains special characters. This may cause issues with SQLite.")
        # Create table if not exists
        columns_sql = ', '.join([f'"{col}" TEXT' for col in fieldnames])
        with self.engine.begin() as conn:
            conn.execute(
                text(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql})')
            )
            # Clear existing data (optional, comment out if you want to append)
            conn.execute(text(f'DELETE FROM "{table_name}"'))
            # Insert rows using named parameters and dicts
            placeholders = ', '.join([f':{col}' for col in fieldnames])
            insert_sql = text(f'INSERT INTO "{table_name}" ({", ".join(fieldnames)}) VALUES ({placeholders})')
            for row in dict_rows:
                # Ensure all keys exist (fill missing with empty string)
                row_dict = {col: row.get(col, '') for col in fieldnames}
                conn.execute(insert_sql, row_dict)

    def save_csv(self, table_name: str, csv_data: str):
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            if obj:
                obj.csv_data = csv_data
                obj.updated_at = datetime.utcnow()
            else:
                obj = TableData(table_name=table_name, csv_data=csv_data, updated_at=datetime.utcnow())
                session.add(obj)
            session.commit()

    

    def save_json(self, table_name: str, json_data: str):
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            if obj:
                obj.json_data = json_data
                obj.updated_at = datetime.utcnow()
            else:
                obj = TableData(table_name=table_name, json_data=json_data, updated_at=datetime.utcnow())
                session.add(obj)
            session.commit()

    def get_csv(self, table_name: str) -> Optional[str]:
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            return obj.csv_data if obj else None

    def get_json(self, table_name: str) -> Optional[str]:
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            return obj.json_data if obj else None

    def import_csv_rows(self, table_name: str, csv_data: str):
        import csv
        import io
        with self.engine.begin() as conn:
            reader = csv.DictReader(io.StringIO(csv_data))
            fieldnames = reader.fieldnames
            # Create table if not exists
            columns_sql = ', '.join([f'"{col}" TEXT' for col in fieldnames])
            conn.execute(
                text(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql})')
            )
            # Clear existing data (optional, comment out if you want to append)
            conn.execute(text(f'DELETE FROM "{table_name}"'))
            # Insert rows using named parameters and dicts
            placeholders = ', '.join([f':{col}' for col in fieldnames])
            insert_sql = text(f'INSERT INTO "{table_name}" ({", ".join(fieldnames)}) VALUES ({placeholders})')
            for row in reader:
                # Ensure all keys exist (fill missing with empty string)
                row_dict = {col: row.get(col, '') for col in fieldnames}
                conn.execute(insert_sql, row_dict)

    def find_row_by_column(self, table_name: str, column_containing_reference: str, reference_value: str):
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f'SELECT * FROM "{table_name}" WHERE "{column_containing_reference}" = :value'), {"value": reference_value}
            )
            row = result.fetchone()
            if row:
                columns = result.keys()
                return dict(zip(columns, row))
            return None
    
    def find_value_by_row_and_column(self, table_name: str, column_containing_reference: str, reference_value: str, target_column: str):
        """
        Retrieve a value from a specific column for the row where column_containing_reference == reference_value.
        """
        with self.engine.connect() as conn:
            result = conn.execute(
                text(f'SELECT "{target_column}" FROM "{table_name}" WHERE "{column_containing_reference}" = :reference_value'),
                {"reference_value": reference_value}
            )
            row = result.fetchone()
            if row:
                return row[0]
            return None
        
    def execute_sql_query(self, table_name: str, sql_query: str):
        """
        Execute an arbitrary SQL query on the given table.
        Returns a list of dicts (rows) or None if table does not exist or error.
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql_query))
                if result.returns_rows:
                    columns = result.keys()
                    return [dict(zip(columns, row)) for row in result.fetchall()]
                return []
        except Exception as e:
            print(f"SQL query error on table {table_name}: {e}")
            return None


    def modify_field(self, table_name: str, column_containing_reference: str, reference_value: str, target_column: str, new_value):
        """
        Modify a field in the specified table.
        
        Args:
            table_name: Name of the table
            column_containing_reference: Column to look up the row
            reference_value: Value to match in the lookup column
            target_column: Column to update
            new_value: New value to set
        Returns:
            bool: True if modified successfully, False if row not found or error.
        """
        with self.engine.begin() as conn:
            result = conn.execute(
                text(f'UPDATE "{table_name}" SET "{target_column}" = :new_value WHERE "{column_containing_reference}" = :reference_value'),
                {"new_value": new_value, "reference_value": reference_value}
            )
            return result.rowcount > 0

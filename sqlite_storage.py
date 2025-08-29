import os
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, text
from sqlalchemy.orm import declarative_base, sessionmaker
from utilities import load_env, critical_tables

Base = declarative_base()

class TableData(Base):
    __tablename__ = 'table_data'
    table_name = Column(String, primary_key=True)
    csv_data = Column(Text)
    json_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SQLiteStorage:
    def __init__(self, db_path: str = "data/airtable_data.db"):
        # Check if we're on Heroku (DATABASE_URL environment variable)
        database_url = os.environ.get('DATABASE_URL')
        MODE = load_env('ENVIRONMENT_MODE')
        
        if database_url and MODE == 'Production':
            # Heroku Postgres
            # Heroku provides postgres:// but SQLAlchemy needs postgresql://
            if database_url.startswith('postgres://'):
                database_url = database_url.replace('postgres://', 'postgresql://')
            self.db_path = database_url
            self.engine = create_engine(database_url, echo=False, future=True)
            print(f"Using Heroku Postgres database")
        else:
            # Local SQLite
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            self.db_path = db_path
            self.engine = create_engine(f'sqlite:///{db_path}', echo=False, future=True)
            print(f"Using SQLite: {db_path}")
            
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
            quoted_fieldnames = ', '.join([f'"{col}"' for col in fieldnames])
            insert_sql = text(f'INSERT INTO "{table_name}" ({quoted_fieldnames}) VALUES ({placeholders})')
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
            quoted_fieldnames = ', '.join([f'"{col}"' for col in fieldnames])
            insert_sql = text(f'INSERT INTO "{table_name}" ({quoted_fieldnames}) VALUES ({placeholders})')
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
        Automatically converts complex data types (lists, dicts) to JSON strings.
        
        Args:
            table_name: Name of the table
            column_containing_reference: Column to look up the row
            reference_value: Value to match in the lookup column
            target_column: Column to update
            new_value: New value to set (will be JSON-serialized if it's a list/dict)
        Returns:
            bool: True if modified successfully, False if row not found or error.
        """
        try:
            # Convert complex data types to JSON strings
            if isinstance(new_value, (list, dict)):
                import json
                processed_value = json.dumps(new_value)
                print(f"JSON-serialized {type(new_value).__name__} for database storage: {processed_value}")
            else:
                processed_value = new_value
            
            with self.engine.begin() as conn:
                result = conn.execute(
                    text(f'UPDATE "{table_name}" SET "{target_column}" = :new_value WHERE "{column_containing_reference}" = :reference_value'),
                    {"new_value": processed_value, "reference_value": reference_value}
                )
                return result.rowcount > 0
                
        except Exception as e:
            print(f"Error modifying field in {table_name}: {e}")
            return False

    def add_record(self, table_name: str, record_data: dict) -> bool:
        """
        Add a new record to the specified table.
        Creates table if it doesn't exist and adds missing columns if they don't exist.
        
        Args:
            table_name: Name of the table to insert into
            record_data: Dictionary containing the record data to insert
            
        Returns:
            bool: True if record was added successfully, False otherwise
        """
        try:
            if not record_data:
                return False
                
            fieldnames = list(record_data.keys())
            
            # Check for special characters in column names
            import re
            special_char_pattern = re.compile(r'[^a-zA-Z0-9_]')
            for col in fieldnames:
                if special_char_pattern.search(col):
                    print(f"Warning: Column name '{col}' in table '{table_name}' contains special characters. This may cause issues with SQLite.")
            
            with self.engine.begin() as conn:
                # Check if table exists (database-agnostic way)
                try:
                    # Try to query the table - if it doesn't exist, this will raise an exception
                    conn.execute(text(f'SELECT 1 FROM "{table_name}" LIMIT 1'))
                    table_exists = True
                except Exception:
                    table_exists = False
                
                if not table_exists:
                    # Create table if it doesn't exist
                    columns_sql = ', '.join([f'"{col}" TEXT' for col in fieldnames])
                    conn.execute(
                        text(f'CREATE TABLE IF NOT EXISTS "{table_name}" ({columns_sql})')
                    )
                else:
                    # Table exists, check for missing columns and add them (database-agnostic way)
                    try:
                        # Get existing columns based on environment
                        MODE = load_env('ENVIRONMENT_MODE')
                        if MODE == 'Production':
                            # PostgreSQL syntax (production)
                            existing_columns_result = conn.execute(
                                text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"),
                                {"table_name": table_name}
                            )
                            existing_columns = {row[0] for row in existing_columns_result.fetchall()}
                        else:
                            # SQLite syntax (local development)
                            existing_columns_result = conn.execute(text(f'PRAGMA table_info("{table_name}")'))
                            existing_columns = {row[1] for row in existing_columns_result.fetchall()}  # row[1] is column name
                    except Exception as e:
                        print(f"Error getting column info for {table_name}: {e}")
                        # If we can't get column info, assume all columns are missing and try to add them
                        existing_columns = set()
                    
                    missing_columns = set(fieldnames) - existing_columns
                    for col in missing_columns:
                        try:
                            print(f"Adding missing column '{col}' to table '{table_name}'")
                            conn.execute(text(f'ALTER TABLE "{table_name}" ADD COLUMN "{col}" TEXT'))
                        except Exception as e:
                            print(f"Warning: Could not add column '{col}' to table '{table_name}': {e}")
                            # Continue anyway - the INSERT might still work if the column actually exists
                
                # Insert the new record
                placeholders = ', '.join([f':{col}' for col in fieldnames])
                quoted_fieldnames = ', '.join([f'"{col}"' for col in fieldnames])
                insert_sql = text(f'INSERT INTO "{table_name}" ({quoted_fieldnames}) VALUES ({placeholders})')
                
                # Ensure all keys exist (fill missing with empty string)
                row_dict = {col: record_data.get(col, '') for col in fieldnames}
                result = conn.execute(insert_sql, row_dict)
                
                return result.rowcount > 0
                
        except Exception as e:
            print(f"Error adding record to {table_name}: {e}")
            return False

    def delete_record(self, table_name: str, column_name: str, value: str) -> bool:
        """
        Delete a record from the table.
        
        Args:
            table_name: Name of the table
            column_name: Column to match for deletion
            value: Value to match
            
        Returns:
            True if record was deleted successfully, False otherwise
        """
        try:
            with self.engine.begin() as conn:
                # Check if table exists (database-agnostic way)
                try:
                    conn.execute(text(f'SELECT 1 FROM "{table_name}" LIMIT 1'))
                    table_exists = True
                except Exception:
                    table_exists = False
                
                if not table_exists:
                    print(f"Table {table_name} does not exist")
                    return False
                
                # Check if column exists (database-agnostic way)
                try:
                    MODE = load_env('ENVIRONMENT_MODE')
                    if MODE == 'Production':
                        # PostgreSQL syntax (production)
                        existing_columns_result = conn.execute(
                            text("SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"),
                            {"table_name": table_name}
                        )
                        existing_columns = {row[0] for row in existing_columns_result.fetchall()}
                    else:
                        # SQLite syntax (local development)
                        existing_columns_result = conn.execute(text(f'PRAGMA table_info("{table_name}")'))
                        existing_columns = {row[1] for row in existing_columns_result.fetchall()}
                    
                    if column_name not in existing_columns:
                        print(f"Column {column_name} does not exist in table {table_name}")
                        return False
                except Exception as e:
                    print(f"Warning: Could not check column existence: {e}")
                    # Proceed anyway - the DELETE might still work
                
                # Execute delete statement
                delete_stmt = text(f'DELETE FROM "{table_name}" WHERE "{column_name}" = :value')
                result = conn.execute(delete_stmt, {"value": value})
                
                return result.rowcount > 0
                
        except Exception as e:
            print(f"Error deleting from {table_name}: {e}")
            return False

    def has_data_in_critical_tables(self) -> bool:
        """
        Check if ALL critical tables have data.
        
        Returns:
            bool: True if ALL critical tables have data, False if any are empty or missing
        """
        tables_with_data = []
        
        try:
            with self.engine.connect() as conn:
                for table_name in critical_tables:
                    try:
                        # Check if table exists and has data
                        result = conn.execute(text(f'SELECT COUNT(*) as count FROM "{table_name}" LIMIT 1'))
                        row = result.fetchone()
                        if row and row[0] > 0:
                            print(f"Found {row[0]} records in {table_name}")
                            tables_with_data.append(table_name)
                        else:
                            print(f"Table {table_name} exists but has no data")
                    except Exception as e:
                        # Table might not exist yet
                        print(f"Table {table_name} not accessible: {e}")
                        continue
                
                # Check if ALL critical tables have data
                if len(tables_with_data) == len(critical_tables):
                    print(f"All critical tables have data: {tables_with_data}")
                    return True
                else:
                    missing_data = [t for t in critical_tables if t not in tables_with_data]
                    print(f"Some critical tables missing data: {missing_data}")
                    return False
                
        except Exception as e:
            print(f"Error checking database data: {e}")
            # If we can't check, assume empty to trigger initial sync
            return False

    def delete_table(self, table_name: str) -> bool:
        """
        Delete/drop a table from the database.
        
        Args:
            table_name: Name of the table to delete
            
        Returns:
            bool: True if table was deleted successfully, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Use double quotes to handle table names with special characters
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
                conn.commit()
                print(f"Successfully deleted table: {table_name}")
                return True
        except Exception as e:
            print(f"Error deleting table {table_name}: {e}")
            return False

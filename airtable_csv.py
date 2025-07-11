import os
from airtable import Airtable
import csv
import io
import json
from typing import Optional
from sqlite_storage import SQLiteStorage

class AirtableCSVManager:
    def __init__(self, base_id, table_name, api_key, sqlite_storage: Optional[SQLiteStorage] = None):
        self.base_id = base_id
        self.table_name = table_name
        self.api_key = api_key
        self.csv_path = f"data/{table_name}.csv"
        self.sqlite_storage = sqlite_storage

    def read_csv(self, from_db: bool = False):
        # Optionally read from SQLite
        if from_db and self.sqlite_storage:
            print(f"Reading CSV from SQLite for table: {self.table_name}")
            return self.sqlite_storage.get_csv(self.table_name)
        # Read and return the raw CSV data from the file
        if not os.path.exists(self.csv_path):
            return None
        with open(self.csv_path, "r", encoding="utf-8") as f:
            return f.read()

    # Fetch CSV data from Airtable and save it to file
    def update_csv_from_airtable(self):
        airtable = Airtable(self.base_id, self.table_name, self.api_key)
        records = airtable.get_all()
        if not records:
            return None

        fieldnames = set()
        for record in records:
            fieldnames.update(record['fields'].keys())
        fieldnames = list(fieldnames)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record['fields'])

        csv_data = output.getvalue()
        output.close()

        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write(csv_data)

        # Store in SQLite if available
        if self.sqlite_storage:
            self.sqlite_storage.import_csv_rows(self.table_name, csv_data)

        return f"Successfully updated CSV from Airtable. Access it at /data/{self.table_name}.csv"

    def convert_csv_to_json(self, from_db: bool = False):
        # Optionally read CSV from SQLite
        if from_db and self.sqlite_storage:
            csv_data = self.sqlite_storage.get_csv(self.table_name)
            if not csv_data:
                return None
            reader = csv.DictReader(io.StringIO(csv_data))
        else:
            if not os.path.exists(self.csv_path):
                return None
            with open(self.csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
        result = []
        for row in reader:
            # Merge imageUrls/* or images/* keys into a single 'images' array
            images = []
            keys_to_remove = []
            for k in list(row.keys()):
                if k.startswith('images/') or k.startswith('imageUrls/'):
                    if row[k]:
                        images.append(row[k])
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del row[k]
            if images:
                row['images'] = images
            result.append(row)
        # Store JSON in SQLite if available
        if self.sqlite_storage:
            self.sqlite_storage.save_json(self.table_name, json.dumps(result))
        return result

    def get_row(self, column_containing_reference: str, reference_value: str):
        if self.sqlite_storage:
            return self.sqlite_storage.find_row_by_column(self.table_name, column_containing_reference, reference_value)
        return None

    def get_value_by_row_and_column(self, column_containing_reference: str, reference_value: str, target_column: str):
        if self.sqlite_storage:
            return self.sqlite_storage.find_value_by_row_and_column(self.table_name, column_containing_reference, reference_value, target_column)
        return None

    def execute_sql_query(self, sql_query: str):
        """
        Execute an arbitrary SQL query on this table using the SQLite backend.
        Returns a list of dicts (rows) or None if not available.
        """
        if self.sqlite_storage:
            return self.sqlite_storage.execute_sql_query(self.table_name, sql_query)
        return None

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
        self.sqlite_storage = sqlite_storage

    # Fetch data from Airtable and store in SQLite only
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

        # Store in SQLite only
        if self.sqlite_storage:
            self.sqlite_storage.import_csv_rows(self.table_name, csv_data)

        return f"Successfully updated DB from Airtable for table {self.table_name}."


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

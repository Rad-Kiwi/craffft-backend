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
        self.has_updates = False  # Track if any updates have been made

    # Fetch data from Airtable and store in SQLite using csv writer
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
            # Ensure row doesnt have a comma
            record = self.record_comma_check(record)
            # Write the record to CSV
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


    def modify_field(self, column_containing_reference: str, reference_value: str, target_column: str, new_value):
        """
        Modify a field in the specified table.
        
        Args:
            table_name: Name of the table
            column_containing_reference: Column to look up the row
            reference_value: Value to match in the lookup column
            target_column: Column to update
            new_value: New value to set
        
        Returns:
            True if modified successfully, False otherwise
        """
        updated = False

        if self.sqlite_storage:
            updated = self.sqlite_storage.modify_field(self.table_name, column_containing_reference, reference_value, target_column, new_value)
        
        if updated:
            self.has_updates = True

        return updated

    @staticmethod
    def record_comma_check(record) -> bool:
        """
        Check if the CSV data contains commas in any field.
        Wraps fields with commas in double quotes.
        """
        for key in record['fields']:
            if isinstance(record['fields'][key], str):
                if ',' in record['fields'][key]:
                    # Wrap in double quotes to handle commas
                    record['fields'][key] = record['fields'][key].replace('"', '""')
        return record

    def upload_to_airtable(self) -> Optional[str]:
        """
        Upload the current SQLite table data back to Airtable.
        This will get all records from SQLite and update/create them in Airtable.
        
        Returns:
            Success message or None if failed
        """
        try:
            if not self.sqlite_storage:
                return "Error: No SQLite storage configured"
            
            # Get all records from SQLite
            sql = f"SELECT * FROM \"{self.table_name}\""
            records = self.sqlite_storage.execute_sql_query(self.table_name, sql)
            
            if not records:
                return "No records found to upload"
            
            airtable = Airtable(self.base_id, self.table_name, self.api_key)
            
            # For now, we'll clear the table and re-create all records
            # In a production system, you'd want to do a proper sync with updates/inserts/deletes
            
            # Get existing records to delete them
            existing_records = airtable.get_all()
            
            # Delete existing records in batches
            if existing_records:
                record_ids = [record['id'] for record in existing_records]
                # Airtable allows deletion of up to 10 records at a time
                for i in range(0, len(record_ids), 10):
                    batch = record_ids[i:i+10]
                    airtable.batch_delete(batch)
            
            # Upload new records in batches
            upload_records = []
            for record in records:
                # Convert SQLite record to Airtable format
                airtable_record = {'fields': record}
                upload_records.append(airtable_record)
            
            # Airtable allows creation of up to 10 records at a time
            uploaded_count = 0
            for i in range(0, len(upload_records), 10):
                batch = upload_records[i:i+10]
                result = airtable.batch_insert(batch)
                if result:
                    uploaded_count += len(result)
            
            return f"Successfully uploaded {uploaded_count} records to Airtable table {self.table_name}"
            
        except Exception as e:
            return f"Error uploading to Airtable: {str(e)}"
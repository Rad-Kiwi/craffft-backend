import os
from airtable import Airtable
import csv
import io
import json
from typing import Optional
from sqlite_storage import SQLiteStorage
from utilities import convert_value_for_airtable

class TableManager:
    def __init__(self, base_id, table_name, api_key, sqlite_storage: Optional[SQLiteStorage] = None):
        self.base_id = base_id
        self.table_name = table_name
        self.api_key = api_key
        self.sqlite_storage = sqlite_storage
        self.has_updates = False  # Track if any updates have been made

    # Fetch data from Airtable and store in SQLite using csv writer
    def update_database_from_airtable(self):
        # Note: Ideally this woul be done with a dictwriter, but I cant seem to get it to work

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
        
        """
        try:
            if not self.sqlite_storage:
                return "Error: No SQLite storage configured"
            
            # Get all records from local database
            sql = f"SELECT * FROM \"{self.table_name}\""
            records = self.sqlite_storage.execute_sql_query(self.table_name, sql)
            
            if not records:
                return "No records found to upload"
            
            airtable = Airtable(self.base_id, self.table_name, self.api_key)
            
            # Delete all existing records
            existing_records = airtable.get_all()
            if existing_records:
                record_ids = [record['id'] for record in existing_records]
                for i in range(0, len(record_ids), 10):
                    batch = record_ids[i:i+10]
                    airtable.batch_delete(batch)
                print(f"Deleted {len(record_ids)} existing records")
            
            # Upload new records (smart conversion for lists and numbers)
            upload_records = []
            for record in records:
                clean_record = {}
                for k, v in record.items():
                    converted_value = convert_value_for_airtable(v)
                    if converted_value is not None:
                        clean_record[k] = converted_value
                upload_records.append(clean_record)
            
            # Upload in batches
            uploaded_count = 0
            for i in range(0, len(upload_records), 10):
                batch = upload_records[i:i+10]
                result = airtable.batch_insert(batch)
                if result:
                    uploaded_count += len(result)
            
            return f"Success: Replaced {self.table_name} with {uploaded_count} records"
            
        except Exception as e:
            return f"Error: {str(e)}"

    def add_record(self, record_data: dict) -> bool:
        """
        Add a new record to the table.
        
        Args:
            record_data: Dictionary containing the record data to insert
            
        Returns:
            True if record was added successfully, False otherwise
        """
        if not self.sqlite_storage:
            return False
            
        try:
            # Insert the record into SQLite
            success = self.sqlite_storage.add_record(self.table_name, record_data)
            
            if success:
                self.has_updates = True
                
            return success
            
        except Exception as e:
            print(f"Error adding record to {self.table_name}: {e}")
            return False

    def delete_record(self, column_containing_reference: str, reference_value: str) -> bool:
        """
        Delete a record from the table.
        
        Args:
            column_containing_reference: Column to look up the row
            reference_value: Value to match in the lookup column
            
        Returns:
            True if record was deleted successfully, False otherwise
        """
        if not self.sqlite_storage:
            return False
            
        try:
            # Delete the record from SQLite
            success = self.sqlite_storage.delete_record(self.table_name, column_containing_reference, reference_value)
            
            if success:
                self.has_updates = True
                
            return success
            
        except Exception as e:
            print(f"Error deleting record from {self.table_name}: {e}")
            return False

    def get_full_table(self):
        """
        Get all records from the table as a list of dictionaries
        """
        if not self.sqlite_storage:
            return None
            
        try:
            sql = f"SELECT * FROM \"{self.table_name}\""
            records = self.sqlite_storage.execute_sql_query(self.table_name, sql)
            return records if records else []
        except Exception as e:
            print(f"Error getting full table {self.table_name}: {e}")
            return []
import os
import time
import schedule
from airtable_multi_manager import AirtableMultiManager

class DailyAirtableUploader:
    def __init__(self):
        # Initialize the multi-manager from environment variables
        self.multi_manager = AirtableMultiManager.from_environment()
        
        # Discover and add all tables from the base on initialization
        print("Discovering tables from Airtable base...")
        results = self.multi_manager.discover_and_add_tables_from_base()
        print(f"Added tables: {results}")
        
        # Initial sync to ensure we have the latest data before starting upload scheduler
        print("Performing initial sync from Airtable...")
        sync_results = self.multi_manager.update_all_tables()
        print(f"Initial sync complete: {sync_results}")

    def upload_to_airtable(self):
        print("Uploading modified tables to Airtable...")
        
        # Check which tables have been modified
        modified_tables = self.multi_manager.get_modified_tables()
        
        if not modified_tables:
            print("No tables have been modified - nothing to upload")
            return
        
        print(f"Found {len(modified_tables)} modified tables: {modified_tables}")
        
        # Upload all modified tables
        results = self.multi_manager.upload_modified_tables_to_airtable()
        
        # Check results and report
        success_count = 0
        failed_tables = []
        
        for table_name, result in results.items():
            if result and result.startswith("Successfully"):
                success_count += 1
                print(f"✓ {table_name}: {result}")
            else:
                failed_tables.append(table_name)
                print(f"✗ {table_name}: {result}")
        
        total_tables = len(results)
        print(f"\nUpload Summary: {success_count}/{total_tables} tables uploaded successfully")
        
        if failed_tables:
            print(f"Failed tables: {', '.join(failed_tables)}")
        else:
            print("All modified tables uploaded successfully!")

    def run_daily(self, time_of_day="00:00"):
        schedule.every().day.at(time_of_day).do(self.upload_to_airtable)
        print(f"Scheduled daily upload of modified tables to Airtable at {time_of_day}.")
        print(f"Currently managing {len(self.multi_manager.get_available_tables())} tables: {self.multi_manager.get_available_tables()}")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    print("Starting Daily Airtable Uploader...")
    uploader = DailyAirtableUploader()
    uploader.run_daily("00:00")  # Change time as needed (HH:MM, 24-hour format)

import os
import time
from dotenv import load_dotenv
import schedule
from airtable_multi_manager import AirtableMultiManager

class DailyAirtableUpdater:
    def __init__(self):
        load_dotenv()
        # Initialize the multi-manager from environment variables
        self.multi_manager = AirtableMultiManager.from_environment()
        
        # Discover and add all tables from the base on initialization
        print("Discovering tables from Airtable base...")
        results = self.multi_manager.discover_and_add_tables_from_base()
        print(f"Added tables: {results}")

    def update_csv(self):
        print("Updating all Airtable tables...")
        results = self.multi_manager.update_all_tables()
        
        # Check results and report
        success_count = 0
        failed_tables = []
        
        for table_name, result in results.items():
            if result and not result.startswith("Error:") and not result.startswith("Failed"):
                success_count += 1
                print(f"✓ {table_name}: {result}")
            else:
                failed_tables.append(table_name)
                print(f"✗ {table_name}: {result}")
        
        total_tables = len(results)
        print(f"\nUpdate Summary: {success_count}/{total_tables} tables updated successfully")
        
        if failed_tables:
            print(f"Failed tables: {', '.join(failed_tables)}")
        else:
            print("All tables updated successfully!")

    def run_daily(self, time_of_day="00:00"):
        schedule.every().day.at(time_of_day).do(self.update_csv)
        print(f"Scheduled daily update for all tables at {time_of_day}.")
        print(f"Currently managing {len(self.multi_manager.get_available_tables())} tables: {self.multi_manager.get_available_tables()}")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    print("Starting Daily Airtable Updater...")
    updater = DailyAirtableUpdater()
    updater.run_daily("00:00")  # Change time as needed (HH:MM, 24-hour format)

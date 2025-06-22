import os
import time
from dotenv import load_dotenv
import schedule
from airtable_csv import AirtableCSVManager

class DailyAirtableUpdater:
    def __init__(self):
        load_dotenv()
        self.base_id = os.getenv('AIRTABLE_BASE_ID')
        self.table_name = os.getenv('AIRTABLE_TABLE_NAME')
        self.api_key = os.getenv('AIRTABLE_API_KEY')
        self.exporter = AirtableCSVManager(self.base_id, self.table_name, self.api_key)

    def update_csv(self):
        print("Updating Airtable CSV...")
        success = self.exporter.update_csv_from_airtable()

        if success:
            print("CSV updated successfully.")
        else:
            print("Failed to update CSV.")

    def run_daily(self, time_of_day="00:00"):
        schedule.every().day.at(time_of_day).do(self.update_csv)
        print(f"Scheduled daily update at {time_of_day}.")
        while True:
            schedule.run_pending()
            time.sleep(60)

if __name__ == "__main__":
    updater = DailyAirtableUpdater()
    updater.run_daily("00:00")  # Change time as needed (HH:MM, 24-hour format)

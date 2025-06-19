from flask import Flask, Response, jsonify
import os
from dotenv import load_dotenv
from airtable_csv import AirtableCSVExporter
import threading
from scheduler import DailyAirtableUpdater

app = Flask(__name__)


load_dotenv('.env.local')

# Ensure required environment variables are set
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_TABLE_NAME') or not os.getenv('AIRTABLE_API_KEY'):
    load_dotenv('.env')
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_TABLE_NAME') or not os.getenv('AIRTABLE_API_KEY'):
    raise ValueError("Missing required environment variables: AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY")

@app.route('/')
def home():
    return "Hello, Flask!"

@app.route('/get-airtable-csv', methods=['GET'])
def get_airtable_csv():
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = os.getenv('AIRTABLE_TABLE_NAME')
    api_key = os.getenv('AIRTABLE_API_KEY')
    exporter = AirtableCSVExporter(base_id, table_name, api_key)
    csv_data = exporter.fetch_csv()
    if not csv_data:
        return Response("No data found", status=404)
    return Response(csv_data, mimetype='text/csv')

@app.route('/update-tile-data')
def update_tile_data():
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = os.getenv('AIRTABLE_TABLE_NAME')
    api_key = os.getenv('AIRTABLE_API_KEY')
    exporter = AirtableCSVExporter(base_id, table_name, api_key)
    success = exporter.save_csv()
    if success:
        return "CSV saved to /data/coastline-tiles-with-data.csv"
    else:
        return "No data found or failed to save", 500

@app.route('/get-tile-data', methods=['GET'])
def get_tile_data():
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = os.getenv('AIRTABLE_TABLE_NAME')
    api_key = os.getenv('AIRTABLE_API_KEY')
    exporter = AirtableCSVExporter(base_id, table_name, api_key)
    json_data = exporter.fetch_json()
    if not json_data:
        return Response("No data found", status=404)
    return jsonify(json_data)

if __name__ == '__main__':
    # Start the scheduler in a background thread
    def start_scheduler():
        updater = DailyAirtableUpdater()
        updater.run_daily("00:00")  # Set desired time

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    app.run(debug=True)
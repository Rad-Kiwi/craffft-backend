from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from flask import Response, jsonify, Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from airtable_csv import AirtableCSVExporter
import threading
from scheduler import DailyAirtableUpdater

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv('.env.local')

# Ensure required environment variables are set
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_TABLE_NAME') or not os.getenv('AIRTABLE_API_KEY'):
    load_dotenv('.env')
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_TABLE_NAME') or not os.getenv('AIRTABLE_API_KEY'):
    raise ValueError("Missing required environment variables: AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY")

ENVIRONMENT_MODE = os.getenv('ENVIRONMENT', 'Production')

exporter = AirtableCSVExporter(
    base_id=os.getenv('AIRTABLE_BASE_ID'),
    table_name=os.getenv('AIRTABLE_TABLE_NAME'),
    api_key=os.getenv('AIRTABLE_API_KEY')
)

CORS(app)


@app.get("/")
def home():
    return "Hello, Flask!"


@app.get("/get-airtable-csv")
def get_airtable_csv():
    csv_data = exporter.read_csv()
    if not csv_data:
        return Response("No data found", status=404)
    return Response(csv_data, mimetype='text/csv')


@app.get("/update-tile-data")
def update_tile_data():
    success = exporter.update_csv_from_airtable()
    if success:
        return "CSV saved to /data/coastline-tiles-with-data.csv"
    else:
        return "No data found or failed to save", 500


@app.get("/get-tile-data")
def get_tile_data():
    json_data = exporter.convert_csv_to_json()
    if not json_data:
        return Response("No data found", status=404)
    return jsonify(json_data)


if __name__ == '__main__':
    if ENVIRONMENT_MODE == 'Production':
        exporter.update_csv_from_airtable()  # Save initial CSV

    # Start the scheduler in a background thread
    def start_scheduler():
        updater = DailyAirtableUpdater()
        updater.run_daily("00:00")  # Set desired time

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    app.run(debug=True)